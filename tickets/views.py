from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import NotFound
from .models import Ticket, Comment
from .serializers import TicketSerializer, CommentSerializer


class TicketListCreateView(generics.ListCreateAPIView):
    serializer_class = TicketSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        member = self.request.user.member          # resolve request -> member
        org_tickets = Ticket.objects.filter(organization=member.organization)  # tenant isolation
        if member.role == 'customer':
            return org_tickets.filter(requester=member)   # RBAC: customer sees only their own
        return org_tickets                          # owner/agent see all org tickets


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
        # scope tickets to the member's org — this is the safety check
        org_tickets = Ticket.objects.filter(organization=member.organization)
        if member.role == 'customer':
            org_tickets = org_tickets.filter(requester=member)
        try:
            return org_tickets.get(pk=self.kwargs['ticket_id'])
        except Ticket.DoesNotExist:
            raise NotFound("Ticket not found")   # 404 if not in their scope

    def get_queryset(self):
        ticket = self.get_ticket()
        return ticket.comments.all()

    def perform_create(self, serializer):
        ticket = self.get_ticket()
        serializer.save(ticket=ticket, author=self.request.user.member)