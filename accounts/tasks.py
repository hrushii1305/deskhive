from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings


@shared_task
def send_agent_request_email(member_id):
    """Notify the org owner that an agent has requested to join."""
    from .models import Member  # imported inside to avoid circular imports

    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return

    org = member.organization
    # find the owner of this org
    owner = Member.objects.filter(organization=org, role='owner').first()
    if not owner or not owner.email:
        return

    send_mail(
        subject=f"New agent request for {org.name}",
        message=(
            f"{member.name} ({member.email}) has requested to join "
            f"{org.name} as an agent.\n\n"
            f"Log in to your dashboard to approve or reject this request."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[owner.email],
        fail_silently=True,
    )
    

@shared_task
def send_agent_decision_email(member_id, decision):
    """Notify an agent that their join request was approved or rejected."""
    from .models import Member
    try:
        member = Member.objects.get(id=member_id)
    except Member.DoesNotExist:
        return
    if not member.email:
        return
    send_mail(
        subject=f"Your request to join {member.organization.name} was {decision}",
        message=(
            f"Hi {member.name},\n\n"
            f"Your request to join {member.organization.name} as an agent "
            f"has been {decision}."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[member.email],
        fail_silently=True,
    )