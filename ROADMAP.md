# The Foreman Roadmap

This roadmap outlines the planned evolution of The Foreman.

It is a living document and will evolve as HardHead Works grows.

Items marked as completed represent stable milestones.

Future versions may change as new requirements emerge through real workshop use.

---

# Guiding Philosophy

The Foreman is developed one working version at a time.

Every release should leave the project in a usable state.

Architecture comes before features.

Features come before optimization.

Optimization comes before expansion.

The Foreman must first become trustworthy before it becomes adaptive.

Features should preserve or restore operational continuity rather than create
another disconnected place to store information.

---

# Completed Releases

## v0.1 — Foundation ✅

Status: Complete

Goals:

- Initial project structure
- Docker environment
- Frontend and backend communication
- Local development environment

Major accomplishments:

- Docker Compose
- Flask backend
- Nginx frontend
- Development workflow established

---

## v0.2 — Dashboard ✅

Status: Complete

Goals:

- Workshop dashboard
- System status
- Greeting
- Initial layout

Major accomplishments:

- Dashboard UI
- Status indicators
- Application shell

---

## v0.3 — Tasks ✅

Status: Complete

Goals:

- Task management
- Persistent storage

Major accomplishments:

- Task creation
- Task completion
- Local storage
- Task priorities

---

## v0.4 — Modular Architecture ✅

Status: Complete

Goals:

- Refactor project architecture

Major accomplishments:

- Page modules
- Router
- Storage module
- API module
- Clean application startup
- Improved maintainability

---

## v0.5 — Inventory System ✅

Status: Complete

Completed

### v0.5.1

- Inventory workspace
- Professional layout
- Summary cards
- Search and filter UI
- Empty state

### v0.5.2

- Persistent inventory
- Add inventory items
- Inventory dialog
- Local storage
- Low-stock detection

### v0.5.3

- Edit inventory
- Delete inventory
- Live search
- Category filtering
- Stock filtering

### v0.5.4

- Inventory sorting
- Dashboard inventory alerts
- Dashboard integration

Status: Complete

Deferred inventory ideas:

- CSV import/export
- Barcode support
- Improved reporting
- Bulk inventory actions

---

# Completed Project Releases

## v0.6 — Projects ✅

Status: Complete

Completed

### v0.6.1

- Projects workspace shell
- Project summary cards
- Search controls
- Status filtering
- Sorting controls
- Add-project placeholder behavior
- Navigation integration

### v0.6.2

- Browser-local project creation and persistence
- Project details, descriptions, notes, dates, costs, priorities, and progress
- Functional project search, status filtering, and sorting
- Persistent project cards and live project summary counts

### v0.6.3

- Browser-local project editing with reusable Add/Edit dialog
- Persistent status, progress, and project-detail updates
- Confirmed permanent project deletion
- Preservation of project identity and creation timestamps during edits

### v0.6.4

- Browser-local project material requirements linked by Inventory item ID
- Deterministic available, required, shortage, and readiness calculations
- Focused Project Materials dialog with confirmed requirement removal
- Project-card readiness indicators and Dashboard readiness summaries
- Missing Inventory references remain visible without changing project data

# Active Release

## v0.7 — Core Convergence 🚧

The v0.7 sequence moves established browser capabilities onto durable shared
foundations before additional operational modules are introduced.

### v0.7.1 — Project Backend Convergence ✅

Status: Complete

Completed:

- Persistent backend Project storage
- Persistent Project material requirements
- Safe, versioned SQLite schema upgrades
- Durable and idempotent Project migration endpoint
- Retained browser Project migration with stable source mappings
- Inventory → Project → Task startup migration ordering
- Backend-authoritative Projects workspace
- Dashboard summaries sourced from backend Projects
- Task reference compatibility when Projects migrate or are deleted
- Expanded frontend and backend automated tests
- Completed manual browser CRUD and persistence acceptance

### v0.7.2 — PWA Foundation ✅

Status: Complete

Completed:

