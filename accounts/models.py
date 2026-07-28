from django.db import models
from organizations.models import Organization


class Member(models.Model):
    ROLE_CHOICES = [
        ('owner', 'Owner'),
        ('agent', 'Agent'),
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