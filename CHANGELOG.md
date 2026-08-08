# Changelog

All notable changes to The Foreman are documented in this file.

This project follows a milestone-based development process.

Each release represents a stable, working version of the application.

---

# [Unreleased]

No unreleased changes are recorded yet.

---

# v0.8.1 — 2026-08-08

## Added

- Added optional same-Space Member responsibility to authoritative Work
  records while preserving existing records with null responsibility.
- Added nullable Task due dates as Work facts without creating Calendar
  commitments or Capacity claims.
- Added factual typed Work dependencies between Tasks and Tasks or Projects
  without scheduling, ranking, or recommendation behavior.
- Added the backend-authoritative normalized `GET /api/work` read model while
  retaining native Task and Project mutation APIs.
- Added the Universal Work frontend with Overview, Tasks, and Projects
  surfaces beneath the permanent Work category.
- Added isolated browser acceptance for Task due dates, Task-to-Project
  relationships, Work dependencies, normalized Work presentation, and
  persistence across reloads.

## Changed

- Advanced the internal SQLite schema from version 4 to version 5 while
  preserving existing Task, Project, Space, migration-provenance, material,
  backup, restore, and export compatibility.
- Preserved native Task and Project lifecycle semantics rather than introducing
  a generalized `work_items` persistence superclass.
- Kept existing Project material requirements as the first concrete Work
  requirement type instead of prematurely generalizing future requirements.
- Updated application release identity to 0.8.1 and finalized the exact
  42-resource PWA shell as `foreman-shell-v0.8.1-c1`.

## Reliability

- Enforced same-Space ownership for Work responsibility and relationships.
- Kept Work dependencies factual and protected them from invalid self,
  duplicate, cross-Space, and cyclic relationships.
- Preserved Task compatibility when related Projects are deleted.
- Preserved module disable/re-enable data retention and corrected Work-owned
  child navigation contributions discovered during browser acceptance.
- Kept Work API and frontend state backend-authoritative with no browser
  persistence fallback.

## Validation

- Completed final full backend acceptance with 306 tests passing.
- Completed final full frontend acceptance with 172 tests passing.
- Completed isolated disposable Firefox acceptance with 42 tests passing.
- Verified disposable acceptance cleanup left zero project containers,
  networks, or images.
- Verified clean disposable startup with empty Inventory, Projects, Tasks, and
  Work dependency collections.
- Preserved operational-fact schema version 1 and portable export format
  version 1.

## Documentation

- Completed the eight-commit v0.8.1 Universal Work milestone.
- Documented Work as a domain and integration boundary rather than a universal
  persistence superclass.
- Preserved Capacity for v0.9.0, Priority for v0.9.1, and Morning Briefing
  recommendations for v0.9.2.
- Set v0.8.2 Tools, Inventory & Care as the next approved milestone.

---

# v0.8.0 — 2026-08-07

## Added

- Added SQLite models and typed contracts for Spaces, People, Organizations,
  Organization-Space relationships, Members, and mutable local module state.
- Added Space-authoritative backend services and APIs for universal foundation
  records.
- Added the deterministic fixed-ID `HardHead Works` default Space for records
  created before Space support.
- Added the permanent primary navigation for Today, Calendar, Work, Resources,
  Money, and Library, with Settings and Account kept separate.
- Added persistent active-Space selection and frontend Space context.
- Added local module registration under Settings with built-in Work and
  Inventory modules.
- Added isolated Firefox acceptance coverage for Space switching, persistence,
  backend isolation, module disable/re-enable behavior, route gating, and
  retained module data.

## Changed

- Advanced the internal SQLite schema from version 2 through version 4 while
  preserving supported Project, Task, Inventory, material-requirement, and
  migration-provenance data.
- Added required indexed `space_id` ownership to operational and
  browser-migration provenance records with restricted Space deletion.
- Rebuilt and backfilled existing operational records into the deterministic
  default Space while preserving IDs, relationships, timestamps, hashes,
  tombstones, and migration uniqueness.
- Made backend Space context authoritative for normal operational collection
  access instead of relying on frontend filtering.
- Made module enablement installation-wide product configuration while
  preserving module-owned backend data when a module is disabled.