- PWA metadata and complete installation assets
- Controlled 29-resource static-shell caching and explicit update lifecycle
- Dirty-form and open-dialog protection during update activation
- HardHead availability and backend-authority protection
- Browser records retained as migration evidence without runtime fallback
  authority
- Private-LAN HTTPS through Caddy with restricted host bindings
- Physical iPhone certificate trust, Home Screen installation, and standalone
  launch acceptance
- Dynamic safe-area correction acceptance
- Household-first deployment at the current private IP origin

The v0.7.2 deployment is private to the household LAN. It adds no public
Internet exposure or user authentication. `hardhead.home.arpa` remains a
future LAN-DNS goal.

### v0.7.3 — Unified Operational Facts ✅

Status: Complete

Purpose:

Create one backend-authoritative, deterministic fact layer for Projects,
material readiness, Tasks, and Inventory so different pages cannot
independently produce contradictory interpretations.

Completed:

- Typed, deterministic facts computed on demand from backend-authoritative
  SQLite records
- One explicit transaction snapshot for all source records
- Stable fact IDs, canonical ordering, typed states, reason codes, evidence,
  and source-record references
- `schemaVersion: 1`, normalized `facts`, and fixed `summary` sections on
  `GET /api/operational-facts`
- Six retained top-level compatibility fields within the approved nine-field
  response
- Stable, non-sensitive HTTP 503 behavior for database query failures
- No persisted fact table or database migration; SQLite schema version remains
  2
- Shared frontend operations API with normalized-contract validation
- Dashboard lifecycle, readiness, and stock summaries sourced from backend
  facts
- Project cards and material dialogs sourced from backend readiness evidence
- Backend-authoritative Inventory stock classification
- Removal of duplicate frontend Project-readiness calculations and numeric
  Inventory fallbacks
- Automated backend and frontend validation plus controlled browser
  operational-convergence validation
- Exact 29-resource PWA shell advanced to
  `foreman-shell-v0.7.3-c2` for release-version finalization
- Browser records excluded from fact inputs and runtime fallback authority

Fact vocabulary and states:

- `project.lifecycle`: `planning`, `active`, `on-hold`, `completed`, `archived`,
  or `invalid`.
- `project.material-readiness`: `ready`, `needs-materials`, `not-applicable`,
  or `invalid`.
- `task.work-state`: `open` or `completed`.
- `inventory.stock-level`: `in-stock`, `low-stock`, `out-of-stock`, or
  `invalid`.

Material-readiness boundary:

- No material requirements means `not-applicable`, not `ready`.
- A missing Inventory reference means availability is unknown. Its evidence
  uses a null available quantity rather than a fabricated zero.
- Readiness evaluates one Project independently. It does not represent
  allocation, reservation, or combined demand across Projects.
- Dashboard and Projects consume the same backend readiness fact.
- Inventory uses backend stock-level facts without a frontend numeric
  classification fallback.

This milestone provides trustworthy inputs for the future Morning Briefing. It
does not implement briefing narration or recommendation logic.

Explicitly excluded:

- Project dependencies or prerequisites
- Blocked Task rules
- Task due-soon or overdue facts
- Project-overdue facts
- Household-timezone policy
- Next actionable step selection
- Inventory allocation or reservation
- Aggregate cross-Project material demand
- System-health facts inside the database-backed facts endpoint
- Migration-required detection
- Historical change tracking or persisted fact snapshots
- Severity scoring, prioritization, or recommended actions
- Notifications, narrative generation, heuristics, or AI
- Backup or restore
- Authentication or external access
- Database schema migration

### v0.7.4 — Backup, Export, Restore, and Verification ✅

Status: Complete

Completed:

- Added verified SQLite snapshots and canonical recovery ZIP packages
- Added deterministic portable JSON export
- Added download and uploaded-package verification APIs
- Added durable restore preflight sessions with exact confirmation
- Added pre-restore safety backups on the live database filesystem
- Added exclusive database-maintenance coordination
- Added atomic activation, post-activation verification, automatic rollback,
  and emergency maintenance latching
