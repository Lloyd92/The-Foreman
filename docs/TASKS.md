# Current Sprint

Tasks should remain small, testable, and compatible with a Green Build.

## Active

- [ ] Implement v0.7.2 backend-authoritative Project readiness.
- [ ] Unify Project and Inventory readiness in operational facts.
- [ ] Plan v0.7.3 backup, export, restore, and verification.

## Completed

- [x] Complete v0.5.4 inventory sorting.
- [x] Complete v0.5.4 Dashboard inventory alerts.
- [x] Integrate v0.5.4 inventory updates with the Dashboard.
- [x] Add the v0.6.1 Projects workspace shell.
- [x] Add v0.6.1 project summary cards.
- [x] Add v0.6.1 search, status-filter, and sorting controls.
- [x] Add v0.6.1 navigation integration.
- [x] Add v0.6.1 add-project placeholder behavior.
- [x] Activate both v0.6.2 add-project actions.
- [x] Add v0.6.2 browser-local project creation and persistence.
- [x] Render persistent v0.6.2 project details and progress.
- [x] Make v0.6.2 project search, status filtering, sorting, and summaries
      functional.
- [x] Remove user-facing project archiving from the approved v0.6.2 scope.
- [x] Add v0.6.3 browser-local project editing.
- [x] Reuse and prepopulate the project dialog for edits.
- [x] Preserve project identity and creation time while recording edit time.
- [x] Add v0.6.3 confirmed permanent project deletion.
- [x] Keep project controls, summaries, search, filtering, and sorting in sync.
- [x] Add v0.6.4 browser-local project material requirements.
- [x] Link requirements to Inventory records by authoritative item ID.
- [x] Add deterministic Project readiness and shortage calculations.
- [x] Add the focused Materials dialog and confirmed requirement removal.
- [x] Add Project readiness indicators and Dashboard readiness summaries.
- [x] Preserve missing Inventory references without mutating Project data.
- [x] Establish the Project service and repository layers.
- [x] Persist Projects and material requirements in backend SQLite.
- [x] Add versioned, idempotent SQLite schema upgrades.
- [x] Add the durable, idempotent Project migration endpoint.
- [x] Migrate retained browser Projects without rewriting the source records.
- [x] Enforce Inventory → Project → Task startup migration ordering.
- [x] Connect the Projects workspace to backend-authoritative Project APIs.
- [x] Source Dashboard Project summaries from backend Projects.
- [x] Preserve Task compatibility when migrated Projects are mapped or deleted.
- [x] Expand automated Project migration, API, runtime, and backend tests.
- [x] Complete manual browser CRUD, materials, persistence, Dashboard, and Task
      compatibility acceptance for v0.7.1.
- [x] Reconcile v0.7.1 documentation and release metadata.

## Current Feature Work

The Projects workspace now uses backend persistence, but the wider Projects
module remains incomplete:

- [x] Implement project creation.
- [x] Implement project persistence.
- [x] Implement material requirements.
- [x] Implement progress tracking.
- [ ] Implement estimated completion.
- [ ] Implement project templates.
- [x] Implement project notes.
- [x] Verify completed v0.7.1 Projects behavior.
- [ ] Add expanded Task-to-Project editing and display.
- [ ] Retire legacy Project storage only after an approved recovery plan.
- [ ] Complete archive cleanup.

## Version 1.0 Foundation Work

- [ ] Implement the Morning Briefing as the Dashboard's default workspace.
- [ ] Implement the Capacity Engine.
- [ ] Integrate Priority ranking after Capacity eligibility.
- [x] Establish the service layer foundation.
- [x] Establish the repository layer foundation.
- [x] Establish the SQLite database foundation.
- [ ] Implement manual backup.
- [ ] Implement scheduled backup.
- [ ] Implement restore.
- [ ] Implement restore verification.
- [x] Establish automated frontend and backend testing.
- [x] Keep completed foundation increments runnable and verifiable.

## Deferred Core Convergence Work

- [ ] Move Project readiness calculations to the backend.
- [ ] Add unified operational facts for Project readiness.
- [ ] Add backup and restore workflows with verification.
- [ ] Establish browser end-to-end test infrastructure.
- [ ] Add a richer Project Migration Report UI and metrics.
- [ ] Add an approved last-known backend read-only fallback after reload
      failures.
- [ ] Implement estimated Project completion.
- [ ] Implement Project templates.
- [ ] Retire retained legacy Project storage only after recovery requirements
      are satisfied.

## Backlog

- [ ] Barcode scanner.
- [ ] CSV import and export.
- [ ] Mobile companion app.
- [ ] PostgreSQL planning for Version 2 consideration.
