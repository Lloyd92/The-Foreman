# The Foreman

> *The Foreman serves the craftsman.*

The Foreman is a local-first, deterministic, and explainable external working
memory and continuity system being developed by **HardHead Works**.

Its purpose is simple:

Help builders, makers, craftsmen, and small businesses organize their work without getting in the way of it.

The Foreman preserves operational state and context rather than merely storing
disconnected records. It is designed to replace scattered notebooks,
spreadsheets, sticky notes, and disconnected applications with one organized
command center that can help its owner continue after an interruption instead
of reconstructing the work from memory.

The current system remains useful without AI. Deterministic records, facts,
reason codes, evidence, and source references establish the factual authority;
future decision-support or AI capabilities must build on that foundation
rather than replace it.

---

# Project Status

**Current Version**

v0.7.5 — Frontend Hardening and Browser E2E

Current focus:

- Reconcile the approved v0.8 and v0.9 architecture sequence
- Define Universal Navigation and Spaces before implementation
- Preserve v0.7.5 runtime, data, deployment, and cache behavior
- Document active-Space authority and universal module ownership
- Prepare the nine-commit v0.8.0 implementation plan

---

# Mission

The Foreman exists to reduce operational friction and preserve continuity
across household, workshop, personal, and small-business work.

Instead of spending time searching for information, reconstructing decisions,
remembering dependencies, or manually connecting scattered records, the owner
should be able to focus on meaningful work.

The Foreman preserves context across interruptions. Current operational state
should remain understandable without requiring the owner to remember how
projects, commitments, resources, records, and decisions fit together.

Every feature is designed around one guiding question:

> **Does this provide clarity, preserve continuity, or help complete meaningful work?**

---

# Primary Experience

The current v0.7.5 Dashboard is the implemented application shell and
operational workspace. It is not the target permanent navigation shell.

The target permanent primary navigation is:

- Today
- Calendar
- Work
- Resources
- Money
- Library

Settings and Account remain separate below the primary navigation.

Today is the target default daily workspace. Through v0.8.6, Today presents
authoritative factual current state only. It does not claim feasibility, rank
eligible Work, recommend next actions, or perform capacity-aware scheduling.

The v0.9.2 Morning Briefing becomes the capacity-aware primary daily
experience presented through Today. It is intended to help the owner
understand:

1. What can I realistically accomplish today?
2. What matters most today?
3. What do I need to know before I begin?

Calendar may record commitments, events, routines, recurrence, and
availability before Capacity exists. Capacity must precede automatic
optional-Work placement, feasibility claims, prioritization, recommendations,
and capacity-aware scheduling decisions.

The permanent navigation, Today workspace, Capacity Engine, Priority Engine,
and complete Morning Briefing are not yet implemented.

---

# Core Principles

The Foreman is built around several fundamental ideas.

- Local-first operation
- External working memory and continuity
- Deterministic and explainable facts
- Modular architecture
- Offline capable
- Reliable over flashy
- Simple over complicated
- Built for real workshops
- Designed to grow with the business

For additional information, see:

- `docs/FOUNDERS_LETTER.md`
- `docs/PROJECT_VISION.md`
- `docs/DESIGN_PRINCIPLES.md`

---

# Current Modules

## Dashboard

The current v0.7.5 application shell and operational workspace. It does not
yet provide the target permanent navigation, Today workspace, or complete
Morning Briefing.

Current capabilities:

- System status
- Greeting and date
- Task management workspace
- Inventory alerts
- Project lifecycle, readiness, and Inventory summaries from the normalized
  backend operational-facts response

The full capacity-aware Morning Briefing is not yet implemented.

---

## Tasks

Manage day-to-day work.

Features include:

- SQLite persistence through the backend
- Migration support for retained browser-local task records
- Completion tracking
- Priority levels

---

## Inventory

Track workshop resources.

Current capabilities:

- Add inventory
- Edit inventory
- Delete inventory
- SQLite persistence through the backend
- Migration support for retained browser-local inventory records
- Search
- Filtering
- Sorting
- Backend-authoritative in-stock, low-stock, out-of-stock, and invalid
  classifications

Inventory owns consumable stock, quantities, thresholds, locations, and
usage.

Planned Inventory capabilities:

- Barcode support
- Material forecasting

Purchasing and supplier-management workflows remain deferred specialized
concerns. They may reference Inventory through stable IDs and relationships
without becoming Inventory authority.

---

## Projects

