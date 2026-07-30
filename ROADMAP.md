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

### v0.7.3 — Unified Operational Facts

Status: In Progress

Purpose:

Create one backend-authoritative, deterministic fact layer for Projects,
material readiness, Tasks, and Inventory so different pages cannot
independently produce contradictory interpretations.

Approved architecture:

- Compute facts on demand from backend-authoritative SQLite records.
- Read all source records from one explicit transaction snapshot.
- Do not persist facts or change database schema version 2.
- Keep `GET /api/operational-facts` as the fact endpoint.
- Add `schemaVersion: 1`, normalized `facts`, and `summary` to the response.
- Temporarily preserve existing top-level response fields for compatibility.
- Keep fact IDs, types, states, reason codes, evidence, source references, and
  ordering deterministic so identical inputs produce identical fact output.
- Never use browser records as fact inputs or runtime fallback authority.

Initial fact vocabulary and states:

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
- Dashboard and Projects must consume the same backend readiness fact.
- Inventory must stop using frontend numeric fallback classification.

This milestone prepares trustworthy inputs for the future Morning Briefing. It
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

### v0.7.4 — Backup, Export, Restore, and Verification

Status: Planned

Objectives:

- Add manual backup and export
- Add restore with explicit verification
- Preserve migration evidence and authoritative SQLite data
- Establish recoverable data-safety workflows

### v0.7.5 — Frontend Hardening and Browser E2E

Status: Planned

Objectives:

- Establish repeatable browser end-to-end testing
- Harden frontend failure and recovery behavior
- Improve migration reporting and diagnostics
- Verify supported browser workflows from clean deployments

Deferred Project work:

- Estimated completion
- Project templates
- Expanded Task-to-Project editing and display
- Legacy Project storage retirement
- Archive cleanup
- Purchasing, reservations, and allocations

These items remain outside v0.7.1 and must be scheduled explicitly.

---

# Later Module Releases

Mealworm Management follows the v0.7 Core Convergence sequence rather than
serving as the immediate v0.7 milestone. Its release number will be assigned
when the foundation milestones are complete.

## Mealworm Management

Objectives:

- Colony management
- Rack visualization
- Feeding schedules
- Harvest planning
- Production reporting

Future integrations:

- Inventory
- Budget
- Sales

---

## Budget

Objectives

- Business budget
- Expense tracking
- Revenue tracking
- Material costing
- Profit estimation

Future integrations

- Inventory
- Projects
- Purchasing

---

## Settings

Objectives

- User preferences
- Workshop configuration
- Backup options
- Data import/export
- Appearance
- Module management

---

## v1.0 — Initial Stable Release

Goals

Deliver a reliable workshop operating system suitable for daily use.

Constitutional foundations:

- The Dashboard is the application shell.
- The Morning Briefing is the Dashboard's default workspace.
- Capacity evaluation occurs before scheduling or recommendation.
- Priority ranks work only after Capacity determines realistic eligibility.
- Recommendations are explainable.
- Core operation remains useful without Artificial Intelligence.

Core modules:

- Dashboard
- Tasks
- Inventory
- Projects
- Budget
- Mealworms

Additional goals:

- Documentation complete
- Stable API
- Tested release
- Installation guide
- SQLite database
- Backup and restore
- Release notes

Visible user interface alone does not make a feature complete when required
behavior is missing. Completion requires implemented behavior, verification,
and current documentation.

---

# Long-Term Vision

## Version 2

Potential additions:

- PostgreSQL database as a later consideration after the Version 1.0 SQLite
  foundation
- User accounts
- Multi-user support
- Mobile companion app
- Cloud synchronization
- Notifications
- REST API expansion
- Plugin architecture

---

## Version 3

Potential additions:

- Barcode scanner
- QR labels
- RFID
- Supplier management
- Purchase orders
- Advanced reporting
- Equipment maintenance
- Machine runtime monitoring

---

## Version 4

Potential additions:

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
