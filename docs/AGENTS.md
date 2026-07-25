# AGENTS.md

This document provides instructions for AI coding agents contributing to The Foreman.

The goal is not simply to generate code.

The goal is to preserve the long-term quality, architecture, and vision of the project.

---

# Read First

Before making any code changes, read these documents in order:

1. README.md
2. ROADMAP.md
3. ARCHITECTURE.md
4. CONTRIBUTING.md
5. docs/FOUNDERS_LETTER.md
6. docs/PROJECT_VISION.md
7. docs/DESIGN_PRINCIPLES.md

Do not begin implementation until you understand the purpose of the project.

---

# Project Purpose

The Foreman is a modular workshop operating system developed for HardHead Works.

It exists to reduce friction inside real workshops.

Every feature should solve a practical problem.

Technology serves craftsmanship.

Never lose sight of that purpose.

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

Pages belong in:

frontend/pages/

Shared utilities belong in:

frontend/utils/

Business logic belongs in modules.

Avoid placing application logic inside HTML.

Avoid duplicate functionality.

Prefer extending existing modules over creating unnecessary new ones.

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

The Foreman is being built to operate a real workshop.

Do not optimize for impressive code.

Optimize for useful software.

Every decision should answer one question:

"Does this help someone build something?"

If the answer is no, reconsider the implementation.

---

# Final Principle

The Foreman serves the craftsman.

Every contribution should move the project toward that goal.# The Foreman

The digital operations center for HardHead Works.

## Vision

The Foreman will manage:

- Inventory
- Tool tracking
- Material tracking
- CNC projects
- Mealworm production
- Customer jobs
- Budgeting
- Scheduling
- AI assistance

Built by HardHead Works.
