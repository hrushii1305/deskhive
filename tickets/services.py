from django.db.models import Count, Q
from accounts.models import Member


def get_least_loaded_agent(organization):
    agent = Member.objects.filter(
        organization=organization,
        role='agent'
    ).annotate(
        open_count=Count(
            'assigned_tickets',
            filter=Q(assigned_tickets__status__in=['open', 'in_progress'])
        )
    ).order_by('open_count', 'id').first()

    return agent