The Projects workspace uses the backend API and SQLite as its
authoritative runtime source. It supports project creation, editing, confirmed
deletion, project cards, progress tracking, summary counts, search, status
filtering, sorting, and persistent material requirements linked to Inventory
records. Project cards and the focused Materials dialog consume normalized
backend material-readiness facts and their evidence without deducting,
reserving, or aggregating inventory across Projects.

Existing browser Projects migrate through a durable, idempotent backend
migration endpoint. Startup migration runs in Inventory → Project → Task order
so material links and Task Project references can be translated safely.
Browser Project storage is intentionally retained as migration evidence and
for compatibility and recovery; it is no longer the Projects page's runtime
authority.

Dashboard and Projects consume the same backend readiness facts. Missing
Inventory references remain visible with unknown availability rather than a
fabricated zero. Deleting a Project clears related Task `projectId`
references, and material requirements whose Inventory items were deleted
remain visible, editable, and removable.

Estimated completion, Project templates, and deeper module integrations remain
planned work.

---

# Unified Operational Facts

v0.7.3 derives one deterministic, backend-authoritative view of current
Project, material, Task, and Inventory state. The backend reads authoritative
SQLite records from one transaction snapshot and returns a versioned
`GET /api/operational-facts` response with normalized facts and summary data.

The implemented fact vocabulary is:

- `project.lifecycle`
- `project.material-readiness`
- `task.work-state`
- `inventory.stock-level`

Each fact has a stable identity, typed state, reason codes, evidence, and
source-record references. Facts are computed on demand and are not persisted.
The operational-fact schema version is 1 while the SQLite database schema
is version 3. The version 3 foundation tables do not change the implemented
operational-fact vocabulary or add `space_id` to existing operational records.

Dashboard, Projects, and Inventory consume these shared facts instead of
independently reconstructing readiness or stock state from quantities.
Browser-local records remain migration and recovery evidence, never
operational fact authority.

This release establishes trustworthy current-state inputs. It does not yet
implement Capacity, Priority, next-action selection, Morning Briefing
narration, or AI.

---

# PWA and Household Deployment

v0.7.2 provides an installable Progressive Web App for the private HardHead
Works household LAN. The manifest, favicon, Apple touch icon, regular icons,
and maskable icons provide the installation identity. The application supports
standalone launch, `viewport-fit=cover`, dynamic safe-area insets, and physical
iPhone Home Screen installation. Trusted HTTPS installation, standalone
launch, backend-authoritative startup, and safe-area behavior have been
accepted on a physical iPhone.

The current v0.7.5 service worker atomically precaches an exact 32-resource
static shell. It does not cache API responses, business records, migrations,
or mutations and does not queue, replay, or synchronize writes. A cached shell
can therefore remain available when HardHead is unavailable, but shell
availability does not mean operational data is available.

`/api/health` is the authoritative operational gate. Normal Projects, Tasks,
and Inventory behavior starts only when HardHead reports both the application
healthy and its database online. Retained browser records are migration
inputs, compatibility evidence, and recovery material only; they are not a
runtime fallback authority. API, migration, and mutation traffic remains
network- and backend-owned.

Service-worker updates remain waiting until the user explicitly applies them.
The update can be deferred, and activation is blocked while a form is dirty or
a dialog is open. The worker does not automatically call `skipWaiting()` or
claim existing clients.

Current access is intentionally restricted:

- `https://192.168.1.184` is the trusted household-LAN origin.
- `http://127.0.0.1:3000` is available only on the tower.
- The backend has no host port and remains private to the Compose network.

Caddy is the private-LAN HTTPS edge. Nginx remains authoritative for static
SPA/PWA delivery and the `/api/` proxy behind Caddy. This deployment is not
exposed to the public Internet. HTTPS protects transport and server identity;
it does not provide user authentication.

Only Caddy's public root certificate is distributed to trusted household
devices. Its private CA keys and certificate state remain protected in
persistent Docker volumes and must not be copied, deleted, or regenerated.
The current origin is the private IP address above. `hardhead.home.arpa`
remains a future LAN-DNS goal, not a currently supported hostname.

---

# Planned Modules and Capabilities

The Foreman is intentionally modular.

Future modules include:

- Budget
- Mealworm Production
- Customer Management
- Purchasing
- Maintenance
- Reporting
- Artificial Intelligence
- Automation

Version 1.0 also requires shared system capabilities including the Morning
Briefing, Capacity Engine, explainable recommendations, continued persistence
and testing maturity, and backup and restore.

Backup, export, restore, and verification are implemented in v0.7.4.
Frontend hardening and verified browser-E2E acceptance are implemented in
v0.7.5. Next-action identification and Morning Briefing narration remain
future capabilities. AI is not part of v0.7.5.

See `ROADMAP.md` for additional details.

