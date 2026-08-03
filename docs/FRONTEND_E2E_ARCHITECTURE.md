# v0.7.5 Frontend Hardening and Browser E2E Architecture

## Purpose

v0.7.5 establishes repeatable real-browser validation and hardens the
frontend boundaries around startup, migration, connection recovery, and
user-visible failures.

This milestone proves existing deterministic backend and frontend contracts
through a supported browser. It does not add new business-domain behavior.

## Approved Browser Path

The first automated browser target is Firefox through geckodriver.

The development tower already provides:

- Firefox
- geckodriver
- Headless execution for repeatable automated validation
- Visible execution for controlled human acceptance

Selenium may be added as a development-only Python dependency. Browser
automation dependencies must remain outside production backend and frontend
images.

Playwright, Puppeteer, Chromium, and downloaded browser bundles are outside
the initial v0.7.5 scope.

## Isolation and Data Safety

Automated mutating browser tests must never use the live household database or
the persistent `foreman-data` volume.

Every mutating E2E run must use:

- A disposable deployment identity
- A temporary SQLite database
- Loopback-only or isolated ports
- No access to the live `/data/foreman.db`
- No live Caddy state, certificates, trust material, or private keys
- Deterministic cleanup

The harness must fail closed when isolation cannot be proven.

Read-only smoke checks against a running development deployment may be
supported separately, but they must not create, edit, migrate, restore, or
delete business records.

## Harness Responsibilities

The browser harness must:

1. Start or connect to an explicitly approved isolated deployment.
2. Wait for backend and database health.
3. Launch Firefox with a fresh temporary profile.
4. Navigate to the approved application origin.
5. Execute deterministic visible workflows.
6. Assert UI state and backend-authoritative results.
7. Capture bounded diagnostic evidence on failure.
8. Close Firefox and clean disposable resources.

The project must provide one documented command for the complete E2E suite
and focused commands for individual workflows.

## Browser Acceptance Layers

### Clean Startup and Navigation

The browser suite must verify:

- The application shell loads
- Backend-authoritative startup completes
- System status reports the expected release
- Primary and utility routes are reachable
- Page routes remain unique
- No uncaught startup error prevents operation

### Backend-Authoritative CRUD

Representative browser workflows must cover:

- Inventory
- Projects and material requirements
- Tasks and Project compatibility

Tests must create and own their records. They must not depend on household
data or browser storage as runtime authority.

### Connection Loss and Safe Recovery

The suite must verify:

- Operations are blocked while HardHead or its database is unavailable
- Retry performs a real health probe
- Recovery after operational startup requires a deliberate reload
- Stale frontend state never silently resumes
- Dirty forms and open dialogs can block unsafe reload
- Reload resumes from backend-authoritative data

Failure simulation must not interrupt the live household deployment.

### Migration Reporting

Inventory, Project, and Task migration use one normalized frontend report
containing only bounded aggregate evidence:

- Module name and normalized severity
- Imported and previously confirmed counts
- Aggregate records requiring attention
- Retryable failure and warning counts
- One consistent browser-record retention statement

User-facing reports exclude raw errors, record identifiers, payloads,
validation details, paths, and backend response objects.

Migration reports remain diagnostic evidence only. They do not become a
second persistence authority or rewrite retained source records.

## Failure Diagnostics

Failed E2E workflows retain only bounded, allowlisted evidence:

- Redacted diagnostic-overlay screenshot
- Route-only local location with query values removed
- Document readiness and connection state
- Counts of visible pages, dialogs, and dirty forms
- Approved body-state flags
- Browser-console severity counts without messages
- Bounded geckodriver severity summary replacing the raw log
- Sanitized test identifier, failure type, and UTC timestamp

Diagnostics exclude page titles, visible application text, assertion values,
raw console messages, raw geckodriver content, page source, databases,
environment files, certificates, private keys, secrets, payloads, record
identifiers, and household records.

A controlled failing Firefox fixture proves safe capture, browser shutdown,
driver-log replacement, artifact inspection, and cleanup.

Successful runs remove temporary artifacts unless the explicit keep option is
enabled.

## Determinism

Tests must use bounded waits on observable state rather than arbitrary sleeps.

Preferred selectors are:

- Unique element IDs
- Stable `data-*` state attributes
- Accessible names and roles
- Visible status text when that text is part of the contract

Tests must avoid fragile styling selectors.

## Green Build

A v0.7.5 Green Build requires:

- Existing backend tests pass
- Existing frontend Node tests pass
- Browser-harness safety tests pass
- Approved Firefox workflows pass against a verified-empty isolated clean
  deployment
- Disposable project containers, networks, and images are verified absent
  after cleanup
- Failure diagnostics are proven with a controlled failing fixture
- No live data or private deployment material is attached
- Documentation matches the implemented commands

## Explicit Exclusions

v0.7.5 does not include:

- Morning Briefing, Capacity, or Priority behavior
- Authentication or external access
- Mobile Safari automation
- Cross-browser automation beyond Firefox
- Cloud CI infrastructure
- Scheduled backups
- Restore activation against live household data
- Legacy browser-storage retirement
- AI-generated diagnostics or autonomous repair

## Planned Commit Sequence

1. Define browser-E2E architecture and acceptance boundaries.
2. Add the isolated Firefox/WebDriver harness.
3. Add clean-deployment startup and navigation smoke coverage.
4. Add backend-authoritative browser CRUD workflows.
5. Add deterministic connection-loss and safe-recovery coverage.
6. Normalize migration reporting and improve diagnostics.
7. Complete isolated clean-deployment browser acceptance.
8. Finalize and release v0.7.5.
