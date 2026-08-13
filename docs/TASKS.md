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

## Completed v0.7.5

- [x] Define browser-E2E architecture and acceptance boundaries.
- [x] Add an isolated Firefox and geckodriver harness.
- [x] Add guards that reject live data and deployment material.
- [x] Add clean-deployment startup and navigation smoke coverage.
- [x] Add backend-authoritative Inventory browser CRUD coverage.
- [x] Add Project and material browser CRUD coverage.
- [x] Add Task and Project compatibility browser coverage.
- [x] Add deterministic connection-loss and safe-recovery coverage.
- [x] Verify dirty-form and open-dialog reload protection.
- [x] Normalize Inventory, Project, and Task migration reporting.
- [x] Add bounded non-sensitive failure diagnostics.
- [x] Prove diagnostic capture through a controlled failure.
- [x] Complete isolated clean-deployment browser acceptance.
- [x] Reconcile v0.7.5 documentation and release metadata.
- [x] Complete v0.7.5 release validation.

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

## Completed v0.8.0 — Universal Navigation & Spaces

v0.8.0 was completed in nine reviewable commits:

- [x] Commit 1 — Reconcile architecture contracts and documentation.
- [x] Commit 2 — Add Space, Person, Organization, Member, and module-registry
  schema.
- [x] Commit 3 — Migrate existing records into the default Space.
- [x] Commit 4 — Add backend services and Space-authoritative APIs.
- [x] Commit 5 — Add the permanent navigation shell.
- [x] Commit 6 — Present active-Space-scoped operational data.
- [x] Commit 7 — Add local module registration and enablement behavior.
- [x] Commit 8 — Add compatibility and isolated browser acceptance coverage.
- [x] Commit 9 — Reconcile release documentation and version metadata.

Commit 1 was documentation-only. It did not change schema, APIs, frontend
navigation, migration behavior, runtime version metadata, cache identity,
Docker deployment, or live data.

Commit 2 established schema and typed contracts only. Commit 3 advanced the
internal SQLite schema to version 4, created the fixed-ID default Space
deterministically, and assigned existing operational and browser-migration
records to it.

Commits 4 through 8 completed Space-authoritative APIs, permanent navigation,
active-Space frontend context, local module registration, restart-safe
multi-Space compatibility, and isolated browser acceptance. Commit 9 closes
the milestone with v0.8.0 release identity and documentation reconciliation.

## Approved Universal Foundation Sequence

- [x] v0.8.0 — Universal Navigation & Spaces
- [x] v0.8.1 — Universal Work System
- [x] v0.8.2 — Tools, Inventory & Care
- [x] v0.8.3 — Calendar & Scheduling
- [ ] v0.8.4 — Money
- [ ] v0.8.5 — Library, Records & Search
- [ ] v0.8.6 — Today Workspace & Household Proving Ground
- [ ] v0.9.0 — Capacity Engine
- [ ] v0.9.1 — Priority Engine
- [ ] v0.9.2 — Morning Briefing

The dependency order is:

Modules provide authoritative facts → Calendar records commitments and
availability → Capacity determines realistic eligibility → Priority ranks
eligible Work → Morning Briefing presents explainable recommendations.

## Completed v0.8.1 — Universal Work System

Architecture review completed before implementation.

Approved direction:

- [x] Preserve Tasks and Projects as distinct authoritative record types.
- [x] Define Work as the owning domain and integration boundary rather than a
      universal persistence superclass.
- [x] Preserve native Task and Project lifecycle semantics.
- [x] Preserve existing Task and Project APIs and browser migration provenance.
- [x] Use same-Space Members for optional Work responsibility.
- [x] Treat Task due dates as Work facts rather than Calendar commitments.
- [x] Retain Project material requirements as the first concrete Work
      requirement type.
- [x] Define Work dependencies as factual relationships without Capacity,
      Priority, scheduling, or recommendation behavior.
- [x] Define a normalized Work read model as derived backend state rather than
      duplicate persistence authority.

Completed implementation sequence:

1. Documentation-only Universal Work architecture contract.
2. Safe persistence and schema upgrade for new Work relationships.
3. Responsibility and Task-date behavior.
4. Work dependency relationships.
5. Backend normalized Work read model.
6. Universal Work frontend convergence.
7. Isolated browser compatibility acceptance.
8. v0.8.1 release reconciliation.

v0.8.1 was completed in eight reviewable commits. Commits 1 through 7
established the Universal Work architecture, schema and persistence support,
responsibility and Task due dates, factual dependencies, normalized Work read
model, frontend convergence, and isolated compatibility acceptance. Commit 8
closes the milestone with v0.8.1 release identity and documentation
reconciliation.

Commit 1 is documentation-only. It does not change the SQLite schema,
application version, PWA cache identity, APIs, frontend runtime behavior,
migration behavior, Docker deployment, or live data.

Explicitly deferred beyond v0.8.1:

