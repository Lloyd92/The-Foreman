# v0.8 Universal Architecture

## Status

Approved architecture for The Foreman v0.8 series.

This document supersedes the earlier proposed
“v0.8 Capacity and Calendar Foundation” draft.

It defines the universal operating structure that must exist before Capacity,
Priority, and the Morning Briefing are implemented.

No v0.8 implementation may contradict this contract without explicit founder
approval.

---

# 1. Milestone Sequence

The approved dependency sequence is:

1. v0.8.0 — Universal Navigation & Spaces
2. v0.8.1 — Universal Work System
3. v0.8.2 — Tools, Inventory & Care
4. v0.8.3 — Calendar & Scheduling
5. v0.8.4 — Money
6. v0.8.5 — Library, Records & Search
7. v0.8.6 — Today Workspace & Household Proving Ground
8. v0.9.0 — Capacity Engine
9. v0.9.1 — Priority Engine
10. v0.9.2 — Morning Briefing

The intended operational progression is:

```text
Modules provide authoritative facts
        |
        v
Calendar records commitments and availability
        |
        v
Capacity determines realistic eligibility
        |
        v
Priority ranks eligible Work
        |
        v
Morning Briefing presents explainable recommendations
```

Later milestones must not be implemented early merely because their future
interfaces are visible.

---

# 2. Permanent Navigation

The permanent primary navigation is:

- Today
- Calendar
- Work
- Resources
- Money
- Library

Settings and Account remain separate below the primary navigation.

Modules are managed under Settings. Enabled modules contribute functionality
inside the six stable categories rather than adding top-level sidebar entries
by default.

This navigation contract remains stable while modules and capabilities grow
underneath it.

---

# 3. Spaces

Spaces provide the universal operational boundary for The Foreman.

Initial and planned Space contexts include:

- Personal
- Household
- Workshop
- HardHead Works

HardHead Works may be introduced when its operational needs justify a distinct
Space. v0.8.0 must not assume every installation requires a business Space.

## 3.1 One Active Space

Normal operational workflows begin with one clearly selected active Space.

In v0.8.0:

- Projects operate within the active Space.
- Tasks operate within the active Space.
- Inventory operates within the active Space.
- People and Organizations may be scoped or related to the active Space.
- Navigation preserves the selected active Space.
- Backend APIs enforce Space context authoritatively.
- Frontend filtering alone is never sufficient for Space isolation.

Ordinary pages must not silently combine records from multiple Spaces.

## 3.2 Intentional Cross-Space Behavior

Broad multi-Space aggregation is not part of normal v0.8.0 operation.

Intentional later exceptions may include:

- Today aggregating selected Spaces in v0.8.6
- Universal Search querying authorized Spaces in v0.8.5 or later
- Specialized administrative views
- Explicit transfer or relationship workflows

Cross-Space behavior must be visible, deliberate, and authorized by the
backend.

---

# 4. People

People represent real-world individuals.

The v0.8.0 Person foundation includes only:

- Stable identity
- Names
- Basic descriptive fields
- Space relationships
- Role or relationship classifications
- Basic CRUD
- Stable references for future records

People may later support household contacts, customers, contractors, service
providers, and similar roles through specialized modules.

v0.8.0 does not implement:

- CRM pipelines
- Leads
- Opportunities
- Sales processes
- Communication histories
- Customer lifecycle automation
- Marketing behavior

---

# 5. Organizations

Organizations represent real-world groups or institutions.

The v0.8.0 Organization foundation includes only:

- Stable identity
- Name
- Basic descriptive fields
- Space relationships
- Role classifications
- Basic CRUD
- Stable references for future records

Possible role classifications include:

- Supplier
- Employer
- Service provider
- Customer organization
- Utility
- School
- Financial institution

v0.8.0 does not implement:

- Supplier-management workflows
- Purchasing behavior
- Customer pipelines
- Sales processes
- Complex organization hierarchies
- Contract management
- Communication histories

Specialized behavior belongs in later optional modules.

---

# 6. Members, Authentication, and Authorization

A Person and a Member are not the same record.

The model must preserve separation between:

- Person — the real-world individual
- Member — that Person’s participation in a Space
- Role or responsibility — what the Member does operationally
- Authentication identity — future login and credential concern
- Authorization — future permission enforcement

Example:

```text
Person: Amber
Member of: Household Space
Role: Household administrator
Responsibilities: Shared household operations
Authentication identity: Not implemented
Authorization policy: Not implemented
```

v0.8.0 Members are operational participation records.

They are not:

- User accounts
- Password records
- Login credentials
- Authentication providers
- Security principals
- Complete permission systems

Secure authentication and authorization belong to later approved work.

---

# 7. Universal Work

