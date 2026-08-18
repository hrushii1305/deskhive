from celery import shared_task
from django.core.mail import send_mail
from django.conf import settings
from .models import Ticket


@shared_task
def send_ticket_created_email(ticket_id):
    """Confirm to the requester that their ticket was received."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return

    if not ticket.requester or not ticket.requester.email:
        return

    send_mail(
        subject=f"[DeskHive] Ticket #{ticket.id} received: {ticket.title}",
        message=(
            f"Hi {ticket.requester.name},\n\n"
            f"We've received your ticket:\n\n"
            f"  #{ticket.id} — {ticket.title}\n"
            f"  Status: {ticket.status}\n"
            f"  Priority: {ticket.priority}\n\n"
            f"Our team will get back to you shortly.\n\n"
            f"— {ticket.organization.name} Support"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.requester.email],
        fail_silently=False,
    )


@shared_task
def send_ticket_assigned_email(ticket_id):
    """Tell the agent that a ticket has been assigned to them."""
    try:
        ticket = Ticket.objects.get(id=ticket_id)
    except Ticket.DoesNotExist:
        return

    if not ticket.assigned_to or not ticket.assigned_to.email:
        return

    raised_by = ticket.requester.name if ticket.requester else "Unknown"

    send_mail(
        subject=f"[DeskHive] Ticket #{ticket.id} assigned to you: {ticket.title}",
        message=(
            f"Hi {ticket.assigned_to.name},\n\n"
            f"A ticket has been assigned to you:\n\n"
            f"  Ticket ID : #{ticket.id}\n"
            f"  Title     : {ticket.title}\n"
            f"  Priority  : {ticket.priority}\n"
            f"  Raised by : {raised_by}\n\n"
            f"Description:\n{ticket.description}\n\n"
            f"— {ticket.organization.name} Support"
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[ticket.assigned_to.email],
        fail_silently=False,
    )