- Updated application release identity to 0.8.0 and advanced the exact PWA
  shell to `foreman-shell-v0.8.0-c1`.
- Unified FastAPI metadata with the authoritative application-version
  constant.

## Reliability

- Rejected future SQLite schema versions before metadata-driven table creation
  can mutate a database.
- Added structural verification for foundation columns, primary keys, indexes,
  unique and check constraints, foreign keys, and restricted root deletion.
- Added restart-safe, state-aware SQLite table replacement, deterministic
  default-Space conflict handling, foreign-key verification, and recovery
  staging support across supported schema states.
- Corrected completed-schema restart validation so valid records may belong to
  any existing Space while foreign keys continue to reject orphan ownership.
- Preserved network-only API and mutation behavior and explicit service-worker
  update activation.

## Validation

- Added focused schema, constraint, migration, recovery, Space, module, and
  typed-contract coverage for the universal foundation.
- Verified existing-data migration, backup/restore compatibility, and portable
  export compatibility while retaining operational-fact schema version 1 and
  portable export format version 1.
- Completed final full backend acceptance with 288 tests passing.
- Completed final full frontend acceptance with 162 tests passing.
- Completed isolated disposable Firefox acceptance with 41 tests passing and
  verified removal of all disposable containers, networks, and images.

## Documentation

- Established the Constitution-first documentation authority order.
- Reconciled the permanent navigation as Today, Calendar, Work, Resources,
  Money, and Library, with Settings and Account below the primary categories.
- Documented one active Space for ordinary workflows and backend-enforced
  Space isolation.
- Defined factual Today through v0.8.6, Capacity in v0.9.0, Priority in v0.9.1,
  and the capacity-aware Morning Briefing through Today in v0.9.2.
- Established strict module ownership and local, non-commercial module
  registration under Settings.
- Kept the first v0.8.0 reconciliation change documentation-only before
  implementation began.
- Separated current implementation from the Version 1.0 target architecture.
- Reconciled persistence documentation with SQLite schema version 4 and the
  active-Space model.

---

# v0.7.5 — 2026-08-03

## Added

- Added an isolated Firefox and geckodriver browser-E2E harness
- Added fail-closed guards that reject live data and deployment material
- Added clean-deployment startup and navigation smoke coverage
- Added backend-authoritative Inventory, Project, material, and Task browser
  workflows
- Added deterministic connection-loss, safe-recovery, dirty-form, and
  open-dialog reload coverage
- Added verified clean-state and disposable-resource cleanup acceptance

## Changed

- Normalized Inventory, Project, and Task migration reporting through one
  shared aggregate reporter
- Updated the application and visible release version to 0.7.5
- Advanced the exact application shell to
  `foreman-shell-v0.7.5-c1`

## Reliability

- Added bounded, non-sensitive browser failure diagnostics
- Proved diagnostic capture through a controlled child Firefox failure
- Prevented browser automation from accessing live databases, mounts,
  volumes, trust material, or deployment secrets
- Required disposable acceptance deployments to begin with empty Inventory,
  Project, and Task collections
- Required disposable project containers, networks, and images to be absent
  after cleanup
- Preserved all persistent Docker volumes during browser-E2E teardown

## Validation

- Completed 200 backend tests against an isolated temporary SQLite database
- Completed 139 frontend tests
- Completed 39 Firefox browser-acceptance tests against a verified-empty
  disposable deployment
- Verified disposable cleanup left zero project containers, networks, or
  images
- Deliberately avoided live data, persistent volumes, trust material, and
  deployment secrets

---

# v0.7.4 — 2026-08-01

## Added

- Added verified SQLite backup snapshots and canonical recovery ZIP packages
- Added deterministic portable JSON export
- Added backup download, uploaded-package verification, restore-preflight, and
  restore-activation APIs
- Added durable expiring restore-preflight sessions with exact typed
  confirmation
- Added pre-restore safety backups, atomic activation, verification, automatic
  rollback, and emergency maintenance latching
- Added the Backup & Recovery utility workspace
- Added isolated destructive API round-trip validation using a disposable
  container and temporary SQLite database

## Changed

