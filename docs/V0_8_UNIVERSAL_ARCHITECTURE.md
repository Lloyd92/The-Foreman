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

The Work category includes:

- Tasks
- Projects
- Requirements
- Dependencies
- Progress
- Responsibility
- Dates
- Relationships
- Shared lifecycle concepts

v0.8.1 owns the universal Work convergence.

## 7.1 Work Ownership

Work is an architectural ownership and integration domain. It is not a
universal persistence superclass.

v0.8.1 must preserve Tasks and Projects as distinct authoritative record types.
Their existing models, APIs, migration provenance, and native lifecycle
semantics remain authoritative.

Universal Work may provide shared relationships and normalized backend read
models derived from those records, but it must not introduce a competing
persistence authority or browser-side source of truth.

Existing `/api/tasks` and `/api/projects` mutation boundaries remain
compatible.

## 7.2 Lifecycle and Progress

Tasks retain their existing open/completed lifecycle.

Projects retain their existing planning, active, on-hold, completed, and
archived lifecycle.

Universal Work may normalize these states for common presentation without
rewriting the authoritative records.

Task progress may be represented deterministically as 0 percent while open and
100 percent when completed. Projects retain their explicit persisted progress.

## 7.3 Responsibility

Work responsibility may reference a nullable Member participating in the same
active Space as the Task or Project.

Existing records remain valid without an assigned Member. Migration must not
fabricate responsibility for historical records.

## 7.4 Work Dates and Calendar

Projects retain their existing start and target dates.

Tasks may gain a nullable due date.

A Work due or target date is a fact about the Work. It is not a Calendar
commitment, scheduled occurrence, reserved work period, or statement that
Capacity exists.

Calendar remains authoritative for commitments, events, routines, recurrence,
and availability.

## 7.5 Requirements

Existing Project material requirements remain the first concrete Work
requirement type.

Work owns the requirement relationship. Inventory remains authoritative for
the referenced Inventory record and stock state.

v0.8.1 must not create generalized requirement types for future modules merely
to anticipate later milestones.

## 7.6 Dependencies

Work dependencies are factual relationships between supported Work records.

Supported relationships may include:

- Task to Task
- Task to Project
- Project to Task
- Project to Project

Dependency services must enforce active-Space isolation and reject missing,
duplicate, self-referential, and cyclic relationships.

A dependency does not determine Capacity, feasibility, scheduling, Priority,
recommendations, or Morning Briefing behavior.

## 7.7 Universal Work Read Model

v0.8.1 may expose a backend-authoritative normalized Work read model derived
from the selected Space Tasks, Projects, and approved Work relationships.

The read model may normalize record type, stable ID, title or name, lifecycle
state, priority, progress, dates, responsibility, and Project relationships.

It remains derived state and does not replace the authoritative Task or Project
mutation APIs.

## 7.8 Compatibility

v0.8.1 must preserve:

- existing Task and Project APIs
- existing Task and Project records
- existing browser migration provenance
- Project material requirements
- Inventory to Project to Task migration ordering
- Task compatibility when related Projects are deleted
- backend-authoritative active-Space isolation
- module enable and disable behavior
- backup, restore, and portable export compatibility
- isolated disposable browser acceptance

New Work fields must be optional or migrated safely so existing records and
existing migration payloads remain valid.

Work may reference future Calendar routines or scheduled occurrences through
stable identifiers and relationships, but Work does not own routine
definitions.

---

# 8. Resources

Resources is a permanent navigation category and integration boundary. It is
not a universal persistence authority.

Resources contains separate systems for:

- Tools
- Inventory
- Care Plans

No v0.8.2 implementation may introduce a universal `resources`,
`resource_items`, or generalized polymorphic Resource persistence model merely
to make future modules appear uniform.

## 8.1 Tools

Tools owns durable equipment.

Tool authority includes:

- identity
- type or category
- condition
- location
- factual availability
- notes
- maintenance and service history

Tool maintenance history is factual completed history. It does not represent a
Calendar commitment, scheduled occurrence, Capacity result, or recommendation.

## 8.2 Inventory

Inventory remains the authoritative consumable-stock system.

Inventory owns:

- quantities
- units
- minimum thresholds
- locations
- cost
- supplier text
- notes
- usage and stock facts

Existing Inventory persistence, APIs, browser-migration compatibility,
Project material requirements, and missing-reference evidence must be
preserved.

Existing Inventory records must not be automatically converted into Tools.
Historical user classification is evidence and must not be rewritten without
an explicit reviewed migration decision.

## 8.3 Care Plans

Care Plans owns upkeep definitions for:

- service
- inspections
- cleaning
- property upkeep
- maintenance
- future husbandry care definitions

A Care Plan may exist independently for general or property upkeep and may
optionally reference a Tool.

Care may record factual upkeep requirements or frequency metadata. It does not
own Calendar recurrence, scheduled commitments, reminders, capacity-aware
placement, or recommendation behavior. Actual scheduled occurrences belong to
Calendar beginning in v0.8.3.

Care must not introduce a generalized polymorphic care-target system merely to
anticipate future modules.

## 8.4 Work and Tool Requirements

Work owns requirement relationships.

v0.8.2 may introduce a concrete Work-to-Tool requirement relationship for
Tasks and Projects. Tools remains authoritative for the referenced Tool and its
factual state.

Creation of a Work-to-Tool requirement must validate that both the Work record
and Tool exist in the same active Space.

Deleting a referenced Tool must not silently erase the Work requirement. The
requirement remains as missing-reference evidence until the user removes or
replaces it.