- Capacity eligibility
- Priority ranking
- automatic recommendations
- automatic optional-Work placement
- Calendar scheduling behavior
- recurrence ownership
- generalized future-module requirement systems
- Morning Briefing decision logic

## Completed v0.8.2 — Tools, Inventory & Care

Architecture review:

- [x] Preserve Resources as a category and integration boundary rather than a
      universal Resource persistence model.
- [x] Preserve Inventory as the consumable-stock authority.
- [x] Define Tools as the durable-equipment authority.
- [x] Define Care Plans as the upkeep-definition authority.
- [x] Keep Calendar scheduling and recurrence ownership in v0.8.3.
- [x] Keep Capacity, Priority, and recommendation behavior deferred.
- [x] Preserve missing referenced-resource evidence instead of silently
      deleting requirement relationships.
- [x] Preserve the existing Mealworms workspace without inventing husbandry
      architecture during v0.8.2.

Completed implementation sequence:

1. [x] Reconcile v0.8.2 architecture and current-state documentation.
2. [x] Add Tools/Care persistence with a safe SQLite schema-v6 upgrade and
       recovery contract.
3. [x] Add backend-authoritative Tools CRUD, active-Space isolation, and module
       registration.
4. [x] Add Care Plans and factual Tool maintenance history.
5. [x] Add concrete Work-to-Tool requirements for supported Tasks and Projects.
6. [x] Converge the Resources frontend around Tools, Inventory, and Care while
       preserving Mealworms compatibility.
7. [x] Add factual Resources operational facts or overview data where justified
       without implementing Capacity.
8. [x] Complete isolated disposable browser compatibility acceptance.
9. [x] Reconcile v0.8.2 release identity, documentation, and Green Build.

v0.8.2 completes the Resources milestone with separate Tools, Inventory, and
Care authorities; factual Tool maintenance history; concrete Work-to-Tool
requirements; Resources frontend convergence; and isolated browser acceptance.
Final release validation passes 328 backend tests, 187 frontend tests, and 44
disposable Firefox tests while preserving operational-fact schema version 1,
portable export format version 1, active-Space isolation, and the deferred
Calendar/Capacity/Priority boundaries.

Commit 1 is documentation-only. It does not change the SQLite schema,
application version, PWA cache identity, APIs, frontend runtime behavior,
migration behavior, Docker deployment, or live data.

## Completed v0.8.3 — Calendar & Scheduling

Architecture review:

- [x] Preserve Calendar as the authority for commitments, events, routines,
      recurrence, and explicitly recorded availability.
- [x] Keep Calendar recordkeeping separate from Capacity feasibility and
      capacity-aware scheduling decisions.
- [x] Require backend-authoritative active-Space isolation for Calendar data.
- [x] Use a configured IANA timezone and deterministic timezone-aware
      date/time behavior.
- [x] Preserve local wall-clock meaning for recurring routines across timezone
      offset and daylight-saving changes.
- [x] Keep initial recurrence deliberately narrow and deterministic rather than
      introducing a generalized scheduling-rule engine.
- [x] Derive bounded recurring occurrences instead of indefinitely
      materializing occurrence rows.
- [x] Allow optional same-Space Member association without introducing a
      generalized attendee or invitation system.
- [x] Keep Work authoritative for Work-to-Calendar relationships while
      Calendar remains authoritative for referenced Calendar records.
- [x] Preserve missing referenced-Calendar evidence rather than silently
      deleting relationship history.
- [x] Keep operational-fact schema version 1 and portable export format version
      1 unchanged throughout v0.8.3.
- [x] Require additive schema-v7 migration and backup/restore compatibility
      before household deployment.
- [x] Keep Capacity, Priority, recommendations, and automatic optional-Work
      placement deferred.

Planned implementation sequence:

1. [x] Reconcile v0.8.3 architecture and current-state documentation.
2. [x] Add Calendar persistence with a safe SQLite schema-v7 upgrade and
       recovery contract.
3. [x] Add Calendar settings, fixed commitments/events/availability, active-
       Space isolation, and optional same-Space Member association.
4. [x] Add deterministic recurring Calendar series, exclusions, timezone/DST
       behavior, and bounded occurrence expansion.
5. [x] Add concrete Work-to-Calendar relationships with retained missing-target
       evidence and Work-owned lifecycle behavior.
6. [x] Replace the Calendar placeholder with the selected-Space Calendar
       frontend and fixed-record workflows.
7. [x] Converge recurring routines, Member filtering, and Calendar module
       behavior without introducing Capacity.
8. [x] Complete isolated disposable browser compatibility acceptance.
9. [x] Reconcile v0.8.3 release identity, documentation, and Green Build.

Commit 1 remains documentation-only. It does not change SQLite schema version 6,
application version 0.8.2, PWA cache identity, APIs, frontend runtime behavior,
migration behavior, Docker deployment, or live household data.

## Planned v0.8.4 — Money

Architecture review:

- [x] Preserve Money as the authority for financial records and explicit
      user-entered financial plans.
- [x] Use Space-authoritative Accounts, Categories, Transactions, Budgets, and
      Obligations as the v0.8.4 factual core.
- [x] Represent income, revenue, and expenses through factual Transactions
      rather than separate competing ledgers.
- [x] Treat recurring costs as Money-owned obligations without introducing
      scheduling, Capacity, or recommendation authority.
- [x] Use explicit Money relationship evidence for approved links to Work,
      Resources, People, and Organizations without transferring ownership.
- [x] Preserve the permanent Money primary-navigation destination and treat the
      retained Budget child route as compatibility surface during convergence.
- [x] Advance SQLite schema version 7 to version 8 through an additive,
      idempotent, verified upgrade.
- [x] Keep backup format version 1 unchanged; full database snapshots include
      new Money tables automatically.
- [x] Keep portable export format version 1 unchanged and deliberately outside
      the v0.8.4 Money contract.
- [x] Keep operational-fact schema version 1 unchanged unless a later reviewed
      Money fact contribution explicitly requires a contract change.
- [x] Keep affordability inference, Capacity, Priority, Morning Briefing
      recommendations, AI interpretation, forecasting, full accounting, tax
      accounting, commercialization, billing, subscriptions, and entitlement
      architecture deferred.

Planned implementation sequence:

1. [x] Reconcile v0.8.4 architecture and current-state documentation.
2. [ ] Add Money persistence with a safe SQLite schema-v8 upgrade and recovery
       compatibility.
3. [ ] Add Space-authoritative Accounts and Categories.
4. [ ] Add factual Transactions for income, revenue, and expenses.
5. [ ] Add Budgets, Obligations, and recurring-cost records without Capacity or
       recommendation behavior.
6. [ ] Add explicit cross-domain Money relationships with retained evidence
       where required by the approved relationship contract.
7. [ ] Replace the Money/Budget placeholder experience with the selected-Space
       Money frontend while preserving compatible navigation.
8. [ ] Complete isolated disposable browser compatibility acceptance.
9. [ ] Reconcile v0.8.4 release identity, documentation, and Green Build.

Commit 1 is documentation-only. It does not change SQLite schema version 7,
application version 0.8.3, PWA cache identity, APIs, frontend runtime behavior,
migration behavior, Docker deployment, portable export format, backup format,
operational-fact schema, or live household data.

## v0.8.0 Architecture Boundaries

- Ordinary workflows use one clearly selected active Space.
- Backend APIs enforce Space isolation; frontend filtering is insufficient.
- Existing Projects, Tasks, and Inventory migrate into a default Space.
- People and Organizations receive minimal stable identity and relationships.
- A Member represents operational participation in a Space.
- Members remain separate from authentication credentials and user accounts.
- Broad multi-Space aggregation is deferred beyond ordinary v0.8.0 workflows.

## Cross-Cutting Architecture Boundaries

- Modules own and validate their authoritative records.
- Modules communicate through stable IDs, relationships, services, APIs,
  and approved operational facts.
- Modules must not manipulate another module's private tables or duplicate
  authority in the frontend.
- Today presents factual current state through v0.8.6.
- Today must not claim feasibility, rank Work, or recommend next actions
  before Capacity and Priority are implemented.
- Calendar may record commitments, events, routines, recurrence, and
  availability before Capacity exists.
- Capacity must precede optional-Work placement, feasibility claims,
  prioritization, recommendations, and capacity-aware scheduling decisions.

## Module Registry and Deployment Boundaries

- The module registry is local configuration only.
- It records module identity, description, enabled state, dependencies,
  contribution locations, safe enable-disable behavior, data retention,
  and module health.
- It must not contain subscriptions, billing, licensing, plans, tiers,
  entitlements, or customer-provisioning behavior.
- HardHead remains local and LAN-only through Version 1.0.
- Secure persistent remote access begins no earlier than Version 1.1.
- Commercial SaaS and subscription infrastructure remain deferred until
  after Version 3.0 unless the founder explicitly reopens that direction.

## Remaining Foundation and Deferred Work

- [ ] Implement scheduled backups.
- [ ] Implement estimated Project completion.
- [ ] Implement Project templates.
- [ ] Expand Task-to-Project editing and display.
- [ ] Add a richer Project Migration Report UI and metrics.
- [ ] Add an approved last-known backend read-only fallback after reload failures.
- [ ] Retire retained legacy Project storage only after recovery requirements
      are satisfied.
- [ ] Complete archive cleanup.
- [ ] Add notifications after the owning operational facts exist.
- [ ] Add equipment-rental support after the universal resource foundation.
- [ ] Add AI-assisted advice only after deterministic foundations are complete.

## Backlog

- [ ] Barcode scanner.
- [ ] CSV import and export.
- [ ] Mobile companion app.
- [ ] PostgreSQL planning for Version 2 consideration.
