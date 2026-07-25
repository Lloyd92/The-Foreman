# The Foreman Architecture

Version: 1.0

---

# Purpose

This document describes the architecture of The Foreman.

Its purpose is to help contributors understand how the application is organized before modifying the codebase.

The Foreman is intentionally designed around a modular architecture so that new features can be added without disrupting existing functionality.

---

# Architectural Goals

The architecture is designed to be:

- Modular
- Maintainable
- Predictable
- Testable
- Scalable
- Local-first

Every module should have a clearly defined responsibility.

---

# High-Level Architecture

```
                   Browser
                       │
             HTML / CSS / JavaScript
                       │
                  Application Router
                       │
        ┌──────────────┼──────────────┐
        │              │              │
   Dashboard        Tasks        Inventory
        │              │              │
        └──────────────┼──────────────┘
                       │
                  Shared Utilities
                       │
                Local Storage / API
                       │
             FastAPI Backend (future)
                       │
          PostgreSQL Database (planned)
```

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

# Folder Structure

```
Foreman/

backend/
frontend/
docs/

README.md
ROADMAP.md
ARCHITECTURE.md
CHANGELOG.md
CONTRIBUTING.md
AGENTS.md
TASKS.md
docker-compose.yml
```

---

## Frontend

```
frontend/

index.html

styles.css

app.js

pages/

utils/

assets/
```

---

### pages/

Each file is responsible for one application page.

Example:

```
dashboard.js

tasks.js

inventory.js
```

Responsibilities:

- Render page content
- Handle user interaction
- Coordinate with storage
- Coordinate with APIs

Pages should not contain unrelated business logic.

---

### utils/

Utility modules contain reusable logic.

Examples:

```
inventoryStorage.js

taskStorage.js

dateUtils.js

formatters.js
```

Utility modules should remain independent of user interface code whenever practical.

---

# Application Startup

Application startup follows this sequence:

```
Browser

↓

index.html

↓

app.js

↓

Router

↓

Initialize Modules

↓

Dashboard

Tasks

Inventory

↓

Application Ready
```

Each module registers its own event listeners during initialization.

---

# Routing

The application uses client-side routing.

Responsibilities:

- Switch between pages
- Preserve navigation state
- Initialize page modules
- Avoid page reloads

The router should not contain business logic.

---

# Module Responsibilities

## Dashboard

Responsible for:

- Greeting
- System overview
- Inventory alerts
- Future project summaries

---

## Tasks

Responsible for:

- Creating tasks
- Editing tasks
- Completing tasks
- Task persistence

---

## Inventory

Responsible for:

- Inventory management
- Search
- Filtering
- Sorting
- Low-stock detection

Inventory should not manage purchasing, budgeting, or projects directly.

---

## Future Modules

Planned modules include:

Projects

Budget

Mealworms

Customers

Purchasing

Maintenance

Reporting

Each module should remain independent while communicating through shared interfaces.

---

# Data Flow

Current architecture:

```
User

↓

UI Event

↓

Page Module

↓

Storage Module

↓

Browser Local Storage

↓

Render Updated UI
```

Future architecture:

```
User

↓

UI Event

↓

Page Module

↓

API Module

↓

FastAPI

↓

Database

↓

API Response

↓

Render Updated UI
```

The goal is to replace storage modules without rewriting page modules.

---

# Event-Driven Communication

Modules communicate using events whenever practical.

Example:

```
Inventory Updated

↓

Dashboard Refreshes

↓

Inventory Summary Updates
```

This reduces coupling between modules.

Modules should avoid directly modifying each other.

---

# State Management

Current:

Browser Local Storage

Future:

Backend database with API synchronization.

Pages should not maintain duplicate copies of application state.

Whenever possible:

Single source of truth.

---

# User Interface

The interface should remain:

Fast

Responsive

Professional

Minimal

Information dense without becoming cluttered.

Animation should support usability rather than decoration.

---

# Styling

Global styles belong in:

```
styles.css
```

Component-specific styles should remain grouped logically.

Future versions may split styles into modules if complexity increases.

---

# Error Handling

Errors should:

- Fail gracefully
- Preserve user data
- Display meaningful messages
- Avoid crashing the application

Unexpected errors should be logged during development.

---

# Performance

Optimize for:

- Responsiveness
- Readability
- Maintainability

The Foreman is expected to run well on modest hardware.

The reference development machine is the HardHead Linux server.

---

# Security

Current development focuses on local deployment.

Future releases should include:

- Authentication
- Authorization
- Secure API communication
- Encrypted credentials
- Database security

Security should be added without compromising usability.

---

# Testing Philosophy

Every feature should be tested.

Verify:

- Existing functionality
- New functionality
- Browser console
- Docker containers
- API responses

Regression testing is preferred over reactive bug fixing.

---

# Documentation

Architecture changes require updates to:

ARCHITECTURE.md

Feature changes require updates to:

CHANGELOG.md

Future plans belong in:

ROADMAP.md

Ideas belong in:

docs/FUTURE_IDEAS.md

---

# Future Evolution

The current architecture is intentionally simple.

As The Foreman grows, planned additions include:

- PostgreSQL
- Authentication
- Multi-user support
- Mobile applications
- Plugin architecture
- REST API expansion
- AI-assisted workflows

These additions should extend the existing architecture rather than replace it.

---

# Architectural Principles

1. One responsibility per module.

2. Prefer composition over duplication.

3. Readability is more important than cleverness.

4. Preserve backwards compatibility whenever practical.

5. Every module should be independently testable.

6. Features should be loosely coupled.

7. Documentation is part of the architecture.

---

# Final Principle

The architecture exists to support craftsmanship.

Every technical decision should make the software easier to understand, easier to maintain, and more useful inside a real workshop.

> The Foreman serves the craftsman.