Deleting the owning Task or Project removes that Work record's Tool
requirements.

A Tool requirement does not determine scheduling feasibility, Capacity,
Priority, recommendations, or Morning Briefing behavior.

## 8.5 Module and Compatibility Boundary

Inventory, Tools, and Care remain separate module authorities beneath
Resources. Tools and Care do not require one another to be enabled.

The existing Mealworms workspace remains compatibility surface during v0.8.2.
It must not be silently deleted, renamed to Care, converted into Care Plans, or
used to invent broader husbandry architecture.

These systems may relate to one another but must not collapse into one
authority.

---

# 9. Money

Money uses universal concepts that can support household and business use.

v0.8.4 establishes these authoritative Money record types:

- Accounts or funding sources
- Financial categories
- Transactions representing factual income, revenue, and expenses
- Budgets representing user-defined plans or limits
- Obligations and recurring costs
- Explicit Money relationship evidence to approved records owned by Work,
  Resources, People, and Organizations

Every Money record is authoritative within one Space. Cross-domain
relationships use stable identifiers and must not duplicate or transfer
another module's authority. Relationship evidence may remain visible when a
referenced target disappears where the approved relationship contract requires
that history to be retained.

The interface may show household or business terminology contextually while
preserving one understandable architecture.

Money records financial facts and explicit user-entered financial plans. It
does not infer free funds, determine affordability, perform Capacity logic,
rank Work, recommend spending, forecast financial outcomes, perform AI
interpretation, or replace complete accounting software.

v0.8.4 advances SQLite schema version 7 to version 8 while preserving backup
format version 1, portable export format version 1, and operational-fact schema
version 1.

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

Calendar is authoritative for:

- Fixed commitments
- Events
- Explicit availability
- Routines and recurring schedule records
- Recurrence definitions and occurrence exclusions
- Timezone-aware Calendar dates and times

Ordinary Calendar records belong to one active Space. A Calendar record may
optionally reference one same-Space Member as its primary associated Member.
This does not create attendee, invitation, RSVP, account, or authentication
semantics.

The selected Space has a configured IANA timezone. Fixed timed records are
interpreted deterministically against that timezone. Recurring records preserve
their local wall-clock meaning across timezone-offset and daylight-saving
changes.

Initial v0.8.3 recurrence is intentionally constrained to deterministic daily
and weekly patterns, bounded intervals, optional weekday selection, and explicit
occurrence exclusions. The milestone must not introduce natural-language
recurrence parsing, arbitrary generalized rule engines, cron semantics, or
automatic schedule optimization merely to anticipate later needs.

Recurring occurrences are derived for bounded requested ranges. The derived
occurrence read model does not become a second persistence authority and does
not require indefinite materialization of occurrence rows.

Work may reference Calendar entries or recurring series through stable
relationships. Work owns those relationship records; Calendar continues to own
the referenced Calendar definitions. Deleting the owning Work removes its
relationship. A missing referenced Calendar record remains observable as
relationship evidence rather than being silently erased.

An availability record means only that the user explicitly recorded that time
as available. Calendar does not infer free time, subtract commitments, compute
usable hours, or claim optional Work fits.

This recordkeeping does not claim that optional Work is achievable.

Capacity must be evaluated before The Foreman:

- Places optional Work into available time
- Declares optional Work feasible
- Ranks eligible Work
- Recommends Work
- Presents capacity-aware scheduling decisions

Operational-fact schema version 1 and portable export format version 1 remain
unchanged throughout v0.8.3.
Backup and restore must preserve Calendar's authoritative SQLite records and
support the additive schema-v6 to schema-v7 transition safely.

This preserves the constitutional rule that Capacity takes precedence over
capacity-aware scheduling while allowing Calendar to record reality before the
Capacity Engine exists.

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

Every v0.8 milestone must preserve a Green Build.

At minimum:

- Existing backend tests pass.
- Existing frontend tests pass.
- New focused tests pass.
- Browser acceptance runs only against an isolated disposable deployment.
- Clean authoritative collections are verified where required without using live household data.
- Disposable project containers, networks, and images are removed.
- No persistent volume is deleted.
- Existing-data migration is tested from supported prior states.
- Backup, restore, and export compatibility are verified.
- Documentation matches implemented behavior.
- Current release metadata remains accurate.
- No later milestone behavior is presented as implemented.

---

# 21. Completion Boundary

v0.8.2 — Tools, Inventory & Care is complete.

The milestone established Resources as a category and integration boundary
while preserving Tools, Inventory, and Care Plans as separate authorities. It
added durable-equipment persistence, factual Tool maintenance history, Care
Plans, concrete Work-to-Tool requirements, Resources frontend convergence,
factual Overview data, and isolated compatibility acceptance without
introducing Calendar scheduling, Capacity, Priority, recommendation behavior,
generalized Resource persistence, or automatic Inventory-to-Tool migration.

The active milestone is:

**v0.8.3 — Calendar & Scheduling**

v0.8.3 owns commitments, events, routines, recurrence, and availability. It
must not claim that optional Work is feasible, automatically place optional
Work, rank Work, or recommend actions before Capacity and Priority exist.

Later milestones must preserve the v0.8.0 Space, module, data-ownership,
deployment, compatibility, and Green Build boundaries; the v0.8.1 Universal
Work ownership and lifecycle boundaries; and the v0.8.2 Resources, Tool,
Inventory, Care, and requirement-ownership boundaries unless an explicit
architecture change is reviewed and approved.
