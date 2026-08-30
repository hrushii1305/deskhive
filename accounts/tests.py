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
    
    
    
    
# ---------- Agent approval workflow tests ----------

@pytest.fixture
def owner_and_org(db):
    org = Organization.objects.create(name="Approval Org", slug="approval-org")
    user = User.objects.create_user(username="approwner", password="pass12345")
    owner = Member.objects.create(
        user=user, organization=org,
        name="Appr Owner", email="approwner@x.com",
        role="owner", status="approved",
    )
    return owner, org


@pytest.fixture
def pending_agent(db, owner_and_org):
    _, org = owner_and_org
    user = User.objects.create_user(username="pendagent", password="pass12345")
    return Member.objects.create(
        user=user, organization=org,
        name="Pending Agent", email="pendagent@x.com",
        role="agent", status="pending",
    )


@pytest.mark.django_db
def test_agent_join_request_creates_pending_agent(client, owner_and_org):
    """An agent join request creates a member with role=agent, status=pending."""
    _, org = owner_and_org
    response = client.post("/api/register/agent/", {
        "username": "newagent",
        "password": "pass12345",
        "email": "newagent@x.com",
        "name": "New Agent",
        "organization_id": org.id,
    }, format="json")

    assert response.status_code == 201
    assert response.data["role"] == "agent"
    assert response.data["status"] == "pending"

    member = Member.objects.get(user__username="newagent")
    assert member.role == "agent"
    assert member.status == "pending"


@pytest.mark.django_db
def test_owner_can_list_and_approve_pending_agent(client, owner_and_org, pending_agent):
    """Owner lists pending agents in their org and approves one."""
    owner, _ = owner_and_org
    client.force_authenticate(user=owner.user)

    # list
    r = client.get("/api/pending-agents/")
    assert r.status_code == 200
    assert len(r.data) == 1
    assert r.data[0]["id"] == pending_agent.id

    # approve
    r = client.post(f"/api/pending-agents/{pending_agent.id}/approve/")
    assert r.status_code == 200

    pending_agent.refresh_from_db()
    assert pending_agent.status == "approved"


@pytest.mark.django_db
def test_owner_cannot_approve_agent_in_another_org(client, pending_agent, db):
    """
    SECURITY: an owner of a DIFFERENT org cannot approve this pending agent.
    Tenant isolation on the approval endpoint.
    """
    # a second org with its own owner
    other_org = Organization.objects.create(name="Other Org", slug="other-org")
    other_user = User.objects.create_user(username="otherowner", password="pass12345")
    other_owner = Member.objects.create(
        user=other_user, organization=other_org,
        name="Other Owner", email="otherowner@x.com",
        role="owner", status="approved",
    )

    client.force_authenticate(user=other_owner.user)
    r = client.post(f"/api/pending-agents/{pending_agent.id}/approve/")

    assert r.status_code == 404          # can't even see it — not in their org
    pending_agent.refresh_from_db()
    assert pending_agent.status == "pending"   # unchanged


@pytest.mark.django_db
def test_non_owner_cannot_access_pending_agents(client, pending_agent):
    """SECURITY: a non-owner (the pending agent themselves) can't list pending agents."""
    client.force_authenticate(user=pending_agent.user)
    r = client.get("/api/pending-agents/")
    assert r.status_code == 403          # not an owner


@pytest.mark.django_db
def test_pending_agent_blocked_from_tickets(client, pending_agent):
    """SECURITY: a pending agent cannot access tickets until approved."""
    client.force_authenticate(user=pending_agent.user)
    r = client.get("/api/tickets/")
    assert r.status_code == 403          # access guard blocks pending

    # after approval, they get in
    pending_agent.status = "approved"
    pending_agent.save()
    r = client.get("/api/tickets/")
    assert r.status_code == 200
    
    
@pytest.mark.django_db
def test_registration_rejects_duplicate_email(client, existing_org):
    """
    A second signup with an already-registered email returns a clean 400,
    not a 500 crash (Member.email is unique).
    """
    # first customer registers with an email
    r1 = client.post("/api/register/customer/", {
        "username": "firstuser",
        "password": "pass12345",
        "email": "dupe@example.com",
        "name": "First User",
        "organization_id": existing_org.id,
    }, format="json")
    assert r1.status_code == 201

    # second signup reuses the same email -> clean validation error
    r2 = client.post("/api/register/customer/", {
        "username": "seconduser",
        "password": "pass12345",
        "email": "dupe@example.com",       # duplicate
        "name": "Second User",
        "organization_id": existing_org.id,
    }, format="json")
    assert r2.status_code == 400          # not 500 — validation caught it
    assert "email" in r2.data