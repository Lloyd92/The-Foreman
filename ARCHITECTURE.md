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

The Foreman is a local-first operational decision-support and continuity
system. It transforms scattered operational information into clear current
state, realistic options, and explainable next actions.

It also serves as an external working memory. The architecture must preserve
projects, decisions, dependencies, progress, and operational context so work
can resume after interruption without reconstructing that context from memory.

The architecture is designed around five core goals:

- Reliability
- Modularity
- Explainability
- Simplicity
- Continuity

The target application shell uses the permanent navigation: Today, Calendar,
Work, Resources, Money, and Library. Settings and Account remain separate.

Today is the default daily workspace. It first presents authoritative factual
state. After Capacity and Priority are implemented, the Morning Briefing is
presented through Today as the primary decision-support experience.

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
- SQLite is the authoritative Project, Task, and Inventory store.
- Browser-local Projects are retained as migration evidence and for
  compatibility and recovery. They are read by migration code, not used as
  the Projects workspace's runtime authority.
- Project material requirements persist in SQLite and link to Inventory by
  item ID.
- The universal foundation schema persists Spaces, People, Organizations,
  Organization-Space relationships, Members, and mutable local module state.
- A deterministic fixed-ID default Space exists. Version 4 migration assigns
  all existing Inventory, Project, Task, and browser-migration provenance
  records to it, and current creation paths explicitly use that same Space.
- Active-Space APIs, authoritative request context, and frontend Space
  selection are not yet implemented.
- Unified Operational Facts derive current lifecycle, material-readiness,
  Task-work, and Inventory-stock conclusions from one authoritative database
  snapshot. Dashboard, Projects, and Inventory consume these facts rather than
  independently interpreting the same records.

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
  and out-of-stock display, dashboard alerts, backend persistence, and
  migration of browser-local records.
- Uses normalized backend `inventory.stock-level` facts as the classification
  authority.

Projects:

- Provides the Projects workspace with backend-authoritative creation,
  editing, confirmed deletion, persistence, project cards, progress tracking,
  persistent material requirements, backend-authoritative readiness,
  summary cards, search, filtering, sorting controls, and empty state.
- Project cards and material dialogs consume normalized
  `project.material-readiness` facts and backend-provided evidence.
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
- Typed universal-foundation and static module-definition contracts
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
├── scripts/
│   ├── bootstrap_browser_e2e.sh
│   ├── run_browser_e2e.sh
│   └── validate_restore_roundtrip.sh
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── compose.yaml
```

The `database/` directory remains a repository placeholder while SQLite is
stored in the Docker-managed `/data` volume. The `docker/` directory now
contains the operational private-LAN Caddy configuration. The `scripts/`
directory supports browser-E2E execution, disposable acceptance, and isolated
restore round-trip validation.

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
is 4. Startup refuses a database whose schema version is newer than the
application supports before table creation can mutate it, then verifies the
required Project, universal-foundation, and default-Space ownership schemas
before advancing the schema version.

The versioned `GET /api/operational-facts` endpoint derives normalized facts
from backend Inventory, Projects, materials, and Tasks. One explicit
transaction supplies the authoritative snapshot for each request. Facts are
computed on demand; there is no persisted fact table and the SQLite schema
version is 4. The operational-fact schema remains version 1. Internal
operational records now carry required `space_id` ownership, but current API
and operational-fact responses do not expose it.

The operational-fact schema version is numeric 1. Its current vocabulary is
`project.lifecycle`, `project.material-readiness`, `task.work-state`, and
`inventory.stock-level`. Every normalized fact has a stable ID, type, subject,
state, reason codes, evidence, and source-record references. Canonical ordering
makes identical source state produce identical serialized fact output.

The response retains six legacy top-level compatibility fields alongside
`schemaVersion`, normalized `facts`, and `summary`, producing the approved
nine-field public contract. Database query failures return a stable,
non-sensitive HTTP 503 response.

This is the implemented module-fact boundary. It is not the Capacity Engine,
Priority Engine, next-action selection, or Morning Briefing narration.

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
merges or removes successful mutation results.

Dashboard, Projects, and Inventory request normalized operational facts
through the shared frontend operations API. Dashboard Project counts come from
the normalized summary. Project cards and material dialogs use
`project.material-readiness` facts and evidence. Inventory status uses
`inventory.stock-level` facts. Missing or malformed facts produce an
unavailable presentation rather than a browser-derived valid state.

## 2.7 PWA, Availability, and Household Deployment

The current PWA delivery path, established in v0.7.2 and hardened through
v0.7.5, is:

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

The service worker atomically precaches exactly 32 static-shell resources.
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
`hardhead.home.arpa` remains a future LAN-DNS goal and is not currently
supported.

---

# 3. Version 1.0 Target

## 3.1 Core System Flow

The target application shell provides the permanent navigation:

- Today
- Calendar
- Work
- Resources
- Money
- Library

Settings and Account remain separate below the primary navigation.

Normal operational workflows use one clearly selected active Space. Backend
services and APIs enforce Space context authoritatively; frontend filtering
alone is never sufficient for Space isolation.

The target decision-support flow is:

```text
Modules provide authoritative facts
        |
        v
