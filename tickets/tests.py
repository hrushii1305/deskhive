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