- Added the Backup & Recovery utility workspace
- Added frontend recovery API utilities with fail-closed contract validation
- Added explicit PWA update protection while recovery forms are active
- Added isolated destructive API round-trip validation against a disposable
  temporary database
- Completed automated and controlled browser validation without activating a
  restore against live data
- Advanced the exact application shell to
  `foreman-shell-v0.7.4-c1` for release finalization

Explicitly excluded:

- Scheduled or automatic backups
- Cloud storage or remote backup destinations
- Authentication or external access
- Public recovery endpoints
- Testing Mode orchestration
- Legacy browser-storage retirement

### v0.7.5 — Frontend Hardening and Browser E2E ✅

Status: Complete

This completed milestone follows v0.7.4.

Architecture:

- Use Firefox and geckodriver as the first supported browser path
- Keep automation dependencies outside production runtime images
- Run mutating E2E workflows only against an isolated disposable deployment
- Fail closed unless live data and deployment material are excluded
- Assert backend-authoritative outcomes through stable browser selectors
- Capture bounded, non-sensitive diagnostics when workflows fail
- Normalize migration reporting without creating another persistence authority

Completed sequence:

1. Define browser-E2E architecture and acceptance boundaries
2. Add the isolated Firefox/WebDriver harness
3. Add clean-deployment startup and navigation smoke coverage
4. Add backend-authoritative browser CRUD workflows
5. Add deterministic connection-loss and safe-recovery coverage
6. Normalize migration reporting and improve diagnostics
7. Complete isolated clean-deployment browser acceptance
8. Finalize and release v0.7.5

Objectives:

- Establish repeatable browser end-to-end testing
- Harden frontend failure and recovery behavior
- Improve migration reporting and diagnostics
- Verify supported browser workflows from clean deployments

Explicitly excluded:

- Morning Briefing, Capacity, or Priority behavior
- Authentication or external access
- Mobile Safari and additional browser automation
- Cloud CI infrastructure
- Live-data mutation or restore activation
- Legacy browser-storage retirement

Deferred Project work:

- Estimated completion
- Project templates
- Expanded Task-to-Project editing and display
- Legacy Project storage retirement
- Archive cleanup
- Purchasing, reservations, and allocations

These items remain outside v0.7.1 and must be scheduled explicitly.

---

# Universal Foundation Roadmap

The v0.8 series establishes a universal operating structure before The Foreman
adds deterministic Capacity, Priority, and Morning Briefing behavior.

The approved dependency sequence is documented in
`docs/V0_8_UNIVERSAL_ARCHITECTURE.md`.

## v0.8.0 — Universal Navigation & Spaces ✅

Status: Complete

Purpose:

Establish the stable application structure and authoritative Space context
required by every later universal capability.

Scope:

- Install the permanent primary navigation:
  - Today
  - Calendar
  - Work
  - Resources
  - Money
  - Library
- Keep Settings and Account separate below primary navigation
- Add Personal, Household, Workshop, and future HardHead Works Space support
- Use one clearly selected active Space for ordinary operational workflows
- Enforce Space isolation through backend services and APIs
- Add minimal People and Organizations foundations
- Add Members as operational Space-participation records
- Keep Members separate from authentication and authorization
- Add local module registration under Settings
- Migrate existing Projects, Tasks, Inventory, and related records into one
  approved deterministic default Space
- Preserve backup, restore, export, migration, and browser acceptance behavior

Explicitly excluded:

- Complete universal Work convergence
- Tools and Care Plans
- Calendar scheduling behavior
- Money and Library behavior
- Completed Today aggregation
- Capacity, Priority, and Morning Briefing behavior
- Authentication, authorization, or remote access
- CRM, purchasing, sales, and supplier-management workflows
- Subscriptions, billing, commercial entitlements, and SaaS tenancy

## v0.8.1 — Universal Work System ✅

Status: Complete

Purpose:

Unify operational work beneath the permanent Work category.

Scope:

- Tasks
- Projects
- Requirements
- Dependencies
- Progress
- Shared Space, responsibility, status, date, relationship, and lifecycle concepts
- Compatibility with existing Tasks and Projects

