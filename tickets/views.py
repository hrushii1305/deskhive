from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .models import Ticket
from .serializers import TicketSerializer


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