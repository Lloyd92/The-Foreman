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

# Active Release

## v0.6 — Projects 🚧

Status: In Progress

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

Pending

Objectives

- Material requirements
- Estimated completion
- Project templates

The visible Projects workspace does not make the Projects module complete.
Required project-management behavior remains pending until it is implemented
and verified.

Future integrations

- Inventory
- Budget
- CNC
- Purchasing

---

# Planned Releases

## v0.7 — Mealworm Management

Objectives

- Colony management
- Rack visualization
- Feeding schedules
- Harvest planning
- Production reporting

Future integrations

- Inventory
- Budget
- Sales

---

## v0.8 — Budget

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

## v0.9 — Settings

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
