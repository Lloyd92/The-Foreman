# Architecture

## The Foreman

### Version 1.0 Target Architecture

This document defines the Version 1.0 target architecture for The Foreman.
It also records the current implementation so contributors can distinguish
what exists today from what the project is building toward.

The target architecture may evolve alongside the project, but it must remain
consistent with the Constitution, Founder's Letter, Engineering Principles,
and Design Principles. The Constitution is the highest authority.

---

# 1. Purpose

The Foreman is a local-first business operating system whose primary
responsibility is to transform scattered operational information into clear,
actionable decisions.

The architecture is designed around four core goals:

- Reliability
- Modularity
- Explainability
- Simplicity

Every technical decision should ultimately improve the Morning Briefing.

The Dashboard is the application shell.

The Morning Briefing is the Dashboard's default workspace and the primary
experience of The Foreman.

---

# 2. Current Implementation

The current implementation is an early working foundation. It does not yet
implement every layer or capability described in the Version 1.0 target.

## 2.1 Current Technology

Backend:

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Uvicorn
- Validated APIs for system status, Inventory, Projects, Tasks, browser-data
  migration, and operational facts

Frontend:

- Static HTML
- CSS
- JavaScript using ES modules
- Nginx

Deployment:

- Docker
- Docker Compose
- `compose.yaml`
- Caddy private-LAN TLS gateway
- Nginx static-file and `/api/` proxy authority behind Caddy

Persistence:

- The backend persists Inventory, Projects, Tasks, and browser-migration
  records in SQLite through SQLAlchemy.
- The Inventory and Tasks frontends retain browser-local compatibility and
  include migration paths to backend persistence.
- SQLite is the authoritative Project store. The Projects workspace and
  Dashboard consume backend Project data through the shared Project API
  utility and runtime validation helpers.
- Browser-local Projects are retained as migration evidence and for
  compatibility and recovery. They are read by migration code, not used as
  the Projects workspace's runtime authority.
- Project material requirements persist in SQLite and link to Inventory by
  item ID. The frontend currently derives readiness and shortages from backend
  Project requirements and current Inventory records without storing derived
  values or mutating Inventory quantities.

## 2.2 Current Workspaces

Dashboard:

- Provides the application shell.
- Displays a greeting, date, system status, Tasks workspace, inventory alerts,
  and module status summaries.
- Does not yet implement the complete capacity-aware Morning Briefing.

Tasks:

- Supports task creation, priority selection, completion, deletion, and
  backend persistence with migration of browser-local records.
- Currently appears within the Dashboard; the dedicated Tasks page remains a
  placeholder.

Inventory:

- Supports creation, editing, deletion, search, filtering, sorting, low-stock
  detection, dashboard alerts, backend persistence, and migration of
  browser-local records.

Projects:

- Provides the v0.7.1 Projects workspace with backend-authoritative creation,
  editing, confirmed deletion, persistence, project cards, progress tracking,
  persistent material requirements, deterministic frontend
  material-readiness calculations, summary cards, search, filtering, sorting
  controls, and empty state.
- Missing Inventory references remain visible, editable, and removable.
- Project deletion clears related Task Project references through database
  foreign-key behavior.
- Estimated completion, Project templates, and deeper module integrations are
  not yet implemented.

Budget and Mealworms:

- Exist as placeholder workspaces.
- Their operational modules are not yet implemented.

## 2.3 Layers and Capabilities Not Yet Implemented

The current implementation does not yet include:

- Capacity Engine
- Priority Engine
- Morning Briefing assembly logic
- Backup
- Restore and restore verification
- Testing Mode

These are incomplete Version 1.0 target capabilities, not evidence that the
target architecture has changed.

The implemented backend foundation currently includes:

- FastAPI routes as the validated HTTP boundary
- Pydantic request and response schemas
- Services for business rules and transaction coordination
- Repositories for SQLAlchemy database access
- SQLAlchemy persistence models
- SQLite application persistence
- Versioned, idempotent SQLite schema upgrades
- Automated backend API tests
- Operational-facts aggregation across backend Inventory, Projects, and Tasks

## 2.4 Current Repository Structure

