from django.db import models
from organizations.models import Organization


class Member(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('agent', 'Agent'),
        ('customer', 'Customer'),
    ]

    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.role})"

    # --- RBAC permission checks ---
    def is_owner(self):
        return self.role == 'owner'

    def is_agent(self):
        return self.role == 'agent'

    def is_customer(self):
        return self.role == 'customer'

    def can_manage_members(self):
        return self.role == 'owner'

    def can_manage_org_settings(self):
        return self.role == 'owner'

    def can_manage_all_tickets(self):
        return self.role in ('owner', 'agent')

    def can_transition_ticket(self):
        return self.role in ('owner', 'agent')

    def can_create_ticket(self):
        return True

    def can_view_ticket(self, ticket):
        # owners/agents see all org tickets; customers see only tickets they raised
        if self.role in ('owner', 'agent'):
            return True
        return ticket.requester_id == self.id