Calendar records commitments and availability
        |
        v
Capacity determines realistic eligibility
        |
        v
Priority ranks eligible Work
        |
        v
Morning Briefing presents explainable recommendations
```

The active Space establishes operational context around this chain. Modules
own and validate their records within that context, and Today later presents
the resulting daily experience through the application shell. Neither changes
or interrupts the locked five-stage dependency flow.

The responsibilities in this flow are explicit:

1. Spaces define operational context.
2. Modules own and validate their authoritative records.
3. Modules expose authoritative facts without replacing source ownership.
4. Calendar records commitments, events, routines, recurrence, and
   availability.
5. Capacity determines what Work is eligible, blocked, or realistically fits.
6. Priority ranks only Work that Capacity has determined is eligible.
7. The Morning Briefing presents commitments, alerts, explanations, and
   recommended next actions.
8. Today presents authoritative daily information and later hosts the complete
   Morning Briefing experience.

Calendar recordkeeping and capacity-aware scheduling are different concerns.

Calendar may record fixed commitments, events, routines, recurrence, and
availability before the Capacity Engine exists. This does not claim that
optional Work is achievable.

Capacity must be evaluated before The Foreman:

- Places optional Work into available time
- Declares optional Work feasible
- Ranks eligible Work
- Recommends Work
- Presents capacity-aware scheduling decisions

This preserves the constitutional rule that Capacity takes precedence over
scheduling and recommendation.

Unified Operational Facts are the implemented first decision-support boundary.
Spaces, universal navigation, Calendar, Capacity, Priority, Today aggregation,
and complete Morning Briefing assembly remain target capabilities assigned to
the approved v0.8 and v0.9 milestones.

## 3.2 Design Goals

The Version 1.0 architecture must be:

- Local-first
- Modular
- Explainable
- Testable
- Recoverable
- Portable
- AI-independent
- Continuity-preserving

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
├── docker/                  # Caddy and shared deployment support
├── docs/
├── frontend/
│   ├── pages/
│   └── utils/
├── scripts/                 # Operational validation and recovery scripts
├── tests/                   # Planned automated tests
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── compose.yaml
```

This remains the target structure. The API, service, repository, model,
schema, SQLite, backend-test, and shared operational-script foundations now
exist. Additional Version 1.0 capabilities remain planned.

---

# 4. Version 1.0 Architectural Layers

## 4.1 Frontend

The frontend is responsible for presentation and user interaction.

The application shell provides the permanent navigation: Today, Calendar,
Work, Resources, Money, and Library. Settings and Account remain separate
below the primary navigation.

Today is the default daily workspace. Through v0.8.6, it presents authoritative
factual current state without making capacity, priority, feasibility, or
recommendation claims.

After the v0.9 decision-support sequence is complete, the Morning Briefing
becomes the capacity-aware primary daily experience presented through Today.
Other workspaces remain modular and retain their own responsibilities.

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

The Morning Briefing is the target capacity-aware primary daily experience
presented through Today after the v0.9 decision-support sequence is complete.

It answers three questions:

1. What can I realistically accomplish today?
2. What matters most today?
3. What do I need to know before I begin?

