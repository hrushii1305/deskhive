from rest_framework import generics
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