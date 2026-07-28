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

Persistence:

- The backend persists Inventory, Projects, Tasks, and browser-migration
  records in SQLite through SQLAlchemy.
- The Inventory and Tasks frontends retain browser-local compatibility and
  include migration paths to backend persistence.
- The v0.6.3 Projects frontend uses browser `localStorage` and does not
  currently use the backend Projects API.
- The browser-local Projects fields and backend Project schema do not yet
  match; browser-local Projects are therefore absent from backend operational
  facts.

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

- Provides the v0.6.3 Projects workspace, browser-local project creation,
  editing, confirmed deletion, persistence, project cards, progress tracking,
  summary cards, search, filtering, sorting controls, and empty state.
- Material requirements, project templates, and deeper module integrations
  are not yet implemented.

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
│   └── .gitkeep
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
│   ├── app.js
│   ├── default.conf
│   ├── index.html
│   └── styles.css
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
├── ROADMAP.md
└── compose.yaml
```

The `database/` and `docker/` directories are currently placeholders. The
SQLite database is stored in the Docker-managed `/data` volume. The repository
does not yet contain an operational `scripts/` directory.

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
creates missing tables from SQLAlchemy metadata. Versioned database migrations
are not yet implemented.

The `/api/operational-facts` endpoint currently aggregates backend Inventory,
Projects, and Tasks through their services and repositories. It is an early
module-fact boundary, not the Morning Briefing, Capacity Engine, or Priority
Engine. Because v0.6.3 Projects remain browser-local, those Projects do not
appear in this backend aggregation.

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