---

# Technology Stack

## Current Implementation

Frontend

- HTML5
- CSS3
- JavaScript (ES Modules)

Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Uvicorn

Database

- SQLite

Infrastructure

- Docker
- Docker Compose
- Nginx
- Caddy private-LAN TLS gateway

Version Control

- Git

Development Environment

- Linux (Xubuntu)

Tasks, Inventory, and Projects use backend SQLite persistence. Browser-local
records remain available only to migration, compatibility, evidence, and
recovery paths; they are not runtime fallback stores. Dashboard, Projects,
and Inventory use the backend operational-facts API as the authority for
current lifecycle, readiness, and stock classifications.

The backend currently provides validated APIs for system status, Inventory,
Projects, Project materials, Tasks, browser-data migration, and operational
facts. Its service, repository, Pydantic schema, SQLAlchemy model, SQLite
persistence, versioned schema-upgrade, and automated-test foundations are
implemented. Capacity, Priority, the complete Morning Briefing, and scheduled
backup automation remain target work.

## Version 1.0 Target

Frontend

- HTML5
- CSS3
- JavaScript (ES Modules)

Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy

Database

- SQLite

Deployment

- Docker
- Docker Compose
- Nginx

Architecture defines the Version 1.0 target. Differences between this target
and the current implementation represent incomplete implementation or an
architectural decision that requires review; the implementation does not
silently override the documented target.

---

# Project Structure

## Current Structure

```
Foreman/

├── backend/
│   ├── app/
│   │   ├── api/         # FastAPI routes
│   │   ├── core/        # Configuration and database sessions
│   │   ├── models/      # SQLAlchemy persistence models
│   │   ├── repositories/ # Database access
│   │   ├── schemas/     # Pydantic request and response schemas
│   │   ├── services/    # Business logic
│   │   └── main.py
│   └── tests/           # Backend API tests
├── database/           # Placeholder for persistent storage
├── docker/             # Current Caddy private-LAN TLS configuration
├── docs/
│   └── AGENTS.md       # Contributor and AI-agent instructions
├── frontend/           # HTML, CSS, and JavaScript application
├── scripts/            # Browser E2E, disposable acceptance, restore validation
├── compose.yaml
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
└── ROADMAP.md
```

The implemented backend foundation includes API, service, repository, model,
schema, SQLite, and test layers. The operational scripts support browser-E2E
execution, disposable acceptance, and isolated restore round-trip validation.
The remaining planned capabilities are documented in `ARCHITECTURE.md`.

---

# Running The Foreman

Clone the repository.

```
git clone <repository-url>
```

Move into the project.

```
cd Foreman
```

Start the application.

```
docker compose up --build
```

Open:

```
http://localhost:3000
```

The loopback origin is reachable only from the host. The current household-LAN
origin is:

```
https://192.168.1.184
```

LAN devices must trust the existing Caddy public root certificate. Do not
distribute Caddy's private CA state or expose this deployment to the public
Internet.

---

# Development Workflow

Development follows a versioned release model.

Every feature should:

1. Be discussed.
2. Be designed.
3. Be implemented.
4. Be tested.
5. Update documentation.
6. Be committed.
7. Receive a Git tag.

See `CONTRIBUTING.md`.

---

# Documentation

Project documentation is located in the `docs/` directory.

Important documents include:

- Constitution
- Founder's Letter
- Engineering Principles
- Architecture
- Project Vision
- Design Principles
- Future Ideas

The Constitution is the highest authority. The Founder's Letter defines
project intent, Engineering Principles define development behavior, Design
Principles define the user experience, and Architecture defines the Version
1.0 target architecture.

---

# Contributing

Before contributing:

1. Read `docs/CONSTITUTION.md`
2. Read `docs/FOUNDERS_LETTER.md`
3. Read `docs/ENGINEERING_PRINCIPLES.md`
4. Read `docs/DESIGN_PRINCIPLES.md`
5. Read `ARCHITECTURE.md`
6. Read `docs/AGENTS.md`
7. Read `README.md`
8. Read `ROADMAP.md`
9. Read `CHANGELOG.md`
10. Read `docs/TASKS.md`
11. Read `CONTRIBUTING.md`

All contributors—including AI coding assistants—are expected to follow the
project's architectural and documentation standards.

---

# License

License information will be added before the first public release.

Until then, all rights are reserved by HardHead Works.

---

# Acknowledgements

The Foreman began as an internal project for HardHead Works with the goal of
building software that supports real craftsmanship.

Every feature is intended to solve practical workshop problems first and grow through real-world use.

---

> **The Foreman serves the craftsman.**