Work may reference Calendar routines or scheduled occurrences through stable
IDs and relationships, but it does not own routine definitions.

Architecture boundary:

- Work is the owning domain and integration boundary, not a universal
  `work_items` persistence superclass.
- Existing Task and Project records, APIs, migration provenance, and native
  lifecycle semantics remain authoritative.
- Universal Work may provide normalized read models and shared relationships
  without duplicating persistence authority.
- Responsibility references a Member participating in the same active Space.
- Task due dates are Work facts and do not imply Calendar commitments,
  scheduled work, or available Capacity.
- Existing Project material requirements remain the first concrete Work
  requirement type.
- Dependencies are factual Work relationships, not scheduling, feasibility,
  ranking, or recommendation behavior.

Explicitly excluded:

- Capacity eligibility
- Priority ranking
- Automatic recommendations

## v0.8.2 — Tools, Inventory & Care ✅

Status: Complete

Purpose:

Establish the permanent Resources category while preserving separate
authorities for durable equipment, consumable stock, and upkeep.

Architecture boundary:

- Resources is a category and integration boundary, not a universal Resource
  persistence superclass.
- Tools owns durable equipment, condition, location, factual availability,
  notes, and maintenance history.
- Inventory remains the existing consumable-stock authority and preserves its
  proven persistence, API, migration, and Project-material compatibility.
- Existing Inventory records are not automatically reclassified as Tools.
- Care Plans owns upkeep definitions and may exist independently or optionally
  reference a Tool.
- Care frequency metadata does not create Calendar recurrence or scheduled
  occurrences.
- Work owns concrete Tool requirement relationships for supported Tasks and
  Projects.
- Missing Tool references remain evidence rather than being silently deleted.
- Tools and Care remain separate module authorities beneath Resources.
- The existing Mealworms workspace remains compatibility surface and is not
  silently converted into Care.

Scope:

- Tools as durable equipment
- Inventory as consumable stock, quantities, thresholds, locations, and usage
- Tool location, condition, and factual availability
- Tool maintenance and service history
- Care Plans for service, inspections, cleaning, property upkeep, maintenance,
  and future husbandry care definitions
- Concrete Work-to-Tool requirements without cross-module ownership
- Active-Space authority and isolation
- Backup and restore compatibility
- Resources frontend convergence
- Isolated browser compatibility acceptance

Explicitly excluded:

- Universal `resources` or `resource_items` persistence
- Generalized future-module requirement systems
- Automatic Inventory-to-Tool conversion
- Purchasing workflows
- Supplier-management expansion
- Equipment rental
- Calendar scheduling or scheduled Care occurrences
- Capacity eligibility
- Priority ranking
- Automatic recommendations
- Morning Briefing decision logic

## v0.8.3 — Calendar & Scheduling ✅

Status: Complete

Purpose:

Record commitments, availability, and schedule information without claiming
that optional Work is feasible.

Architecture contract:

- Calendar is authoritative for commitments, events, routines, recurrence, and
  explicitly recorded availability.
- Calendar recordkeeping is separate from capacity-aware scheduling.
- Ordinary Calendar operations are scoped authoritatively to the selected
  active Space.
- A nullable same-Space Member may identify the primary Member associated with
  a Calendar record without creating a generalized attendee system.
- Calendar uses a configured IANA timezone and deterministic timezone-aware
  date, time, and recurrence handling.
- Fixed Calendar records distinguish commitments, events, and availability.
- All-day records use calendar dates rather than fabricated midnight UTC
  timestamps.
- Recurring records preserve local wall-clock meaning across timezone offset
  and daylight-saving changes.
- Initial recurrence remains deliberately narrow: deterministic daily and
  weekly routines, bounded intervals, optional weekday selection, and explicit
  occurrence exclusions.
- Recurring occurrences are derived for a bounded requested range rather than
  materialized indefinitely as duplicate persistent records.
- Work owns Work-to-Calendar relationships while Calendar owns the referenced
  Calendar records.
