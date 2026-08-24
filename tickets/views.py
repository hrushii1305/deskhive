from django.db import transaction
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from .models import Ticket, Comment
from .services import get_least_loaded_agent
from .serializers import TicketSerializer, CommentSerializer
from .tasks import send_ticket_created_email, send_ticket_assigned_email


class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

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
        send_ticket_created_email.delay(ticket.id)
        if agent:
            send_ticket_assigned_email.delay(ticket.id)


class TicketDetailView(generics.RetrieveUpdateDestroyAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        member = self.request.user.member
        org_tickets = Ticket.objects.filter(organization=member.organization)
        if member.role == 'customer':
            return org_tickets.filter(requester=member)
        return org_tickets


class TicketClaimView(APIView):
    """
    POST /api/tickets/<id>/claim/

    Lets an agent claim an unassigned ticket. Uses row-level locking
    (select_for_update inside a transaction) so two agents claiming the
    same ticket at the same instant can't both succeed — the second one
    waits for the first to commit, then sees it's taken and is refused.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, ticket_id):
        member = request.user.member

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

            ticket.assigned_to = member
            ticket.status = 'in_progress'
            ticket.save()

        # Notify the newly-assigned agent, consistent with perform_create above.
        send_ticket_assigned_email.delay(ticket.id)

        return Response(
            {"detail": "Ticket claimed.", "assigned_to": str(member)},
            status=status.HTTP_200_OK,
        )


class CommentListCreateView(generics.ListCreateAPIView):
    serializer_class = CommentSerializer
    permission_classes = [IsAuthenticated]

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
        serializer.save(ticket=ticket, author=self.request.user.member)