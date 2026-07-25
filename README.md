# The Foreman

> *The Foreman serves the craftsman.*

The Foreman is a modular workshop operating system being developed by **HardHead Works**.

Its purpose is simple:

Help builders, makers, craftsmen, and small businesses organize their work without getting in the way of it.

The Foreman is designed to replace scattered notebooks, spreadsheets, sticky notes, and disconnected applications with one organized command center for the workshop.

---

# Project Status

**Current Version**

v0.5.4 (Development)

Current focus:

- Inventory Management
- Dashboard Integration
- Workshop Operating System Foundation

---

# Mission

The Foreman exists to reduce friction inside the workshop.

Instead of spending time searching for materials, remembering measurements, tracking projects, or managing inventory manually, users should be able to focus on building.

Every feature is designed around one guiding question:

> **Does this help someone build something?**

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

The central command center for the workshop.

Displays:

- System status
- Daily overview
- Inventory alerts
- Future project summaries

---

## Tasks

Manage day-to-day work.

Features include:

- Persistent task storage
- Completion tracking
- Priority levels

---

## Inventory

Track workshop resources.

Current capabilities:

- Add inventory
- Edit inventory
- Delete inventory
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

# Planned Modules

The Foreman is intentionally modular.

Future modules include:

- Projects
- Budget
- Mealworm Production
- Customer Management
- Purchasing
- Maintenance
- Reporting
- Artificial Intelligence
- Automation

See `ROADMAP.md` for additional details.

---

# Technology Stack

Frontend

- HTML5
- CSS3
- JavaScript (ES Modules)

Backend

- Python
- FastAPI

Infrastructure

- Docker
- Docker Compose
- Nginx

Version Control

- Git

Development Environment

- Linux (Xubuntu)

---

# Project Structure

```
Foreman/

├── backend/
├── frontend/
├── docs/

├── README.md
├── ROADMAP.md
├── ARCHITECTURE.md
├── CHANGELOG.md
├── CONTRIBUTING.md

└── docker-compose.yml
```

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

- Founder's Letter
- Project Vision
- Design Principles
- Future Ideas

These documents explain the philosophy behind the project and should be read before making significant architectural changes.

---

# Contributing

Before contributing:

1. Read `README.md`
2. Read `ROADMAP.md`
3. Read `ARCHITECTURE.md`
4. Read `CONTRIBUTING.md`

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