- Deleting owning Work removes its Work-to-Calendar relationships. Deleting a
  referenced Calendar record preserves relationship evidence rather than
  silently erasing historical context.
- Portable export format version 1 and operational-fact schema version 1 remain
  unchanged throughout v0.8.3.
- Backup and restore must recognize the additive Calendar schema and safely
  upgrade supported schema-v6 databases without mutating existing records.

Planned implementation scope:

- Selected-Space Calendar settings and configured IANA timezone
- Fixed events, commitments, and availability windows
- Optional all-day Calendar records
- Routines and recurring schedule records
- Deterministic recurrence expansion and occurrence exclusions
- Work-to-Calendar relationships
- Selected-Space Calendar frontend
- Backend-authoritative Calendar CRUD and occurrence APIs
- Additive SQLite schema-v7 migration and recovery compatibility
- Isolated disposable browser acceptance

Explicitly excluded:

- Capacity eligibility
- Automatic placement of optional Work
- Claims that optional Work fits available time
- Free-time or usable-hours inference
- Priority ranking
- Recommendation logic
- Morning Briefing decision logic
- Notifications
- External calendar synchronization
- Invitation, RSVP, or generalized attendee workflows
- Generalized scheduling optimization or resource booking

## v0.8.4 — Money

Status: Planned

Purpose:

Provide universal household and business financial records beneath the
permanent Money category.

Scope:

- Income and revenue
- Expenses
- Accounts or funding sources
- Budgets
- Obligations and recurring costs
- Transaction categorization
- Contextual household and business terminology
- Relationships to Spaces, Work, Resources, People, and Organizations

Money provides operational financial decision support and does not replace
complete accounting software.

## v0.8.5 — Library, Records & Search

Status: Planned

Purpose:

Create the permanent Library category for durable records, references, and
search without transferring ownership from other modules.

Scope:

- Notes
- Documents
- Manuals
- Receipts
- Photos
- Decisions
- Measurements
- CAD references
- Universal Search
- Relationships to Spaces and other entities

Other modules may reference Library records without duplicating or owning
their stored content.

## v0.8.6 — Today Workspace & Household Proving Ground

Status: Planned

Purpose:

Create the factual daily workspace and validate the universal architecture
through real household use.

Scope:

- Selected-Space factual aggregation
- Today’s Calendar commitments
- Due and overdue Work
- Active Projects
- Resource shortages
- Care alerts
- Money obligations
- Recent changes
- Relevant Library records
- Household proving with the owner and spouse
- Workflow corrections based on real daily use

Explicitly excluded:

- Capacity eligibility
- Claims that optional Work fits available time
- Priority ranking
- Recommended next actions
- Complete Morning Briefing narration
- Hidden or AI-generated priority logic

## v0.9.0 — Capacity Engine

Status: Planned

Purpose:

Determine realistic Work eligibility from authoritative operational facts and
real constraints.

Scope:

- Eligible Work
- Blocked Work
- Realistic fit within available time and constraints
- Explainable eligibility reason codes
- Calendar commitments used as constraints
- Resources, Money, workload, and other approved facts used as inputs
- Deterministic results without AI dependency

Capacity reads source facts but does not own or rewrite them.

## v0.9.1 — Priority Engine

Status: Planned

Purpose:

Rank only Work that Capacity has already determined is realistically eligible.

Scope:

- Explainable deterministic ranking
- Approved urgency, importance, dependency, and consequence inputs
- User-controlled overrides
- Stable ranking reasons
- No promotion of blocked or infeasible Work

Priority ranks eligible Work but does not rewrite authoritative source facts.

## v0.9.2 — Morning Briefing

Status: Planned

Purpose:

Present Capacity, Priority, commitments, alerts, explanations, and recommended
next actions through the primary daily experience.

Scope:

- Capacity results
- Priority results
- Calendar commitments
- Operational alerts
- Explainable recommended next actions
- Source and reason visibility
- Natural-language narration where appropriate
- Deterministic core operation without required AI

The Morning Briefing presents results but does not replace the authority of
the modules, Calendar, Capacity, or Priority.

