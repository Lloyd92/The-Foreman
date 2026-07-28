# Changelog

All notable changes to The Foreman are documented in this file.

This project follows a milestone-based development process.

Each release represents a stable, working version of the application.

---

# [Unreleased]

## Documentation

- Established the Constitution-first documentation authority order.
- Clarified the Dashboard as the application shell and the Morning Briefing as
  its default workspace.
- Separated current implementation from the Version 1.0 target architecture.
- Reconciled current release status, planned work, repository paths, and
  persistence terminology.
- Confirmed FastAPI, SQLAlchemy, Pydantic, and SQLite as the Version 1.0 target
  stack.

---

# v0.7.1

## Added

- Backend SQLite persistence for Projects and material requirements
- Versioned, idempotent SQLite schema upgrades with internal schema version 2
- Durable, server-authoritative browser Project migration with stable source
  IDs, payload fingerprints, and atomic provenance
- Inventory → Project → Task startup migration ordering
- Backend Project and material CRUD integration for the Projects workspace
- Shared frontend Project API and runtime validation utilities
- Expanded frontend migration, API, runtime, and backend Project test coverage

## Improved

- Made backend Project responses authoritative for the Projects workspace and
  Dashboard Project summaries
- Preserved missing Inventory references so requirements remain visible,
  editable, and removable
- Kept Task records renderable by clearing their Project references when a
  related Project is deleted
- Completed manual browser validation of Project CRUD, material changes,
  refresh persistence, Dashboard summaries, and Task compatibility
- Updated application version metadata to 0.7.1

## Compatibility

- Retained legacy browser Project source data for migration evidence,
  compatibility, and manual recovery
- Retained tombstone provenance after deletion of a migrated Project so
  idempotent retries do not recreate it
- Report migration conflicts when a previously migrated browser source record
  is edited locally
- Retained archived legacy Projects for manual recovery instead of importing
  or deleting them silently

---

# v0.6.4

## Added

- Browser-local project material requirements linked to Inventory item IDs
- Focused Materials dialog for adding and removing project requirements
- Deterministic material availability, shortage, and readiness calculations
- Project-card readiness indicators and Dashboard project-readiness metrics
- Visible missing-reference handling for deleted Inventory items

## Improved

- Kept material readiness current after Project and Inventory changes
- Preserved legacy Projects without material requirements
- Updated application version metadata to 0.6.4

---

# v0.6.3

## Added

- Reusable Add/Edit project dialog with complete field prepopulation
- Project Edit and confirmed permanent Delete controls
- Edit timestamps while preserving project identity and creation timestamps

## Improved

- Kept summaries, search, filtering, sorting, and browser-local persistence
  current after project changes
- Updated application version metadata to 0.6.3

---

# v0.6.2

## Added

- Browser-local project storage and refresh-safe persistence
- Project creation dialog fields for type, status, priority, progress, dates,
  estimated cost, description, and notes
- Project cards with key planning details and progress bars

## Improved

- Activated both Projects workspace creation actions
- Made project search, status filtering, sorting, and summary counts functional
- Updated application version metadata to 0.6.2

## Removed

- Deferred user-facing browser-local project archiving beyond v0.6.2

---

# v0.6.1

## Added

- Projects workspace shell
- Project summary cards
- Project search controls
- Project status filtering controls
- Project sorting controls
- Add-project placeholder behavior
- Projects navigation integration

---

# v0.5.4

## Added

- Inventory sorting
- Dashboard inventory alerts
- Dashboard integration with inventory
- Automatic inventory update events

## Improved

- Inventory workflow
- Dashboard awareness of inventory status

---

# v0.5.3

## Added

- Inventory editing
- Inventory deletion
- Live inventory search
- Category filtering
- Stock status filtering

## Improved

- Inventory management workflow
- Inventory table interaction

## Fixed

- Inventory dialog improvements
- Inventory persistence refinements

---

# v0.5.2

## Added

- Inventory creation dialog
- Browser-local inventory storage
- Category tracking
- Low-stock detection
- Inventory summary cards

---

# v0.5.1

## Added

- Inventory workspace
- Professional inventory layout
- Search interface
- Filter controls
- Inventory summary cards
- Empty-state experience

---

# v0.4.0

## Added

- Modular application architecture
- Router module
- Dashboard module
- Task module
- API module
- Storage module

## Improved

- Project organization
- Code maintainability
- Application startup process

---

# v0.3.0

## Added

- Browser-local task storage
- Task priorities
- Task completion

## Improved

- Dashboard usability

---

# v0.2.0

## Added

- Dashboard interface
- Greeting system
- System status
- Initial application layout

---

# v0.1.0

## Added

- Initial project structure
- Docker development environment
- Flask backend
- Nginx frontend
- Docker Compose configuration
- Local development workflow

---

# Project History

The Foreman began as an internal software project for HardHead Works.

Its purpose is to simplify workshop management through modular software that grows alongside the business.

Each release builds upon the previous one while preserving the project's long-term philosophy:

> The Foreman serves the craftsman.
