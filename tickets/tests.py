import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from organizations.models import Organization
from accounts.models import Member
from tickets.models import Ticket


@pytest.fixture
def client():
    return APIClient()


@pytest.fixture
def org_a(db):
    return Organization.objects.create(name="Clinic A", slug="clinic-a")


@pytest.fixture
def org_b(db):
    return Organization.objects.create(name="Clinic B", slug="clinic-b")


@pytest.fixture
def owner_a(db, org_a):
    user = User.objects.create_user(username="owner_a", password="pass12345")
    return Member.objects.create(
        user=user, organization=org_a,
        name="Owner A", email="owner_a@a.com", role="owner",
    )


@pytest.fixture
def customer_a(db, org_a):
    user = User.objects.create_user(username="cust_a", password="pass12345")
    return Member.objects.create(
        user=user, organization=org_a,
        name="Customer A", email="cust_a@a.com", role="customer",
    )


@pytest.fixture
def owner_b(db, org_b):
    user = User.objects.create_user(username="owner_b", password="pass12345")
    return Member.objects.create(
        user=user, organization=org_b,
        name="Owner B", email="owner_b@b.com", role="owner",
    )


@pytest.fixture
def tickets_a(db, org_a, customer_a):
    """Two tickets in Org A: one raised by customer_a, one by nobody."""
    t1 = Ticket.objects.create(
        organization=org_a, title="A - customer ticket",
        description="x", requester=customer_a,
    )
    t2 = Ticket.objects.create(
        organization=org_a, title="A - other ticket", description="y",
    )
    return [t1, t2]


@pytest.fixture
def ticket_b(db, org_b):
    return Ticket.objects.create(
        organization=org_b, title="B - secret ticket", description="z",
    )


# ---------- Tests ----------

@pytest.mark.django_db
def test_tickets_require_authentication(client):
    """An unauthenticated request must be rejected with 401."""
    response = client.get("/api/tickets/")
    assert response.status_code == 401


@pytest.mark.django_db
def test_tenant_isolation(client, owner_b, tickets_a, ticket_b):
    client.force_authenticate(user=owner_b.user)
    response = client.get("/api/tickets/")
    assert response.status_code == 200
    assert len(response.data) == 1                       # only Org B's ticket

    titles = [t["title"] for t in response.data]
    assert "B - secret ticket" in titles                 # sees its own
    assert not any(t.startswith("A - ") for t in titles)
    
    
@pytest.mark.django_db
def test_customer_sees_only_own_tickets(client, customer_a, tickets_a):
    """Org A has 2 tickets; the customer raised only 1 of them."""
    client.force_authenticate(user=customer_a.user)
    response = client.get("/api/tickets/")

    assert response.status_code == 200
    assert len(response.data) == 1
    assert response.data[0]["title"] == "A - customer ticket"


@pytest.mark.django_db
def test_owner_sees_all_org_tickets(client, owner_a, tickets_a):
    """The owner of Org A sees both of its tickets."""
    client.force_authenticate(user=owner_a.user)
    response = client.get("/api/tickets/")

    assert response.status_code == 200
    assert len(response.data) == 2
    
    
# ---------- Claim + Audit Log fixtures ----------

@pytest.fixture
def agent_a(db, org_a):
    user = User.objects.create_user(username="agent_a", password="pass12345")
    return Member.objects.create(
        user=user, organization=org_a,
        name="Agent A", email="agent_a@a.com", role="agent",
    )


@pytest.fixture
def unclaimed_ticket_a(db, org_a, customer_a):
    """An open, unassigned ticket in Org A, ready to be claimed."""
    return Ticket.objects.create(
        organization=org_a,
        title="A - unclaimed",
        description="needs an agent",
        requester=customer_a,
        status="open",
    )


# ---------- Claim + Audit Log tests ----------

@pytest.mark.django_db
def test_agent_can_claim_unassigned_ticket(client, agent_a, unclaimed_ticket_a):
    """Claiming an open ticket returns 200 and assigns it to the agent."""
    client.force_authenticate(user=agent_a.user)
    response = client.post(f"/api/tickets/{unclaimed_ticket_a.id}/claim/")

    assert response.status_code == 200

    unclaimed_ticket_a.refresh_from_db()
    assert unclaimed_ticket_a.assigned_to == agent_a
    assert unclaimed_ticket_a.status == "in_progress"


@pytest.mark.django_db
def test_claiming_already_claimed_ticket_returns_409(client, agent_a, unclaimed_ticket_a):
    """A second claim on the same ticket is refused with 409 (locking guard)."""
    client.force_authenticate(user=agent_a.user)

    # first claim succeeds
    first = client.post(f"/api/tickets/{unclaimed_ticket_a.id}/claim/")
    assert first.status_code == 200

    # second claim on the now-claimed ticket is refused
    second = client.post(f"/api/tickets/{unclaimed_ticket_a.id}/claim/")
    assert second.status_code == 409


@pytest.mark.django_db
def test_claiming_writes_audit_log_entry(client, agent_a, unclaimed_ticket_a):
    """A successful claim creates exactly one immutable audit-log entry."""
    from tickets.models import TicketAuditLog

    client.force_authenticate(user=agent_a.user)
    client.post(f"/api/tickets/{unclaimed_ticket_a.id}/claim/")

    entries = TicketAuditLog.objects.filter(ticket=unclaimed_ticket_a)
    assert entries.count() == 1

    entry = entries.first()
    assert entry.action == "claimed"
    assert entry.actor == agent_a
    assert entry.old_value == "open"
    assert entry.new_value == "in_progress"
    

@pytest.mark.django_db
def test_auto_assignment_writes_audit_log(client, org_a, agent_a, customer_a):
    """Creating a ticket auto-assigns it to an agent and logs that assignment."""
    from tickets.models import TicketAuditLog

    # customer creates a ticket; with an agent in the org, it auto-assigns
    client.force_authenticate(user=customer_a.user)
    response = client.post("/api/tickets/", {
        "title": "New ticket",
        "description": "please help",
    })
    assert response.status_code == 201

    ticket_id = response.data["id"]
    entries = TicketAuditLog.objects.filter(ticket_id=ticket_id, action="auto_assigned")
    assert entries.count() == 1
    assert entries.first().new_value == str(agent_a)


@pytest.mark.django_db
def test_status_change_writes_audit_log(client, org_a, owner_a, unclaimed_ticket_a):
    """Updating a ticket's status writes a status_changed audit entry."""
    from tickets.models import TicketAuditLog

    client.force_authenticate(user=owner_a.user)
    response = client.patch(
        f"/api/tickets/{unclaimed_ticket_a.id}/",
        {"status": "resolved"},
    )
    assert response.status_code == 200

    entries = TicketAuditLog.objects.filter(
        ticket=unclaimed_ticket_a, action="status_changed"
    )
    assert entries.count() == 1
    entry = entries.first()
    assert entry.old_value == "open"
    assert entry.new_value == "resolved"