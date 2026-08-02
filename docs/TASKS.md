# Current Sprint

Tasks should remain small, testable, and compatible with a Green Build.

## Completed v0.7.3

- [x] Reconcile v0.7.3 roadmap and task ownership.
- [x] Add typed operational-fact schemas and stable reason codes.
- [x] Build pure deterministic fact calculations.
- [x] Read Projects, materials, Tasks, and Inventory from one transaction
      snapshot.
- [x] Add canonical ordering and stable fact IDs.
- [x] Represent missing Inventory references with null availability.
- [x] Add `schemaVersion: 1`, normalized facts, and summary to
      `/api/operational-facts`.
- [x] Preserve existing top-level response fields during the compatibility
      window.
- [x] Add database-failure handling with a stable, non-sensitive 503 response.
- [x] Add frontend `operationsApi` consumption.
- [x] Move Dashboard lifecycle, readiness, and shortage summaries to backend
      facts.
- [x] Move Project cards and material dialogs to backend readiness facts.
- [x] Move Inventory stock classification to backend facts.
- [x] Remove frontend Project readiness calculation after convergence.
- [x] Remove Inventory numeric fallback classification.
- [x] Preserve browser migration data only as migration and recovery evidence.
- [x] Revise the exact 29-resource service-worker shell for frontend
      convergence and release identity.
- [x] Add focused backend and frontend tests.
- [x] Complete controlled browser operational-convergence validation.
- [x] Reconcile documentation, continuity principles, and version metadata.
- [x] Complete v0.7.3 release validation.

## Completed v0.7.4

- [x] Add verified manual backup packages.
- [x] Add deterministic portable JSON export.
- [x] Add uploaded backup verification.
- [x] Add durable restore preflight sessions.
- [x] Require exact confirmation before activation.
- [x] Add exclusive database-maintenance coordination.
- [x] Create durable pre-restore safety backups.
- [x] Add atomic restore activation and post-activation verification.
- [x] Add automatic verified rollback.
- [x] Add emergency maintenance latching for double failure.
- [x] Add controlled restore API endpoints.
- [x] Add frontend recovery API utilities.
- [x] Add the Backup & Recovery utility workspace.
- [x] Advance the PWA shell for recovery delivery.
- [x] Validate backup and export downloads in the browser.
- [x] Validate restore preflight in the browser without live activation.
- [x] Validate the complete destructive API round trip in an isolated
      disposable container.
- [x] Complete v0.7.4 release validation.

## Active v0.7.5

- [x] Define browser-E2E architecture and acceptance boundaries.
- [ ] Add an isolated Firefox and geckodriver harness.
- [ ] Add guards that reject live data and deployment material.
- [ ] Add clean-deployment startup and navigation smoke coverage.
- [ ] Add backend-authoritative Inventory browser CRUD coverage.
- [ ] Add Project and material browser CRUD coverage.
- [ ] Add Task and Project compatibility browser coverage.
- [ ] Add deterministic connection-loss and safe-recovery coverage.
- [ ] Verify dirty-form and open-dialog reload protection.
- [ ] Normalize Inventory, Project, and Task migration reporting.
- [ ] Add bounded non-sensitive failure diagnostics.
- [ ] Prove diagnostic capture through a controlled failure.
- [ ] Complete isolated clean-deployment browser acceptance.
- [ ] Reconcile v0.7.5 documentation and release metadata.
- [ ] Complete v0.7.5 release validation.

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
- [x] Add v0.7.2 PWA identity, manifest, and installation assets.
- [x] Add controlled v0.7.2 static-shell caching.
- [x] Add the explicit, deferrable service-worker update lifecycle.
- [x] Protect updates and recovery while forms are dirty or dialogs are open.
- [x] Gate operations on backend and database availability.
- [x] Remove browser records as runtime fallback authority.
- [x] Add private-LAN HTTPS with restricted host bindings.
- [x] Complete physical iPhone certificate trust and Home Screen installation.
- [x] Complete standalone launch and dynamic safe-area acceptance.
- [x] Reconcile v0.7.2 version metadata and release documentation.
- [x] Complete v0.7.2 final release validation.

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
- [x] Implement manual backup.
- [ ] Implement scheduled backup.
- [x] Implement restore.
- [x] Implement restore verification.
- [x] Establish automated frontend and backend testing.
- [x] Keep completed foundation increments runnable and verifiable.

## Deferred Core Convergence Work

- [ ] Establish browser end-to-end test infrastructure.
- [ ] Add a richer Project Migration Report UI and metrics.
- [ ] Add an approved last-known backend read-only fallback after reload
      failures.
- [ ] Implement estimated Project completion.
- [ ] Implement Project templates.
- [ ] Retire retained legacy Project storage only after recovery requirements
      are satisfied.

## Deferred Operational and Module Work

- [ ] Add due dates and overdue or due-soon facts.
- [ ] Add Project dependencies and prerequisites.
- [ ] Add blocked Task and Project states.
- [ ] Add Inventory allocation, reservation, and cross-Project demand.
- [ ] Add historical operational observations.
- [ ] Add capacity-aware prioritization and recommendations.
- [ ] Add Morning Briefing narration.
- [ ] Add notifications.
- [ ] Add recurring responsibilities.
- [ ] Add Finance.
- [ ] Add equipment rentals.
- [ ] Add AI-assisted advice only after deterministic foundations are complete.

## Backlog

- [ ] Barcode scanner.
- [ ] CSV import and export.
- [ ] Mobile companion app.
- [ ] PostgreSQL planning for Version 2 consideration.