- Updated the application and visible release version to 0.7.4
- Advanced the exact application shell to
  `foreman-shell-v0.7.4-c1`
- Added a separate utility-navigation area without changing the primary module
  navigation
- Kept recovery transport centralized in frontend API utilities and free of
  browser persistence

## Reliability

- Kept backup, restore, and validation local-first
- Preserved non-sensitive recovery responses without exposing private paths
- Required verification before restore activation
- Required a durable safety backup before replacement
- Restored the original database automatically when activation verification
  failed
- Kept database access disabled through an emergency latch when activation and
  rollback both failed
- Prevented the recovery workflow from mixing application-shell generations

## Validation

- Completed 200 backend tests
- Completed 132 frontend tests
- Completed controlled Firefox backup download, portable export, and restore
  preflight validation
- Completed an isolated destructive round trip with no network, mounts,
  volumes, or access to the live `/data/foreman.db`
- Deliberately did not activate a restore against the live household database

---

# v0.7.3 — 2026-07-30

## Added

- Added four normalized operational fact types:
  `project.lifecycle`, `project.material-readiness`, `task.work-state`, and
  `inventory.stock-level`
- Added stable fact IDs, typed states, reason codes, evidence, source-record
  references, and deterministic ordering
- Added operational-fact `schemaVersion: 1` with fixed normalized `facts` and
  `summary` fields
- Added a shared frontend operations API that validates the normalized
  contract and preserves availability failures

## Changed

- Expanded `GET /api/operational-facts` to the approved nine-field response
  while retaining the six compatibility fields: `activeProjects`,
  `incompleteTasks`, `completedTasks`, `taskPriorityCounts`,
  `projectStatusCounts`, and `inventory`
- Derived facts on demand from one authoritative SQLite transaction snapshot
- Converged Dashboard Project and Inventory summaries onto backend facts
- Converged Project cards and material dialogs onto backend readiness facts
  and evidence
- Made normalized `inventory.stock-level` facts authoritative for frontend
  stock classification
- Updated the application and visible release version to 0.7.3
- Advanced the exact 29-resource application shell to
  `foreman-shell-v0.7.3-c2` so the precached version surface updates safely

## Removed

- Removed `frontend/utils/projectReadiness.js` and duplicate frontend Project
  readiness calculations
- Removed frontend numeric Inventory classification fallbacks

## Reliability

- Added a stable, non-sensitive HTTP 503 response for operational-fact
  database failures
- Kept missing Inventory availability unknown instead of fabricating zero
- Preserved explicit service-worker update activation and network-only API and
  mutation behavior
- Added no fact persistence or database migration; SQLite `user_version`
  remains 2

## Validation

- Added deterministic backend fact-engine and endpoint coverage
- Added focused frontend contract and operational-convergence coverage
- Completed automated, trusted-HTTPS, database-integrity, and controlled
  Firefox/WebDriver operational-convergence validation

---

# v0.7.2

## Added

- Installable PWA manifest with favicon, Apple touch icon, regular icons, and
  maskable icons
- Standalone iPhone launch support and dynamic safe-area handling
- Atomic, exact 29-resource static-shell cache
- Explicit, deferrable service-worker update activation
- Dirty-form and open-dialog protection during update activation and recovery
- Backend-authoritative availability gating through `/api/health`
- Private-LAN HTTPS through Caddy with restricted LAN-IP bindings

## Improved

- Kept API, migration, and mutation traffic network- and backend-owned
- Removed browser records as runtime fallback authority while retaining them
  as migration input, compatibility evidence, and recovery material
- Preserved Nginx as the static-file and `/api/` proxy authority behind Caddy
- Kept the backend private to the Compose network
- Updated application version metadata to 0.7.2
- Advanced the controlled shell cache to `foreman-shell-v0.7.2-c5`

## Security and Deployment

- Ignored local deployment configuration, trust exports, certificate files,
  private keys, and generated Caddy state
- Distributed only Caddy's public root certificate to the trusted physical
  iPhone
- Completed physical iPhone Home Screen installation, trusted HTTPS,
  standalone launch, backend-authoritative startup, and safe-area acceptance
- Kept the deployment private to the household LAN without adding public
  exposure or user authentication

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
