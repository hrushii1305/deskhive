from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from .models import Ticket, Comment, TicketAuditLog, log_ticket_action
from .services import get_least_loaded_agent
from .serializers import TicketSerializer, CommentSerializer
from accounts.permissions import IsApprovedMember
from .tasks import send_ticket_created_email, send_ticket_assigned_email


class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsApprovedMember]

    def get_queryset(self):
        member = self.request.user.member
        org_tickets = Ticket.objects.filter(organization=member.organization)
        if member.role == 'customer':
            return org_tickets.filter(requester=member)
        return org_tickets

    def perform_create(self, serializer):
        member = self.request.user.member
        agent = get_least_loaded_agent(member.organization)
        ticket = serializer.save(
            organization=member.organization,
            requester=member,
            assigned_to=agent,
        )
        # Log the auto-assignment as an audit event (only if an agent was assigned).
        if agent:
            log_ticket_action(
                ticket=ticket,
                actor=member,
                action='auto_assigned',
                old_value='unassigned',
                new_value=str(agent),
            )
        send_ticket_created_email.delay(ticket.id)
        if agent:
            send_ticket_assigned_email.delay(ticket.id)


class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated, IsApprovedMember]

    def get_queryset(self):
        member = self.request.user.member
        org_tickets = Ticket.objects.filter(organization=member.organization)
        if member.role == 'customer':
            return org_tickets.filter(requester=member)
        return org_tickets

    def perform_update(self, serializer):
        # Capture the old status BEFORE the update is applied.
        old_status = serializer.instance.status
        ticket = serializer.save()
        # Only log if the status actually changed (no point logging open -> open).
        if old_status != ticket.status:
            log_ticket_action(
                ticket=ticket,
                actor=self.request.user.member,
                action='status_changed',
                old_value=old_status,
                new_value=ticket.status,
            )


class TicketClaimView(APIView):
    """
    POST /api/tickets/<id>/claim/

    Lets an AGENT (or owner) claim an unassigned ticket. Customers cannot
    claim tickets. Uses row-level locking (select_for_update inside a
    transaction) so two agents claiming the same ticket at the same instant
    can't both succeed — the second one waits for the first to commit, then
    sees it's taken and is refused. Every successful claim writes an audit entry.
    """
    permission_classes = [IsAuthenticated, IsApprovedMember]

    def post(self, request, ticket_id):
        member = request.user.member

        # RBAC: only agents and owners can claim tickets — customers cannot.
        # Enforced server-side so a customer can't claim by calling the API
        # directly, even if the UI button is hidden.
        if member.role not in ('agent', 'owner'):
            return Response(
                {"detail": "Only agents can claim tickets."},
                status=status.HTTP_403_FORBIDDEN,
            )

        with transaction.atomic():
            # Lock this ticket row until the transaction commits.
            # Tenant-scoped, exactly like the other views.
            try:
                ticket = (
                    Ticket.objects
                    .select_for_update()
                    .get(pk=ticket_id, organization=member.organization)
                )
            except Ticket.DoesNotExist:
                raise NotFound("Ticket not found")

            # Holding the lock guarantees this is the TRUE current state,
            # not a stale read from before another agent's claim.
            if ticket.assigned_to is not None:
                return Response(
                    {"detail": f"Already claimed by {ticket.assigned_to}."},
                    status=status.HTTP_409_CONFLICT,
                )

            # Capture the OLD status BEFORE changing it, so the audit
            # entry records the real transition (open -> in_progress).
            old_status = ticket.status

            ticket.assigned_to = member
            ticket.status = 'in_progress'
            ticket.save()

            # Immutable audit entry, inside the same transaction as the claim,
            # so it rolls back with the claim if anything fails.
            log_ticket_action(
                ticket=ticket,
                actor=member,
                action='claimed',
                old_value=old_status,
                new_value=ticket.status,
            )

        # Notify the newly-assigned agent, consistent with perform_create above.
        send_ticket_assigned_email.delay(ticket.id)

        return Response(
            {"detail": "Ticket claimed.", "assigned_to": str(member)},
            status=status.HTTP_200_OK,
        )


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated, IsApprovedMember]

    def get_ticket(self):
        member = self.request.user.member
        org_tickets = Ticket.objects.filter(organization=member.organization)
        if member.role == 'customer':
            org_tickets = org_tickets.filter(requester=member)
        try:
            return org_tickets.get(pk=self.kwargs['ticket_id'])
        except Ticket.DoesNotExist:
            raise NotFound("Ticket not found")

    def get_queryset(self):
        ticket = self.get_ticket()
        return ticket.comments.all()

    def perform_create(self, serializer):
        ticket = self.get_ticket()
        comment = serializer.save(ticket=ticket, author=self.request.user.member)

        # Broadcast the new comment to everyone watching this ticket via WebSocket
        from channels.layers import get_channel_layer
        from asgiref.sync import async_to_sync

        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f'ticket_{ticket.id}',
            {
                'type': 'comment_message',
                'author': str(comment.author),
                'body': comment.body,
            }
        )