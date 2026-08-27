# DeskHive — Multi-Tenant Helpdesk SaaS

A production-deployed, multi-tenant B2B helpdesk platform built with Django and Django REST Framework. Multiple independent organizations manage their support operations on a single application instance, with strict data isolation and role-based access control enforced at the API layer.

**Live demo:** https://deskhive-production.up.railway.app
**API docs (Swagger):** https://deskhive-production.up.railway.app/api/docs/

![CI](https://github.com/hrushii1305/deskhive/actions/workflows/ci.yml/badge.svg)

---

## Overview

DeskHive lets multiple companies (tenants) run their customer support on one deployed instance while guaranteeing that no organization can ever see another's data. Each request is scoped to the authenticated user's organization, and within that organization, a user's role (Owner, Agent, or Customer) determines exactly what they can see and do.

New organizations self-register through a public endpoint — the registrant becomes the Owner. The project was built in phases: a shippable, deployed core first, with features layered on top of the live application.

---

## Key Features

- **Multi-tenancy with enforced data isolation** — every query is scoped to the requesting user's organization; cross-tenant access is impossible through the API.
- **Role-Based Access Control (RBAC)** — three roles with distinct permissions:
  - *Owner* — full organization control, sees all tickets.
  - *Agent* — works the shared ticket queue: views all org tickets, transitions states, comments, claims tickets.
  - *Customer* — restricted to only the tickets they personally raised.
- **Self-service registration** — public signup creates a new organization with the registrant as its Owner; passwords are hashed, and account creation is wrapped in a database transaction so it either fully succeeds or rolls back.
- **Concurrency-safe ticket claiming** — agents claim unassigned tickets; a database transaction with `select_for_update()` (row-level locking) prevents two agents claiming the same ticket at once. The first request locks the row and assigns it; a competing request waits, sees it's taken, and is refused with HTTP 409.
- **Automatic ticket assignment** — new tickets are auto-assigned to the least-loaded agent, found in a single query via a filtered `annotate(Count(...))` that counts each agent's active tickets (avoiding N+1 queries).
- **Asynchronous email notifications (Celery)** — ticket creation and assignment trigger background Celery tasks to send emails, so requests return immediately instead of blocking on delivery.
- **Scheduled SLA escalation (Celery Beat)** — a scheduled task periodically finds stale (long-unresolved) tickets and escalates them.
- **Real-time updates (WebSockets)** — Django Channels with a Redis channel layer pushes live ticket updates to connected clients over WebSockets. *(Runs locally; production deployment is on the roadmap.)*
- **Full REST API** — complete CRUD for tickets plus a nested, security-hardened comment system.
- **Interactive API docs** — auto-generated OpenAPI / Swagger UI (drf-spectacular).
- **CI pipeline** — GitHub Actions runs the test suite on every push.
- **Styled web frontend** — a vanilla-JS UI (login, role-scoped ticket list, ticket detail with claim + comment thread, logout) served by Django.

---

## Architecture

### Data Model

| Model | Purpose | Key Relationships |
|-------|---------|-------------------|
| **Organization** | The tenant | Has many Members and Tickets |
| **Member** | A person in an org (Owner/Agent/Customer) | Linked one-to-one to a Django auth User; belongs to an Organization |
| **Ticket** | A support request | Belongs to an Organization; has an assigned Agent and a Customer requester |
| **Comment** | A message on a ticket | Belongs to a Ticket; written by a Member |

### Design Decisions

- **`on_delete` per relationship:** Deleting an Organization cascades to its Members and Tickets (the data is meaningless without the tenant). Deleting a Member sets their Tickets' and Comments' references to null (the records outlive the person — history is preserved).
- **Tenant isolation in `get_queryset`:** Views resolve `request.user.member` → filter all data to `member.organization`. Customers are further narrowed to their own tickets. This is defence-in-depth — isolation lives in the query layer, not just the models.
- **Concurrency control:** Claiming a ticket is a read-then-write that would race under load. It runs inside `transaction.atomic()` with `select_for_update()`, so the database serialises competing claims into a queue instead of letting both succeed.
- **Secure registration:** Public signup creates the User, Organization, and Member together inside a single atomic transaction, so a failure never leaves an orphaned account. A user can only ever become Owner of an organization they create — they can't inject themselves into an existing one.
- **Secure nested resources:** Comments live at `/api/tickets/<id>/comments/`. The parent ticket and the comment's author are derived server-side (from the URL and the authenticated user) and validated against the org-scoped queryset — never trusted from the request body — preventing broken object-level authorization.
- **Auth split:** the REST API uses stateless JWT; WebSockets use session auth, because browsers can't easily attach a custom Authorization header to a WebSocket handshake.

---

## Tech Stack

- **Backend:** Python, Django 5.2, Django REST Framework
- **Authentication:** djangorestframework-simplejwt (JWT) for the API; session auth for WebSockets
- **Database:** PostgreSQL (production) / SQLite (local)
- **Async tasks & scheduling:** Celery + Celery Beat (Redis broker)
- **Real-time:** Django Channels + Redis channel layer
- **Server & static:** Gunicorn + WhiteNoise
- **API docs:** drf-spectacular (OpenAPI / Swagger)
- **CI:** GitHub Actions
- **Testing:** pytest + pytest-django
- **Deployment:** Railway
- **Config:** Environment-based (12-factor) — all secrets and environment-specific settings externalized

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/register/` | Public signup — creates a new organization and its Owner account |
| `POST` | `/api/token/` | Obtain JWT access + refresh tokens (login) |
| `POST` | `/api/token/refresh/` | Refresh an expired access token |
| `GET` `POST` | `/api/tickets/` | List org tickets / create a ticket |
| `GET` `PUT` `PATCH` `DELETE` | `/api/tickets/<id>/` | Retrieve / update / delete a ticket |
| `POST` | `/api/tickets/<id>/claim/` | Claim an unassigned ticket (row-level locked) |
| `GET` `POST` | `/api/tickets/<id>/comments/` | List / add comments on a ticket |
| `GET` | `/api/docs/` | Interactive Swagger UI |

Registration is public; all ticket and comment endpoints require a valid JWT (`Authorization: Bearer <token>`) and return only data within the authenticated user's organization.

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

# Create a .env file with:
#   SECRET_KEY=your-secret-key
#   DEBUG=True

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

The app runs at `http://127.0.0.1:8000/` using SQLite locally. Production settings (Postgres, DEBUG off, allowed hosts) activate automatically via environment variables.

## Testing

```bash
pytest
```

---

## Roadmap

The core (above) is built and deployed. Planned next:

- **Immutable audit log** for ticket state changes (who changed what, append-only)
- **Multi-role onboarding with an approval workflow** — customers self-register into an existing org; agents request to join and are approved by the org's Owner (with email notification to the Owner)
- **File attachments** via S3 pre-signed URLs
- **WebSocket real-time in production** (Redis + ASGI server on the host)

---

Built by [Hrushi](https://github.com/hrushii1305).