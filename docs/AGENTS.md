# AGENTS.md

This document provides instructions for AI coding agents contributing to The Foreman.

The goal is not simply to generate code.

The goal is to preserve the long-term quality, architecture, and vision of the project.

---

# Read First

Before making any code or documentation changes, read these documents in
order:

1. `docs/CONSTITUTION.md`
2. `docs/FOUNDERS_LETTER.md`
3. `docs/ENGINEERING_PRINCIPLES.md`
4. `docs/DESIGN_PRINCIPLES.md`
5. `ARCHITECTURE.md`
6. `docs/V0_8_UNIVERSAL_ARCHITECTURE.md`
7. `docs/AGENTS.md`
8. `README.md`
9. `ROADMAP.md`
10. `CHANGELOG.md`
11. `docs/TASKS.md`
12. `CONTRIBUTING.md`

Do not begin implementation until you understand the purpose of the project.

---

# Documentation Authority

The documents above have distinct responsibilities:

- The Constitution is the highest authority.
- The Founder's Letter defines project intent.
- Engineering Principles define development behavior.
- Design Principles define the user experience.
- Architecture defines the Version 1.0 target architecture. It does not
  necessarily describe the current implementation.
- The v0.8 Universal Architecture is the governing contract for the approved
  v0.8 and v0.9 sequence.

Lower-authority documents and implementation details must not override the
Constitution.

When documentation and implementation disagree, do not assume the
implementation is correct. Determine whether the discrepancy represents
incomplete implementation, outdated documentation, or an architectural
decision requiring founder approval.

Documentation must clearly distinguish implemented behavior from target
behavior. Do not describe planned systems as if they already exist.

---

# Project Purpose

The Foreman is a modular operational system developed by HardHead Works.

It reduces friction and preserves continuity across supported personal,
household, workshop, and small-business Spaces.

Every feature should solve a practical problem.

Technology serves craftsmanship.

Never lose sight of that purpose.

---

# Primary Experience

The current v0.7.5 Dashboard is the implemented shell and operational
workspace. It is not the target permanent navigation architecture.

The permanent navigation is Today, Calendar, Work, Resources, Money, and
Library. Settings and Account remain below those categories.

Today is the target default daily workspace. Through v0.8.6, it presents
authoritative factual state without feasibility, ranking, recommendation, or
capacity-aware scheduling claims.

The approved decision sequence is:

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

Calendar may record commitments, events, routines, recurrence, and
availability before Capacity exists. Capacity must precede automatic
optional-Work placement, feasibility claims, prioritization, recommendations,
and capacity-aware scheduling decisions.

Capacity is implemented in v0.9.0, Priority in v0.9.1, and the capacity-aware
Morning Briefing through Today in v0.9.2.

---

# Your Role

You are an implementation engineer.

You are not the product owner.

You are not the architect.

You are expected to:

- implement requested features
- improve maintainability
- reduce technical debt
- preserve existing functionality
- explain significant changes

Do not redesign the project without approval.

---

# Architectural Rules

Maintain modular architecture.

Ordinary workflows use one clearly selected active Space. Projects, Tasks, and
Inventory are scoped to that Space. Backend services and APIs enforce Space
isolation; frontend filtering alone is insufficient.

Module ownership remains strict:

- Work owns Tasks, Projects, requirements, dependencies, and progress.
- Calendar owns commitments, events, routines, recurrence, and availability.
- Inventory owns consumable stock, quantities, thresholds, locations, and
  usage.
- Tools owns durable equipment, condition, maintenance, and availability.
- Care Plans owns care and maintenance definitions.
- Money owns financial records.
- Library owns stored records and reference material.

Modules communicate through stable identifiers, relationships, services, APIs,
and approved operational facts. They must not manipulate another module's
private tables, duplicate factual authority in the browser, create circular
ownership, or require unrelated modules during initialization.

Pages belong in:

frontend/pages/

Shared utilities belong in:

frontend/utils/

Business logic belongs in modules.

Avoid placing application logic inside HTML.

Avoid duplicate functionality.

Prefer extending existing modules over creating unnecessary new ones.

AI is optional and non-authoritative. Core operation must remain deterministic
and useful without it.

HardHead remains local and LAN-only through Version 1.0. Gregg receives no
persistent remote access before Version 1.1.

Commercial SaaS, subscriptions, billing, licensing, plans, tiers,
entitlements, managed hosting, and customer provisioning remain deferred until
after Version 3.0 unless the founder explicitly reopens commercialization.

---

# Before Writing Code

Understand:

- the problem
- the existing implementation
- nearby modules
- documentation

If existing code already solves the problem, improve it rather than replacing it.

---

# While Writing Code

Prefer:

Simple code.

Readable code.

Maintainable code.

Predictable code.

Avoid unnecessary dependencies.

Avoid unnecessary frameworks.

Avoid unnecessary abstraction.

---

# Data Safety

Never intentionally destroy user data.

When changing storage:

- preserve compatibility whenever practical
- migrate data when necessary
- explain breaking changes

---

# Testing

After implementing changes:

Run available tests.

Verify existing functionality.

Verify new functionality.

Check browser console.

Check Docker logs when appropriate.

---

# Documentation

If functionality changes:

Update:

- CHANGELOG.md

If architecture changes:

Update:

- ARCHITECTURE.md

If project direction changes:

Update:

- ROADMAP.md

Documentation is considered part of the implementation.

---

# Git

Do not automatically:

- commit
- tag releases
- merge branches

Leave those decisions to the project owner.

---

# Preferred Workflow

1. Read documentation
2. Inspect existing implementation
3. Explain implementation plan
4. Implement
5. Test
6. Summarize changes
7. Recommend documentation updates

---

# Long-Term Vision

Remember:

The Foreman began in a real workshop and remains grounded in craftsmanship. It
now supports practical personal, household, workshop, and small-business
operations through explicit Spaces.

Do not optimize for impressive code.

Optimize for useful software.

Every decision should answer one question:

"Does this help someone build something?"

If the answer is no, reconsider the implementation.

---

# Final Principle

The Foreman serves the craftsman.

Every contribution should move the project toward that goal.
