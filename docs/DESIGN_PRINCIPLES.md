# The Foreman Design Principles

Version: 1.0

---

# Purpose

The Foreman is designed to help builders, makers, craftsmen, and small business owners organize their work without getting in the way of it.

Every design decision should make the software easier to understand, easier to maintain, and easier to use in a real workshop.

These principles guide every feature added to The Foreman.

---

# 1. Build for the Workshop First

The Foreman exists to solve real problems encountered inside HardHead Works.

Features should solve actual workshop problems before considering broader audiences.

If it works well in HardHead Works, it can later be generalized for everyone else.

---

# 2. Simplicity Over Complexity

The simplest solution that solves the problem is usually the correct one.

Avoid unnecessary complexity.

Avoid unnecessary dependencies.

Avoid unnecessary configuration.

---

# 3. Reliability Over Flashiness

The Foreman is a workshop tool.

Users should trust it more than admire it.

Fast.

Stable.

Predictable.

Professional.

Fancy animations and visual effects should never interfere with productivity.

---

# 4. Every Feature Must Have a Purpose

No feature should exist simply because it is technically interesting.

Every feature should answer one question:

"What real problem does this solve?"

If that question cannot be answered, the feature should not exist.

---

# 5. Modular Everything

Every system should be independent.

Tasks should not depend on Inventory.

Inventory should not depend on Budget.

Budget should not depend on Mealworms.

Modules communicate through well-defined interfaces.

This allows new systems to be added without rewriting existing ones.

---

# 6. Separation of Responsibilities

Each file should have a single responsibility.

Examples:

Pages render pages.

Storage stores data.

API communicates with the backend.

Router changes views.

Business logic belongs in modules—not inside HTML.

---

# 7. Human Readability Wins

Code is written for people first.

Future developers should understand the code without needing clever tricks.

Clear names.

Consistent formatting.

Meaningful comments.

Readable functions.

Maintainability is more valuable than saving a few lines of code.

---

# 8. Preserve User Data

User information should never be lost without deliberate migration.

Updates should preserve existing projects, inventory, budgets, and settings whenever possible.

Backward compatibility is preferred.

---

# 9. Automate Repetitive Work

Whenever users repeat the same task multiple times, ask:

"Can The Foreman do this automatically?"

Automation should reduce workload—not remove user control.

The Foreman assists the craftsman.

It does not replace the craftsman.

---

# 10. Performance Matters

The Foreman should feel responsive on modest hardware.

It is expected to run on older workshop computers like the HardHead server.

Optimize for responsiveness before optimization for scale.

---

# 11. Offline First

A workshop should continue operating without Internet access.

The Foreman should function locally whenever possible.

Cloud features are optional—not required.

---

# 12. Data Before Appearance

Good information is more important than beautiful graphics.

Users should immediately know:

• What needs attention
• What is low
• What is overdue
• What should be built next

The interface should communicate information clearly.

---

# 13. Consistency

Buttons should behave consistently.

Dialogs should behave consistently.

Navigation should behave consistently.

Keyboard shortcuts should behave consistently.

Users should never have to guess how something works.

---

# 14. Version Everything

Every meaningful change should be tracked.

Git commits.

Git tags.

Release notes.

Documentation.

Nothing important should exist only in memory.

---

# 15. Document Decisions

When architecture changes, update:

ARCHITECTURE.md

When functionality changes, update:

CHANGELOG.md

When future direction changes, update:

ROADMAP.md

Good documentation is part of the software.

---

# 16. AI is a Tool, Not the Product

AI assists development.

AI assists planning.

AI assists automation.

AI should never reduce the user's understanding or control of their own workshop.

The Foreman should always remain transparent in its decisions.

---

# 17. Grow With the Business

The Foreman should scale naturally.

A hobby workshop.

A small business.

A commercial shop.

Multiple buildings.

Multiple employees.

The architecture should support growth without requiring complete redesign.

---

# 18. Build Things That Last

Temporary shortcuts become permanent problems.

Choose solutions that future developers will appreciate.

Every release should leave the project in a better state than it was before.

---

# Final Principle

The Foreman serves the craftsman.

Software exists to help people build things.

It should remove friction.

It should increase confidence.

It should organize work.

It should never become the work itself.