```text
Foreman/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── models/
│   │   ├── repositories/
│   │   ├── schemas/
│   │   ├── services/
│   │   └── main.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── database/
│   └── .gitkeep
├── docker/
│   └── Caddyfile
├── docs/
│   ├── AGENTS.md
│   ├── CONSTITUTION.md
│   ├── DESIGN_PRINCIPLES.md
│   ├── ENGINEERING_PRINCIPLES.md
│   ├── FOUNDERS_LETTER.md
│   ├── FUTURE_IDEAS.md
│   ├── PROJECT_VISION.md
│   └── TASKS.md
├── frontend/
│   ├── pages/
│   ├── utils/
│   ├── Dockerfile
│   ├── assets/
│   ├── app.js
│   ├── default.conf
│   ├── index.html
│   ├── manifest.webmanifest
│   ├── service-worker.js
│   └── styles.css
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── compose.yaml
```

The `database/` directory remains a repository placeholder while SQLite is
stored in the Docker-managed `/data` volume. The `docker/` directory now
contains the operational private-LAN Caddy configuration. The repository does
not yet contain an operational `scripts/` directory.

## 2.5 Current Backend Flow

Current database-backed requests follow this implemented flow:

```text
FastAPI route
      │
      ▼
Pydantic request validation
      │
      ▼
Service business rules and transaction coordination
      │
      ▼
Repository SQLAlchemy queries
      │
      ▼
SQLAlchemy models
      │
      ▼
SQLite in the Docker-managed /data volume
      │
      ▼
Pydantic response serialization
```

FastAPI dependencies provide one SQLAlchemy session per request. Services
commit successful mutations and roll back failed mutations; repositories
remain responsible for database queries and record access. Application startup
creates missing tables from SQLAlchemy metadata and applies versioned,
idempotent SQLite schema upgrades. The current internal SQLite schema version
is 2. Startup refuses a database whose schema version is newer than the
application supports and verifies the required Project schema after upgrades.

The `/api/operational-facts` endpoint currently aggregates backend Inventory,
Projects, and Tasks through their services and repositories. It is an early
module-fact boundary, not the Morning Briefing, Capacity Engine, or Priority
Engine. Backend Projects are visible in active-Project and Project-status
facts. Project material readiness remains a frontend calculation and is not
yet part of backend operational facts.

## 2.6 Current Project Migration and Runtime Flow

Application startup coordinates retained browser-data migration in this order:

```text
Inventory migration
        │
        ▼
Project migration
        │
        ▼
Task migration
```

Inventory migrates first so Project material requirements can resolve their
authoritative Inventory IDs. Project migration then produces mappings from
stable browser source IDs to backend Project UUIDs. Task migration runs last
so legacy Task Project references can use those mappings. Task migration still
runs when individual Project migrations fail.

The durable Project migration endpoint records provenance in SQLite using the
stable source record ID and a canonical payload fingerprint. Project creation,
material-requirement creation, and provenance insertion occur in one database
transaction. The backend is the idempotency authority: matching retries return
the existing Project, while changed payloads produce a conflict. If a migrated
Project is deleted, its provenance row remains with a null Project mapping as
a tombstone so the source record is not silently recreated.

Browser migration provenance is advisory. The original browser Project
collection remains unchanged for compatibility, migration evidence, and
manual recovery. Archived legacy Projects remain in that retained source and
are not imported automatically.

After the migration prerequisite completes, the Projects page loads
exclusively through `GET /api/projects`. Normal Project and material mutations
use the Project API endpoints, then render the validated backend response as
the visible source of truth. A shared Project runtime validates lists and
merges or removes successful mutation results. Dashboard Project summaries
also load backend Projects and respond to Project update events.

Backend-authoritative readiness and a unified operational-facts model remain
deferred core-convergence work. The current frontend combines backend Projects
with Inventory data to calculate Project readiness deterministically.

## 2.7 PWA, Availability, and Household Deployment

The v0.7.2 PWA Foundation uses this implemented delivery path:

```text
LAN device
    │ trusted HTTPS
    ▼
Caddy private-LAN TLS gateway
    │
    ▼
frontend Nginx
    ├── static SPA/PWA shell
    └── /api/ proxy
             │
             ▼
          backend
             │
             ▼
           SQLite
```

The manifest and installation assets define the PWA identity and installation
boundary. Standalone display, Apple installation metadata, and dynamic
safe-area insets support the installed iPhone experience.

The service worker atomically precaches exactly 29 static-shell resources.
Only exact allowlisted shell resources and navigation fallback are handled by
that cache. APIs, migrations, mutations, non-GET requests, the worker itself,
unknown static resources, and cross-origin requests remain network-owned.
There is no business-data cache, write queue, replay path, Background Sync, or
IndexedDB mutation store.

Updates install into a waiting state. Activation requires an explicit user
action and is blocked while a form is dirty or a dialog is open. The worker
does not automatically skip waiting or claim existing clients.

The connection-state controller uses `/api/health` as the operational
authority. The application does not start business operations until HardHead
reports both a healthy application and an online database. A cached shell may
remain visible during backend loss, but that does not make operational data
available. Projects, Tasks, and Inventory browser records remain
migration/evidence/compatibility inputs only and never become normal runtime
fallback authority.

The frontend is bound to tower loopback at `127.0.0.1:3000`. Caddy binds ports
80 and 443 only to the configured private-LAN IP, currently
`192.168.1.184`. The backend has no host binding and remains private to the
Compose network. Nginx remains the static-file and `/api/` proxy authority;
Caddy adds the trusted HTTPS edge without replacing it.

This is a household-first private deployment, not public Internet exposure.
HTTPS protects transport and server identity but does not authenticate users.
Only Caddy's public root certificate is distributed to trusted devices. Its
private CA keys and certificate state remain protected in persistent
`caddy-data` and `caddy-config` volumes.

The current secure origin is the private IP address.
`hardhead.home.arpa` remains a future LAN-DNS goal and is not part of v0.7.2.

---

# 3. Version 1.0 Target

## 3.1 Core System Flow

```text
Projects
Tasks
Inventory
Finance
Notes
Settings
      │
      ▼
Operational facts from modules
      │
      ▼
Capacity Engine
      │
      ▼
Priority Engine
      │
      ▼
Morning Briefing
      │
      ▼
Dashboard application shell
```

The responsibilities in this flow are explicit:

1. Modules provide operational facts.
2. Capacity determines which work is realistically eligible.
3. Priority ranks eligible work.
4. The Morning Briefing presents the result in the Dashboard's default
   workspace.

Capacity evaluation precedes scheduling and recommendation. Scheduling may
organize eligible work, but it must never override real limits.

## 3.2 Design Goals

The Version 1.0 architecture must be:

- Local-first
- Modular
- Explainable
- Testable
- Recoverable
- Portable
- AI-independent

Artificial Intelligence may enhance the application, but it is never required
for core operation.

## 3.3 Official Version 1.0 Technology Stack

Backend:

- Python
- FastAPI
- SQLAlchemy
- Pydantic

Database:

- SQLite

Frontend:

- HTML
- CSS
- JavaScript

Deployment:

- Docker
- Docker Compose

FastAPI, SQLAlchemy, Pydantic, and SQLite are the official Version 1.0 target
stack and now form the implemented backend foundation. The remaining Version
1.0 services and operational capabilities are still target work. Changing the
target stack requires an explicit architectural decision and founder approval.

## 3.4 Planned Version 1.0 Repository Structure

The exact internal package names may be refined when each layer is
implemented, but the following structure records the required separation of
responsibilities:

```text
Foreman/
├── backend/
│   └── app/
│       ├── api/             # Validated API endpoints
│       ├── services/        # Business-logic layer
│       ├── repositories/    # Database-access layer
│       ├── models/          # SQLAlchemy persistence models
│       ├── schemas/         # Pydantic schemas
│       └── main.py
├── database/                # Planned SQLite data and backup support
├── docker/                  # Planned shared deployment support
├── docs/
├── frontend/
│   ├── pages/
│   └── utils/
├── scripts/                 # Planned operational and backup scripts
├── tests/                   # Planned automated tests
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── compose.yaml
```

