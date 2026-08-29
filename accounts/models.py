from django.db import models
from organizations.models import Organization
from django.contrib.auth.models import User


class Member(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('agent', 'Agent'),
        ('customer', 'Customer'),
    ]

    STATUS_CHOICES = [
        ('pending', 'Pending'),      # agent has requested to join, awaiting owner approval
        ('approved', 'Approved'),    # active member
        ('rejected', 'Rejected'),    # owner declined the request
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='member'
    )
    organization = models.ForeignKey(
        Organization,
        on_delete=models.CASCADE,
        related_name='members'
    )
    name = models.CharField(max_length=200)
    email = models.EmailField(unique=True)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='agent')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
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

    def is_approved(self):
        return self.status == 'approved'

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
        if self.role in ('owner', 'agent'):
            return True
        return ticket.requester_id == self.id