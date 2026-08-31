# DeskHive — Multi-Tenant Helpdesk SaaS

A production-deployed, multi-tenant B2B helpdesk platform built with Django and Django REST Framework. Multiple independent organizations manage their support operations on a single application instance, with strict data isolation and role-based access control enforced at the API layer.

**Live demo:** https://deskhive-production.up.railway.app
**API docs (Swagger):** https://deskhive-production.up.railway.app/api/docs/

![CI](https://github.com/hrushii1305/deskhive/actions/workflows/ci.yml/badge.svg)

---

## Overview

DeskHive lets multiple companies (tenants) run their customer support on one deployed instance while guaranteeing that no organization can ever see another's data. Each request is scoped to the authenticated user's organization, and within that organization, a user's role (Owner, Agent, or Customer) determines exactly what they can see and do.

The platform supports full multi-role onboarding: organizations self-register (the registrant becomes Owner), customers self-register into an existing organization, and agents request to join and are approved by the org's Owner. It was built in phases — a shippable, deployed core first, with features layered on top of the live application.

---

## Key Features

- **Multi-tenancy with enforced data isolation** — every query is scoped to the requesting user's organization; cross-tenant access is impossible through the API.
- **Role-Based Access Control (RBAC)** — three roles with distinct permissions:
  - *Owner* — full organization control, sees all tickets, approves agent join requests.
  - *Agent* — works the shared ticket queue: views all org tickets, transitions states, comments, claims tickets.
  - *Customer* — restricted to only the tickets they personally raised.
- **Multi-role onboarding with an approval workflow:**
  - Owners self-register and create a new organization.
  - Customers self-register into an existing organization (immediate access).
  - Agents *request* to join an existing organization and are created in a `pending` state; the org Owner approves or rejects, and an access guard blocks pending agents from any app data until approved. Roles are forced server-side to prevent privilege escalation, and approvals are tenant-scoped so an Owner can only approve agents in their own organization.
- **Concurrency-safe ticket claiming** — agents claim unassigned tickets; a database transaction with `select_for_update()` (row-level locking) prevents two agents claiming the same ticket at once. The first request locks the row and assigns it; a competing request waits, sees it's taken, and is refused with HTTP 409.
- **Automatic ticket assignment** — new tickets are auto-assigned to the least-loaded agent, found in a single query via a filtered `annotate(Count(...))` that counts each agent's active tickets (avoiding N+1 queries).
- **Immutable audit log** — every ticket state change (claim, auto-assignment, status change) is recorded in an append-only audit log capturing the actor, action, and old→new values. Entries are never modified or deleted.
- **Asynchronous email notifications (Celery)** — ticket creation/assignment and agent join/approval events trigger background Celery tasks that send real emails (SMTP), so requests return immediately instead of blocking on delivery.
- **Scheduled SLA escalation (Celery Beat)** — a scheduled task periodically finds stale (long-unresolved) tickets and escalates them.
- **Real-time updates (WebSockets)** — Django Channels with a Redis channel layer pushes live ticket updates to connected clients over WebSockets. *(Runs locally; production deployment is on the roadmap.)*
- **Full REST API** — complete CRUD for tickets plus a nested, security-hardened comment system.
- **Interactive API docs** — auto-generated OpenAPI / Swagger UI (drf-spectacular).
- **CI pipeline** — GitHub Actions runs the full test suite (21 tests) on every push.
- **Styled web frontend** — a vanilla-JS UI: login, role-scoped ticket list, ticket detail with claim + comment thread, signup (role picker + org dropdown), pending-approval screen, owner approvals page, and role-aware navigation.

---

## Architecture

### Data Model

| Model | Purpose | Key Relationships |
|-------|---------|-------------------|
| **Organization** | The tenant | Has many Members and Tickets |
| **Member** | A person in an org (Owner/Agent/Customer), with a status (pending/approved/rejected) | Linked one-to-one to a Django auth User; belongs to an Organization |
| **Ticket** | A support request | Belongs to an Organization; has an assigned Agent and a Customer requester |
| **Comment** | A message on a ticket | Belongs to a Ticket; written by a Member |
| **TicketAuditLog** | An append-only record of a ticket state change | Belongs to a Ticket; references the acting Member |

### Design Decisions

- **`on_delete` per relationship:** Deleting an Organization cascades to its Members and Tickets (the data is meaningless without the tenant). Deleting a Member sets their Tickets' and Comments' references to null (the records outlive the person — history is preserved).
- **Tenant isolation in `get_queryset`:** Views resolve `request.user.member` → filter all data to `member.organization`. Customers are further narrowed to their own tickets. This is defence-in-depth — isolation lives in the query layer, not just the models.
- **Role & status forced server-side:** Registration and join-request endpoints never trust a role or status from the client — they are set on the server. This prevents a user from signing up as an Owner or self-approving as an Agent.
- **Tenant-scoped approvals:** The approval endpoints require the Owner role *and* scope the query to the Owner's own organization, so an Owner cannot see or approve agents belonging to another organization.
- **Access guard:** A permission class blocks members whose status is not `approved` from accessing app data, so a pending agent can authenticate but sees nothing until an Owner approves them.
- **Concurrency control:** Claiming a ticket is a read-then-write that would race under load. It runs inside `transaction.atomic()` with `select_for_update()`, so the database serialises competing claims instead of letting both succeed.
- **Secure registration:** Public signup creates the User, Organization, and Member together inside a single atomic transaction, so a failure never leaves an orphaned account.
- **Secure nested resources:** Comments live at `/api/tickets/<id>/comments/`. The parent ticket and the comment's author are derived server-side and validated against the org-scoped queryset — never trusted from the request body — preventing broken object-level authorization.
- **Best-effort notifications:** Email tasks are dispatched but never block or fail the core request; a broker/SMTP outage cannot break a ticket creation or an approval.
- **Auth split:** the REST API uses stateless JWT; WebSockets use session auth, because browsers can't easily attach a custom Authorization header to a WebSocket handshake.
- **12-factor config:** all secrets and environment-specific settings (SECRET_KEY, database, email credentials) come from environment variables — never hardcoded.

---

## Tech Stack

- **Backend:** Python, Django 5.2, Django REST Framework
- **Authentication:** djangorestframework-simplejwt (JWT) for the API; session auth for WebSockets
- **Database:** PostgreSQL (production) / SQLite (local)
- **Async tasks & scheduling:** Celery + Celery Beat (Redis broker)
- **Real-time:** Django Channels + Redis channel layer
- **Email:** SMTP (real delivery) via Celery, console backend in dev
- **Server & static:** Gunicorn + WhiteNoise
- **API docs:** drf-spectacular (OpenAPI / Swagger)
- **CI:** GitHub Actions
- **Testing:** pytest + pytest-django (21 tests)
- **Deployment:** Railway

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `GET` | `/api/organizations/` | Public list of organizations (for signup) |
| `POST` | `/api/register/` | Public signup — creates a new organization and its Owner |
| `POST` | `/api/register/customer/` | Public — register a Customer into an existing org (role forced) |
| `POST` | `/api/register/agent/` | Public — request to join an existing org as an Agent (pending) |
| `GET` | `/api/pending-agents/` | Owner-only — list pending agent requests in the Owner's org |
| `POST` | `/api/pending-agents/<id>/approve/` | Owner-only — approve a pending agent (org-scoped) |
| `POST` | `/api/pending-agents/<id>/reject/` | Owner-only — reject a pending agent (org-scoped) |
| `GET` | `/api/me/` | Current user's member info (role/status) for role-aware UI |
| `POST` | `/api/token/` | Obtain JWT access + refresh tokens (login) |
| `POST` | `/api/token/refresh/` | Refresh an expired access token |
| `GET` `POST` | `/api/tickets/` | List org tickets / create a ticket |
| `GET` `PUT` `PATCH` `DELETE` | `/api/tickets/<id>/` | Retrieve / update / delete a ticket |
| `POST` | `/api/tickets/<id>/claim/` | Claim an unassigned ticket (row-level locked) |
| `GET` `POST` | `/api/tickets/<id>/comments/` | List / add comments on a ticket |
| `GET` | `/api/docs/` | Interactive Swagger UI |

Registration and the org list are public; all other endpoints require a valid JWT (`Authorization: Bearer <token>`) and return only data within the authenticated user's organization.

---

## Local Setup

```bash
# Clone and enter the project
git clone https://github.com/hrushii1305/deskhive.git
cd deskhive

# Create and activate a virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# Install dependencies
pip install -r requirements.txt

# Create a .env file with (example):
#   SECRET_KEY=your-secret-key
#   DEBUG=True
#   # Optional — real email; omit to use the console backend:
#   EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
#   EMAIL_HOST_USER=your@gmail.com
#   EMAIL_HOST_PASSWORD=your-app-password
#   DEFAULT_FROM_EMAIL=DeskHive <your@gmail.com>

# Redis (for Celery + Channels), e.g. via Docker:
docker run -d -p 6380:6379 --name deskhive-redis redis:7

# Run migrations and create an admin user
python manage.py migrate
python manage.py createsuperuser

# Start the development server
python manage.py runserver

# For async features, in separate terminals:
celery -A deskhive worker --loglevel=info --pool=solo
celery -A deskhive beat --loglevel=info
```

The app runs at `http://127.0.0.1:8000/` using SQLite locally. Production settings (Postgres, DEBUG off, allowed hosts, email) activate automatically via environment variables.

## Testing

```bash
pytest
```

Tests cover authentication, tenant isolation, RBAC, ticket claiming (200/409), the audit log, and the onboarding/approval workflow — including security cases (privilege-escalation guard, cross-org approval block, and the pending-agent access guard).

---

## Roadmap

The core (above) is built, tested, and deployed. Planned next:

- **File attachments** via S3 pre-signed URLs
- **WebSocket real-time in production** (Redis + ASGI server on the host)

---

Built by [Hrushi](https://github.com/hrushii1305).