The Work category eventually includes:

- Tasks
- Projects
- Requirements
- Dependencies
- Progress

Work may reference Calendar routines or scheduled occurrences through stable
identifiers and relationships, but it does not own routine definitions.

v0.8.1 owns the universal Work convergence.

v0.8.0 may establish relationships and navigation placeholders required for
that future work, but it must not prematurely implement the complete universal
Work model.

---

# 8. Resources

Resources contains separate systems for:

- Tools
- Inventory
- Care Plans

Tools owns durable equipment, including future condition, location,
availability, and maintenance history.

Inventory owns consumable stock, quantities, thresholds, locations, and usage.

Care Plans owns service, inspection, cleaning, property upkeep, maintenance,
and future husbandry care definitions.

These systems may relate to one another but must not collapse into one
authority.

---

# 9. Money

Money uses universal concepts that can support household and business use.

Later Money capabilities may include:

- Income
- Revenue
- Expenses
- Accounts or funding sources
- Budgets
- Obligations
- Recurring costs
- Transaction categorization

The interface may show household or business terminology contextually while
preserving one understandable architecture.

Money is operational financial decision support. It is not intended to replace
complete accounting software.

---

# 10. Library

Library eventually contains:

- Notes
- Documents
- Manuals
- Receipts
- Photos
- Decisions
- Measurements
- CAD references
- Search

Library owns stored records and document references.

Other modules may link to Library records without duplicating or taking
ownership of them.

---

# 11. Today and the Morning Briefing

Today and the Morning Briefing are different capabilities.

## 11.1 Today Workspace

v0.8.6 Today presents authoritative current information.

Today may show:

- Today’s calendar commitments
- Due and overdue Work
- Active Projects
- Resource shortages
- Care alerts
- Money obligations
- Recent changes
- Relevant Library records
- Selected-Space factual summaries

Today does not:

- Determine realistic eligibility
- Claim optional Work fits available time
- Rank eligible actions
- Recommend what should be done first
- Produce a complete Morning Briefing
- Use hidden or AI-generated priority logic

Today is a presentation surface. It is not authoritative storage.

## 11.2 Capacity Engine

v0.9.0 Capacity determines:

- What Work is eligible
- What Work is blocked
- What can realistically fit
- Which constraints prevent Work
- Explainable eligibility reason codes

Capacity reads approved source facts but does not own or rewrite them.

## 11.3 Priority Engine

v0.9.1 Priority determines:

- Which eligible Work deserves attention first
- Explainable deterministic ranking
- User-controlled overrides

Priority ranks eligible Work but does not rewrite source records.

## 11.4 Morning Briefing

v0.9.2 Morning Briefing presents:

- Capacity results
- Priority results
- Alerts
- Commitments
- Explanations
- Recommended next actions
- Natural-language narration where appropriate

The Morning Briefing remains the heart of The Foreman.

---

# 12. Calendar and Capacity

Calendar recordkeeping and capacity-aware scheduling are different concerns.

Calendar may record:

- Fixed commitments
- Events
- Routines
- Availability
- Recurrence rules
- Timezone-aware dates and times

This recordkeeping does not claim that optional Work is achievable.

Capacity must be evaluated before The Foreman:

- Places optional Work into available time
- Declares optional Work feasible
- Ranks eligible Work
- Recommends Work
- Presents capacity-aware scheduling decisions

This preserves the constitutional rule that Capacity takes precedence over
scheduling while allowing Calendar to record reality before the Capacity
Engine exists.

---

# 13. Module Registry

The module registry under Settings supports local product configuration.

Permitted concepts include:

- Module identifier
- Module name
- Description
- Enabled or disabled state
- Required dependencies
- Contribution locations
- Safe-enable rules
- Safe-disable rules
- Data-retention behavior when disabled
- Module health or compatibility state

Contribution locations are limited to Today, Calendar, Work, Resources,
Money, Library, and Settings where configuration is required.

Module enablement is configuration, not monetization.

The following concepts are prohibited before the approved post-v3.0
commercialization phase:

- Subscription plans
- Billing
- Paid tiers
- Licensing checks
- Commercial entitlements
- Payment-based feature restrictions
- Plan-based storage limits
- Account suspension
- SaaS tenants
- Customer provisioning

---

# 14. Data Ownership

The Foreman connects information without confusing ownership.

Authoritative ownership includes:

| System | Owns |
|---|---|
| Spaces | Operational context and Space identity |
| People | Real-world individual identity |
| Organizations | Real-world organization identity |
| Members | Participation within a Space |
| Work | Tasks, Projects, requirements, dependencies, and progress |
| Inventory | Consumable stock, quantities, thresholds, locations, and usage |
| Tools | Durable-equipment condition and availability |
| Care Plans | Service and upkeep definitions |
| Calendar | Fixed commitments, events, routines, recurrence, and availability |
| Money | Financial records |
| Library | Stored records and document references |
| Capacity | Eligibility calculations derived from approved facts |
| Priority | Ranking of eligible Work |
| Today | Presentation of current authoritative facts |
| Morning Briefing | Presentation of Capacity, Priority, alerts, and explanations |

Modules may communicate through:

- Stable identifiers
- Defined relationships
- Service contracts
- Backend APIs
- Operational facts

Modules must not:

- Directly manipulate another module’s private tables
- Duplicate authoritative data
- Maintain competing browser-side sources of truth
- Create circular ownership
- Require unrelated modules to initialize before functioning

---

# 15. Backend Authority

The backend remains authoritative.

Space isolation, record ownership, validation, and relationships must be
enforced by backend services and APIs.

The frontend may present and request state, but it must not become the final
authority for:

- Active-Space isolation
- Record ownership
- Cross-Space access
- Module enablement
- Operational facts
- Data migrations
- Security boundaries

Stale browser data remains migration, compatibility, evidence, or recovery
material only. It must not become normal runtime authority.

---

# 16. Existing-Data Migration

v0.8.0 must preserve existing Projects, Tasks, Inventory, Project materials,
migration provenance, backups, restores, and portable exports.

Existing operational records must be assigned to one approved deterministic
default Space.

The migration must be:

- Versioned
- Idempotent
- Atomic where required
- Testable
- Explainable
- Recoverable
- Compatible with backup and restore
- Free from record-text inference

The migration must not guess a Space from names, descriptions, notes, or other
free-form record content.

The exact default-Space rule must be approved before schema implementation.

---

# 17. v0.8.0 Scope

v0.8.0 establishes:

- Permanent navigation
- Spaces
- One active Space for ordinary workflows
- Minimal People
- Minimal Organizations
- Members as operational participation records
- Backend-authoritative Space context
- Module registration under Settings
- Existing-record migration into Space context
- Compatibility and browser acceptance

v0.8.0 does not implement:

- Complete universal Work behavior
- Complete Tools behavior
- Care Plans
- Calendar scheduling behavior
- Money behavior
- Library behavior
- Completed Today aggregation
- Capacity
- Priority
- Morning Briefing
- Authentication
- Authorization
- Remote access
- CRM
- Purchasing workflows
- Commercial entitlements
- Subscription infrastructure
- SaaS tenancy

---

# 18. Engineering Standards

All v0.8.0 work must preserve the hardening standards established in v0.7.5:

- The backend remains authoritative.
- Browser acceptance uses isolated disposable deployments.
- Mutating tests never touch live household data.
- Stable semantic selectors are required.
- Connection-loss behavior remains deliberate.
- Reload behavior does not bypass active safety dialogs.
- Stale browser state never becomes runtime authority.
- Diagnostics remain bounded and non-sensitive.
- Clean deployment is verified.
- Cleanup is deterministic.
- Persistent volumes remain protected.
- Backup compatibility remains intact.
- Restore compatibility remains intact.
- Export compatibility remains intact.
- Migration compatibility remains intact.

---

# 19. Deployment and Commercial Boundaries

HardHead remains local and LAN-only through v1.0.

Secure remote access begins in v1.1 only after external connectivity,
authentication, authorization, and permission boundaries are intentionally
implemented.

Gregg does not receive persistent remote access before v1.1.

Before v1.1, external evaluation may use:

- A separate local installation
- An exported demonstration build
- A guided walkthrough
- A recorded demonstration

Subscription features, billing, commercial entitlements, managed-hosting
plans, public SaaS infrastructure, and other commercialization systems remain
deferred until after v3.0.

---

# 20. Green Build Requirements

v0.8.0 work is not complete until it preserves a Green Build.

At minimum:

- Existing backend tests pass.
- Existing frontend tests pass.
- New focused tests pass.
- Browser acceptance runs only against an isolated disposable deployment.
- Clean Inventory, Project, and Task collections are verified where required.
- Disposable project containers, networks, and images are removed.
- No persistent volume is deleted.
- Existing-data migration is tested from supported prior states.
- Backup, restore, and export compatibility are verified.
- Documentation matches implemented behavior.
- Current release metadata remains accurate.
- No later milestone behavior is presented as implemented.

---

# 21. Approval Boundary

The approved next milestone is:

**v0.8.0 — Universal Navigation & Spaces**

The first approved change is documentation-only.

No schema, API, frontend, migration, Docker, deployment, or version changes may
begin until the v0.8.0 Commit 1 documentation contract is reviewed and
approved.
