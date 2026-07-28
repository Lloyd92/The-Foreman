# Contributing to The Foreman

Thank you for contributing to The Foreman.

Whether you are a developer, designer, tester, technical writer, or AI coding assistant, your goal is the same:

**Help build software that helps people build things.**

Before contributing, read these documents in order:

1. `docs/CONSTITUTION.md`
2. `docs/FOUNDERS_LETTER.md`
3. `docs/ENGINEERING_PRINCIPLES.md`
4. `docs/DESIGN_PRINCIPLES.md`
5. `ARCHITECTURE.md`
6. `docs/AGENTS.md`
7. `README.md`
8. `ROADMAP.md`
9. `CHANGELOG.md`
10. `docs/TASKS.md`
11. `CONTRIBUTING.md`

These documents define the project's purpose and engineering philosophy.

The Constitution is the highest authority. The Founder's Letter defines
project intent, Engineering Principles define development behavior, Design
Principles define the user experience, and Architecture defines the Version
1.0 target architecture.

When documentation and implementation disagree, do not assume the
implementation is correct. Determine whether the discrepancy represents
incomplete implementation, outdated documentation, or an architectural
decision requiring founder approval.

---

# Development Philosophy

The Foreman is developed intentionally.

Every feature should solve a real workshop problem.

Quality is more important than speed.

Maintainability is more important than cleverness.

The project should remain understandable years after it is written.

---

# Workflow

Every feature follows the same process.

## 1. Design

Understand the problem before writing code.

Questions to answer:

- What problem is being solved?
- Who benefits?
- Does this already exist elsewhere?
- Can the solution be simpler?

---

## 2. Architecture Review

Before implementing a feature:

- Review existing modules.
- Avoid duplicate functionality.
- Keep responsibilities separated.
- Identify whether the change affects the current implementation, the Version
  1.0 target architecture, or both.
- Confirm that the Dashboard remains the application shell and the Morning
  Briefing remains its default workspace.
- Confirm that capacity is evaluated before scheduling or recommendation.

Follow the architecture described in `ARCHITECTURE.md`.

Architecture describes the Version 1.0 target and may not match every part of
the current implementation. Do not treat an implementation difference as an
implicit architecture change.

---

## 3. Implementation

Implement the smallest complete solution.

Do not add unrelated improvements in the same change.

Keep commits focused.

---

## 4. Testing

Every feature should be tested before being committed.

Verify:

- Existing functionality still works.
- New functionality behaves correctly.
- No console errors.
- No unnecessary warnings.

---

## 5. Documentation

If functionality changes:

Update:

- CHANGELOG.md
- ROADMAP.md (if applicable)
- ARCHITECTURE.md (if architecture changes)

Documentation is considered part of the feature.

---

## 6. Version Control

After testing and with project-owner approval:

```bash
git add .
git commit -m "Meaningful description"

git tag
```

Every release should have:

- A commit
- A Git tag
- Updated documentation

Contributors and AI assistants must not commit, tag, merge, or push unless the
project owner explicitly instructs them to do so.

---

# Coding Standards

## General

Prefer readability.

Prefer consistency.

Prefer maintainability.

Avoid unnecessary complexity.

---

## File Responsibilities

Each module should have one responsibility.

Examples:

```
pages/
    Render application pages

utils/
    Shared application logic

storage/
    Data persistence

api/
    Backend communication
```

Avoid mixing responsibilities.

---

## Function Design

Functions should:

- Do one thing.
- Have descriptive names.
- Be reasonably short.
- Avoid side effects whenever practical.

---

## Naming

Use descriptive names.

Good:

```
renderInventory()

saveInventoryItems()

initializeDashboard()
```

Avoid:

```
run()

test()

data()

tmp()
```

---

## Comments

Comments should explain **why**, not **what**.

Bad:

```javascript
// Increment i

i++;
```

Good:

```javascript
// Skip archived projects because they are displayed separately.
```

---

# User Interface Guidelines

The interface should be:

- Fast
- Clean
- Professional
- Predictable

Avoid unnecessary animation.

Avoid visual clutter.

Information should be immediately understandable.

---

# AI Contributors

AI coding assistants (including Codex) are expected to:

- Read project documentation before coding.
- Preserve existing architecture.
- Avoid unnecessary dependencies.
- Never remove working functionality without justification.
- Produce maintainable code.
- Explain significant architectural changes.
- Update documentation when behavior changes.

AI should not automatically:

- Commit changes.
- Create Git tags.
- Rewrite large portions of the application without approval.

---

# Pull Requests (Future)

Each pull request should include:

- Purpose
- Summary
- Screenshots (if UI changes)
- Testing performed
- Documentation updates

---

# Bug Reports

A good bug report includes:

- Expected behavior
- Actual behavior
- Steps to reproduce
- Browser
- Operating system
- Console output (if available)

---

# Feature Requests

Feature requests should answer:

- What problem does this solve?
- Who benefits?
- Is there a simpler solution?
- Does it fit the project vision?

Ideas that are not immediately planned should be added to:

```
docs/FUTURE_IDEAS.md
```

---

# The Foreman Constitution

These principles apply to every contribution.

## 1.

Every feature solves a real problem.

---

## 2.

Build for HardHead Works first.

Generalize later.

---

## 3.

Maintainability is more valuable than cleverness.

---

## 4.

Never sacrifice stability for speed.

---

## 5.

One responsibility per module.

---

## 6.

Every meaningful release receives:

- Documentation
- Commit
- Git tag

---

## 7.

Protect user data.

Never introduce unnecessary risk of data loss.

---

## 8.

Document important decisions.

Future developers should understand why choices were made.

---

## 9.

Automate repetitive work.

Technology should remove friction.

---

## 10.

The Foreman serves the craftsman.

Software exists to support meaningful work—not distract from it.

---

# Final Thought

Every contribution should leave the project better than it was found.

Whether the improvement is one line of code or an entire subsystem, strive to make the next developer's job easier.

Build carefully.

Build intentionally.

Build something worth maintaining.