## Cross-Cutting Architecture Boundaries

- Normal operational pages use one clearly selected active Space.
- Backend APIs enforce Space context; frontend filtering alone is insufficient.
- People and Organizations remain minimal universal foundations in v0.8.0.
- Person, Member, operational role, authentication, and authorization remain separate.
- Module registration under Settings is local configuration, not monetization.
- Modules communicate through stable relationships, APIs, services, and operational facts.
- Modules do not manipulate one another’s private tables or duplicate authority.
- Today presents authoritative current facts without performing Capacity or Priority behavior.
- Calendar may record commitments and availability before Capacity exists.
- Capacity precedes feasibility claims, optional-work placement, ranking, and recommendations.
- The backend remains authoritative throughout the v0.8 and v0.9 series.
- v0.7.5 isolated-browser, diagnostics, cleanup, and data-safety standards remain mandatory.

## Deployment and Commercial Boundaries

- HardHead remains local and LAN-only through v1.0.
- Secure remote access begins in v1.1 after authentication, authorization, and permissions.
- Gregg receives no persistent remote access before v1.1.
- AI remains optional and is never required for core operation.
- Subscription, billing, entitlement, managed-hosting, and public SaaS work remains deferred until after v3.0.

---

# Long-Term Trust Progression

v1.0 first delivers reliable, explainable decision support grounded in
authoritative records, deterministic facts, Capacity, and Priority.

## v1.5 — Observational Analytics Without Behavior Changes

The Foreman may observe and summarize historical patterns without silently
changing rules, priorities, or user behavior.

## v2.0 — User-Approved Adaptive Calibration

Any adaptive calibration must be explicit, reviewable, reversible, and
approved by the user.

## v3.0 — Optional AI Advisor

AI may optionally interpret and explain authoritative facts. It must not
become the factual authority or be required for core operation.

The Foreman must first become trustworthy before it becomes adaptive.

---

# Future Platform and Specialized Expansion

These exploratory ideas do not reorder:

- The approved v0.8.0 through v0.9.2 dependency sequence
- The Version 1.0 deterministic trust target
- The v1.5, v2.0, and v3.0 trust progression
- The LAN-only-through-v1.0 deployment boundary
- The post-v3.0 commercialization boundary

## Platform Options

- PostgreSQL as a later consideration after the Version 1.0 SQLite foundation
- Authentication identities and authorization as explicit future security work
- Secure remote access beginning in v1.1
- Mobile companion applications
- Cloud synchronization only when local-first operation and data ownership remain intact
- Notifications
- REST API expansion
- Stable plugin or module interfaces
- Intentional cross-Space administrative views

Members remain operational Space-participation records and must not be treated
as authentication identities.

Public SaaS tenancy, customer provisioning, billing, subscriptions, licensing,
and commercial entitlements remain deferred until after v3.0.

---

## Workshop Integration Options

- Barcode scanner
- QR labels
- RFID
- Supplier management
- Purchase orders
- Advanced reporting
- Equipment maintenance
- Machine runtime monitoring

---

## Optional Advanced Automation

- Artificial Intelligence
- Voice assistant
- Intelligent planning
- Predictive inventory
- Production forecasting
- Automated scheduling
- Natural language search

---

## Future

Possible long-term capabilities:

- Multiple workshop support
- Multiple business support
- Manufacturing workflows
- CNC automation
- Sensor integration
- ESP32 and Arduino integration
- Camera monitoring
- Robotics support

These ideas are exploratory and may evolve over time.

---

# Development Process

Every release follows the same workflow:

1. Design
2. Architecture review
3. Implementation
4. Testing
5. Documentation
6. Git commit
7. Git tag

Every completed release should leave The Foreman in a working state.

---

# Success Criteria

The Foreman succeeds when it:

- Saves time.
- Reduces mistakes.
- Improves organization.
- Supports real workshop workflows.
- Scales with HardHead Works.
- Remains simple to use.
- Remains enjoyable to maintain.

---

> **The Foreman serves the craftsman.**

Build steadily.

Build intentionally.

Build something that lasts.
