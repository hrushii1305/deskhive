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