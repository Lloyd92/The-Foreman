# The Foreman

> *The Foreman serves the craftsman.*

The Foreman is a modular workshop operating system being developed by **HardHead Works**.

Its purpose is simple:

Help builders, makers, craftsmen, and small businesses organize their work without getting in the way of it.

The Foreman is designed to replace scattered notebooks, spreadsheets, sticky notes, and disconnected applications with one organized command center for the workshop.

---

# Project Status

**Current Version**

v0.6.2 (Development)

Current focus:

- Projects workspace
- Documentation reconciliation
- Workshop operating system foundation

---

# Mission

The Foreman exists to reduce friction inside the workshop.

Instead of spending time searching for materials, remembering measurements, tracking projects, or managing inventory manually, users should be able to focus on building.

Every feature is designed around one guiding question:

> **Does this help someone build something?**

---

# Primary Experience

The Dashboard is the application shell.

The Morning Briefing is the Dashboard's default workspace and the primary
experience of The Foreman. It is intended to help the owner understand:

1. What can I realistically accomplish today?
2. What matters most today?
3. What do I need to know before I begin?

Capacity always precedes scheduling. Future recommendations must fit the
owner's available time, energy, money, materials, and other real constraints.

The current Dashboard is an early operational workspace. The complete Morning
Briefing and Capacity Engine remain Version 1.0 target capabilities.

---

# Core Principles

The Foreman is built around several fundamental ideas.

- Local-first operation
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

The application shell and home of the Morning Briefing.

Current capabilities:

- System status
- Greeting and date
- Task management workspace
- Inventory alerts
- Module status summaries

The full capacity-aware Morning Briefing is not yet implemented.

---

## Tasks

Manage day-to-day work.

Features include:

- SQLite persistence through the backend
- Migration and fallback support for browser-local tasks
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
- Migration and fallback support for browser-local inventory
- Search
- Filtering
- Sorting
- Low-stock detection

Planned capabilities:

- Barcode support
- Purchase tracking
- Supplier management
- Material forecasting

---

# Projects

The v0.6.2 Projects workspace supports browser-local project creation and
persistence, project cards, progress tracking, summary counts, search, status
filtering, and sorting.

Material requirements, project templates, and deeper module integrations
remain planned work.

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

Version Control

- Git

Development Environment

- Linux (Xubuntu)

Tasks and Inventory use backend SQLite persistence with migration and fallback
support for browser-local records. The v0.6.2 Projects workspace remains
browser-local and does not yet use the existing backend Projects API.

The backend currently provides validated APIs for system status, Inventory,
Projects, Tasks, browser-data migration, and operational facts. Its service,
repository, Pydantic schema, SQLAlchemy model, SQLite persistence, and
automated-test foundations are implemented. Capacity, Priority, the complete
Morning Briefing, and backup and restore remain Version 1.0 target work.

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
├── docker/             # Reserved infrastructure directory
├── docs/
│   └── AGENTS.md       # Contributor and AI-agent instructions
├── frontend/           # HTML, CSS, and JavaScript application
├── compose.yaml
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md
├── README.md
└── ROADMAP.md
```

The implemented backend foundation includes API, service, repository, model,
schema, SQLite, and test layers. The Version 1.0 target may add operational
scripts and the remaining planned capabilities documented in
`ARCHITECTURE.md`.

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

All contributors—including AI coding assistants—are expected to follow the project's architectural and documentation standards.

---

# License

License information will be added before the first public release.

Until then, all rights are reserved by HardHead Works.

---

# Acknowledgements

The Foreman began as an internal project for HardHead Works with the goal of building software that supports real craftsmanship.

Every feature is intended to solve practical workshop problems first and grow through real-world use.

---

> **The Foreman serves the craftsman.**