This remains the target structure. The API, service, repository, model,
schema, SQLite, and backend-test foundations now exist; shared operational
scripts and additional Version 1.0 capabilities remain planned.

---

# 4. Version 1.0 Architectural Layers

## 4.1 Frontend

The frontend is responsible for presentation and user interaction.

The Dashboard provides the application shell. Its default workspace is the
Morning Briefing. Other workspaces must remain modular and must not displace
the Morning Briefing as the primary experience.

## 4.2 API

The FastAPI layer receives requests and returns validated responses.

Pydantic schemas define and validate request and response boundaries.

## 4.3 Services

Services contain business logic, including:

- Morning Briefing assembly
- Capacity evaluation
- Priority evaluation
- Inventory evaluation
- Financial readiness

Services must not depend on frontend presentation details.

## 4.4 Repositories

Repositories are responsible for database access.

Business logic must not depend directly on SQLite or SQLAlchemy implementation
details.

## 4.5 Database

SQLite provides persistent storage for Version 1.0.

Database storage replaces neither the service layer nor the repository
boundary.

---

# 5. Morning Briefing

The Morning Briefing is the Dashboard's default workspace and the primary
output of the system.

It answers three questions:

1. What can I realistically accomplish today?
2. What matters most today?
3. What do I need to know before I begin?

Every major module contributes operational facts toward these answers.

The Morning Briefing assembles capacity-aware, prioritized information. It
does not replace the independent responsibilities of contributing modules.

---

# 6. Capacity Engine

The Capacity Engine evaluates:

- Available time
- Available energy
- Work schedule
- Commute
- Budget
- Inventory readiness
- Required tools
- Available materials
- Current workload
- Work type

Capacity evaluation precedes both scheduling and recommendation.

Only work that fits the owner's real constraints is eligible for
prioritization. Recommendations must always fit today's reality.

---

# 7. Priority Engine

The Priority Engine ranks work only after the Capacity Engine has determined
that the work is realistically eligible.

Priority must not make impossible work appear actionable. Its output supports
the Morning Briefing by identifying the next meaningful work among realistic
options.

---

# 8. Explainability

Every recommendation should include:

- Recommendation
- Reason
- Confidence
- Source information when practical

The Foreman must never expect blind trust.

Explainability applies whether a recommendation is generated by deterministic
business logic or enhanced by AI.

---

# 9. Module Philosophy

Modules remain independent.

Examples include:

- Projects
- Tasks
- Inventory
- Finance
- Notes
- Settings

Modules own their operational facts and provide those facts through
well-defined interfaces.

Capacity evaluates realistic eligibility, Priority ranks eligible work, and
the Morning Briefing assembles the result.

---

# 10. AI Integration

Version 1.0 requires no AI.

The complete core flow—from module facts through Capacity and Priority to the
Morning Briefing—must remain useful without AI.

Future AI providers must connect through a provider interface rather than
being tightly coupled to the application.

AI may assist, explain, summarize, or reason. It must not replace human
judgment.

---

# 11. Backup and Restore

Backup and restore are Version 1.0 requirements.

Version 1.0 must support:

- Manual backup
- Scheduled backup
- Restore
- Restore verification

Backup and restore must preserve user ownership of local data and support
recoverability.

---

# 12. Testing Mode

Testing Mode creates a recoverable snapshot before experimentation.

The owner may restore production data when Testing Mode ends.

Testing Mode must not weaken backup, restore, or data-safety requirements.

---

# 13. Portability

The Foreman must remain portable and local-first.

Core workshop operation must not depend on an Internet connection or a cloud
service. Deployment and data should remain transferable between supported
local environments.

---

# 14. Green Build

Every development session ends with a Green Build.

A Green Build means:

- The application launches.
- Current functionality works.
- Documentation is current.
- No known critical issues remain.

Target architecture that is not yet implemented must be documented as target
state, not reported as completed functionality.

---

# 15. Closing

The architecture exists to support one outcome:

Help the user understand what is possible, what matters most, and what should
happen next.

Bring clarity to complexity.

Give confidence through clarity.

Keep the work moving.