Every major module contributes authoritative operational facts toward these
answers.

Before the Morning Briefing is implemented, Today may present factual current
state, commitments, alerts, and records. It must not claim feasibility, rank
Work, or recommend next actions without Capacity and Priority evaluation.

The Morning Briefing assembles capacity-aware, prioritized information. It
does not replace the independent responsibilities or ownership of contributing
modules. It should restore enough current context for the owner to continue
after an interruption, not merely narrate disconnected records.

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

Calendar may record fixed commitments, events, routines, recurrence, and
availability before Capacity evaluation.

Capacity evaluation must precede automatic placement of optional Work,
feasibility claims, prioritization, recommendations, and capacity-aware
scheduling decisions.

Only Work that fits the owner's real constraints is eligible for
prioritization. Recommendations must always fit today's reality.

---

# 7. Priority Engine

The Priority Engine ranks Work only after the Capacity Engine has determined
that the Work is realistically eligible.

Priority must not make impossible Work appear actionable. Its output supports
the Morning Briefing by identifying the next meaningful Work among realistic
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

Modules remain independent and own their authoritative records.

Examples include:

- Work owns Tasks, Projects, requirements, dependencies, and progress.
- Inventory owns consumable stock, quantities, thresholds, locations, and
  usage.
- Tools owns durable equipment, condition, and availability.
- Calendar owns fixed commitments, events, routines, recurrence, and
  availability.
- Care Plans owns maintenance and care definitions.
- Money owns financial records.
- Library owns stored records and reference material.

Modules communicate through stable identifiers, relationships, services, APIs,
and approved operational facts. They must not manipulate another module's
private tables, duplicate authority, or create browser-side truth.

Capacity reads approved facts to determine realistic eligibility. Priority
ranks eligible Work. Today presents factual current state, and the Morning
Briefing later assembles capacity-aware recommendations.

The local module registry records module identity, enablement, dependencies,
contribution locations, data-retention behavior, and health. It does not
contain subscriptions, billing, licensing, plans, tiers, or entitlements.

The current Unified Operational Facts boundary gives modules one
deterministic, explainable representation of current state. Frontend pages
must consume that shared authority rather than recreate page-specific facts.

# 10. AI Integration

Version 1.0 requires no AI.

The complete core flow—from module facts through Capacity and Priority to the
Morning Briefing—must remain useful without AI.

Future AI providers must connect through a provider interface rather than
being tightly coupled to the application.

AI may assist, explain, summarize, or reason. It must not replace human
judgment or become the factual authority. AI interpretation must remain
grounded in authoritative records and deterministic operational facts.

---

# 11. Backup and Restore

Backup and restore are Version 1.0 requirements.

v0.7.4 establishes the deterministic recovery foundation:

- Manual verified backup packages containing authoritative SQLite data and a
  canonical integrity manifest
- Deterministic portable JSON export for user-owned business records
- Uploaded-package verification before restore preparation
- Durable, expiring restore-preflight sessions on the live database filesystem
- Exact typed confirmation before destructive activation
- A durable verified safety backup before replacement begins
- Atomic same-filesystem database replacement
- Post-activation schema, checksum, record-count, and operational-fact
  verification
- Automatic rollback to the verified safety backup when activation
  verification fails
- An emergency maintenance latch when both activation and rollback fail
- A Backup & Recovery workspace that exposes downloads, preflight review, and
  controlled activation without revealing private filesystem paths
- An isolated destructive round-trip validator that uses a disposable
  container and temporary SQLite database without mounting live data

Scheduled backup automation remains Version 1.0 work.

Backup and restore preserve user ownership of local data and support
recoverability. Backups preserve the continuity system itself: authoritative
records, migration evidence, and the context required to resume work remain
restorable and verifiable.

# 12. Testing Mode

Testing Mode creates a recoverable snapshot before experimentation.

The owner may restore production data when Testing Mode ends.

Testing Mode must not weaken backup, restore, or data-safety requirements.

---

# 13. Portability

The Foreman must remain portable and local-first.

Core operation must not depend on an Internet connection or a cloud service.
Deployment and data should remain transferable between supported local
environments.

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
