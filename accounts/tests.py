import pytest
from django.contrib.auth.models import User
from rest_framework.test import APIClient
from organizations.models import Organization
from accounts.models import Member


@pytest.fixture
def client():
    return APIClient()


@pytest.mark.django_db
def test_registration_creates_user_org_and_owner_member(client):
    """A successful signup creates all three linked records, with owner role."""
    payload = {
        "username": "newowner",
        "password": "strongpass123",
        "email": "new@co.com",
        "name": "New Owner",
        "organization_name": "NewCo",
    }
    response = client.post("/api/register/", payload, format="json")

    assert response.status_code == 201
    assert User.objects.filter(username="newowner").exists()
    assert Organization.objects.filter(name="NewCo").exists()

    member = Member.objects.get(email="new@co.com")
    assert member.role == "owner"
    assert member.organization.name == "NewCo"


@pytest.mark.django_db
def test_registration_never_returns_password(client):
    """The password must never appear in the response body."""
    payload = {
        "username": "safeuser",
        "password": "strongpass123",
        "email": "safe@co.com",
        "name": "Safe User",
        "organization_name": "SafeCo",
    }
    response = client.post("/api/register/", payload, format="json")

    assert response.status_code == 201
    assert "password" not in response.data


@pytest.mark.django_db
def test_registration_rejects_duplicate_username(client):
    """Signing up with a taken username must fail validation, not crash."""
    User.objects.create_user(username="taken", password="pass12345")
    payload = {
        "username": "taken",
        "password": "strongpass123",
        "email": "dupe@co.com",
        "name": "Dupe",
        "organization_name": "DupeCo",
    }
    response = client.post("/api/register/", payload, format="json")

    assert response.status_code == 400
    
    
# ---------- Customer registration tests ----------

@pytest.fixture
def existing_org(db):
    return Organization.objects.create(name="Existing Org", slug="existing-org")


@pytest.mark.django_db
def test_customer_can_register_into_existing_org(client, existing_org):
    """A customer signs up into an existing org and is created with role=customer."""
    response = client.post("/api/register/customer/", {
        "username": "newcustomer",
        "password": "pass12345",
        "email": "newcustomer@example.com",
        "name": "New Customer",
        "organization_id": existing_org.id,
    }, format="json")

    assert response.status_code == 201
    assert response.data["role"] == "customer"

    member = Member.objects.get(user__username="newcustomer")
    assert member.role == "customer"
    assert member.organization == existing_org


@pytest.mark.django_db
def test_customer_registration_ignores_injected_role(client, existing_org):
    """
    SECURITY: even if the client sends role='owner', the server forces
    role='customer'. Prevents privilege escalation via the signup endpoint.
    """
    response = client.post("/api/register/customer/", {
        "username": "sneaky",
        "password": "pass12345",
        "email": "sneaky@example.com",
        "name": "Sneaky User",
        "organization_id": existing_org.id,
        "role": "owner",              # attacker tries to become an owner
    }, format="json")

    assert response.status_code == 201

    member = Member.objects.get(user__username="sneaky")
    assert member.role == "customer"      # still a customer — attack failed


@pytest.mark.django_db
def test_customer_registration_rejects_nonexistent_org(client):
    """Can't register into an org that doesn't exist."""
    response = client.post("/api/register/customer/", {
        "username": "someone",
        "password": "pass12345",
        "email": "someone@example.com",
        "name": "Someone",
        "organization_id": 99999,        # no such org
    }, format="json")

    assert response.status_code == 400   # validation error