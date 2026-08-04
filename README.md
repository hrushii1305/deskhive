# DeskHive — Multi-Tenant Helpdesk SaaS

A production-deployed, multi-tenant B2B helpdesk platform built with Django and Django REST Framework. Multiple independent organizations manage their support operations on a single application instance, with strict data isolation and role-based access control enforced at the API layer.

**Live demo:** https://deskhive-production.up.railway.app
**API root:** https://deskhive-production.up.railway.app/api/tickets/

---

## Overview

DeskHive lets multiple companies (tenants) run their customer support on one deployed instance while guaranteeing that no organization can ever see another's data. Each request is scoped to the authenticated user's organization, and within that organization, a user's role (Owner, Agent, or Customer) determines exactly what they can see and do.

The project was built in phases: a shippable, deployed core first, with advanced features layered on top of the live application.

---

## Key Features

- **Multi-tenancy with enforced data isolation** — every query is scoped to the requesting user's organization; cross-tenant access is impossible through the API.
- **Role-Based Access Control (RBAC)** — three roles with distinct permissions:
  - *Owner/Admin* — full organization control, manages members and settings, sees all tickets.
  - *Agent* — works the shared ticket queue: views all org tickets, transitions states, comments.
  - *Customer* — restricted to only the tickets they personally raised.
- **JWT authentication** — stateless, short-lived access tokens (no server-side session storage), enabling horizontal scalability.
- **Full REST API** — complete CRUD for tickets plus a nested, security-hardened comment system.
- **Ticket lifecycle** — status workflow (Open → In Progress → Resolved → Closed) with priority levels.
- **Threaded comments** — conversation on each ticket, with author and ticket derived server-side to prevent authorization bypass.

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
- **Tenant isolation in `get_queryset`:** Views resolve `request.user.member` → filter all data to `member.organization`. Customers are further narrowed to their own tickets.
- **Secure nested resources:** Comments live at `/api/tickets/<id>/comments/`. The parent ticket is derived from the URL and validated against the org-scoped queryset — never trusted from the request body — preventing broken object-level authorization.

---

## Tech Stack

- **Backend:** Python, Django 5.2, Django REST Framework
- **Authentication:** djangorestframework-simplejwt (JWT)
- **Database:** PostgreSQL (production) / SQLite (local)
- **Server:** Gunicorn + WhiteNoise (static files)
- **Deployment:** Railway
- **Config:** Environment-based (12-factor) — all secrets and environment-specific settings externalized

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/api/token/` | Obtain JWT access + refresh tokens (login) |
| `POST` | `/api/token/refresh/` | Refresh an expired access token |
| `GET` `POST` | `/api/tickets/` | List org tickets / create a ticket |
| `GET` `PUT` `PATCH` `DELETE` | `/api/tickets/<id>/` | Retrieve / update / delete a ticket |
| `GET` `POST` | `/api/tickets/<id>/comments/` | List / add comments on a ticket |

All ticket and comment endpoints require a valid JWT (`Authorization: Bearer <token>`) and return only data within the authenticated user's organization.

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

# Run migrations and create an admin user
python manage.py migrate
python manage.py createsuperuser

# Start the development server
python manage.py runserver
```

The app runs at `http://127.0.0.1:8000/` using SQLite locally. Production settings (Postgres, DEBUG off, allowed hosts) activate automatically via environment variables.

---

## Roadmap

Phase 2 (in progress, on the live app):
- Asynchronous email notifications (Celery)
- Scheduled SLA escalation (Celery Beat)
- Immutable audit log for ticket state changes
- Concurrency handling with row-level locking (prevents double-claiming tickets)
- Real-time updates via WebSockets and Redis Pub/Sub
- File attachments via S3 pre-signed URLs

---

Built by [Hrushi](https://github.com/hrushii1305).