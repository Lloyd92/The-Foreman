# Design Principles
## The Foreman
### Version 1.0

---

# Introduction

The Foreman is not designed to impress.

It is designed to help.

Every design decision should reduce unnecessary mental effort and increase confidence.

Good design should feel natural.

The user should spend their time accomplishing work—not learning how to use the software.

The best interface is the one that quietly disappears.

---

# Principle 1
## Calm Over Chaos

The Foreman should create a feeling of control.

It should never overwhelm its user with unnecessary information.

When multiple pieces of information compete for attention, prioritize only what is immediately useful.

The interface should reduce stress rather than increase it.

---

# Principle 2
## Today Establishes the Daily Experience

The target permanent navigation is Today, Calendar, Work, Resources, Money,
and Library. Settings and Account remain below those categories.

Today is the target default daily workspace. Through v0.8.6, it presents
authoritative factual current state without making feasibility, ranking,
recommendation, or capacity-aware scheduling claims.

After the v0.9 Capacity and Priority sequence is complete, the v0.9.2 Morning
Briefing becomes the capacity-aware primary daily experience presented through
Today.

Calendar may display and manage commitments, events, routines, recurrence, and
availability before Capacity exists. Those records do not imply that optional
Work is feasible.

Capacity is required before automatic optional-Work placement, feasibility
claims, prioritization, recommendations, and capacity-aware scheduling
decisions.

When deciding whether a feature belongs in Version 1.0 ask:

> Does this preserve clarity, continuity, or meaningful progress?

If not...

It probably belongs somewhere else.

---

# Principle 3
## Information Should Have Purpose

Every screen should answer a question.

Permanent-category examples:

Today

> What is factually true today?

Calendar

> What commitments and availability are recorded?

Work

> What Tasks and Projects require attention?

Resources

> What Inventory and Tools are available?

Money

> What financial obligations and records matter?

Library

> What notes, documents, and stored records do I need?

If a page exists without answering an important question, reconsider its purpose.

---

# Principle 4
## Reduce Cognitive Load

Never make the user remember something the software can remember.

Never require unnecessary clicks.

Never force users to search for important information.

The Foreman should remember details so its user can focus on thinking.

---

# Principle 5
## Progressive Complexity

Show only what is needed now.

Advanced information should remain available...

But not immediately visible.

Beginners should feel comfortable.

Power users should never feel limited.

---

# Principle 6
## Consistency Creates Confidence

Buttons should behave consistently.

Navigation should remain predictable.

Colors should retain their meaning.

Terminology should remain consistent throughout the application.

The user should never wonder what something does.

---

# Principle 7
## Explain Before Asking for Trust

Recommendations should include reasoning whenever practical.

Instead of:

> Buy more plywood.

Prefer:

> Current inventory supports one remaining project.
> Two future projects require additional plywood.

Users should understand recommendations.

Trust grows through explanation.

---

# Principle 8
## One Screen. One Purpose.

Avoid combining unrelated functions.

Each screen should focus on solving one primary problem.

Simple screens reduce decision fatigue.

Work owns Tasks, Projects, requirements, dependencies, and progress. Calendar
owns commitments, events, routines, recurrence, and availability. Inventory
owns consumable stock, quantities, thresholds, locations, and usage. Tools
owns durable equipment, condition, maintenance, and availability. Care Plans
owns care and maintenance definitions. Money owns financial records. Library
owns stored records and reference material.

Backend services and APIs enforce record ownership and active-Space isolation.
Frontend filtering must not become a security boundary or competing factual
authority. Modules communicate through stable identifiers and approved
relationships rather than manipulating another module's private tables.

---

# Principle 9
## Respect Attention

Notifications should exist only when they provide value.

Interruptions should be meaningful.

The Foreman should never compete for attention.

It should quietly wait until it has something important to say.

---

# Principle 10
## Build for Daily Use

Every feature should assume the application will be opened every day.

Frequently used actions should require minimal effort.

The software should become part of a daily routine.

---

# Principle 11
## Mobile Is an Extension

The phone application is not a smaller desktop.

It is a companion.

Mobile should emphasize:

- Morning Briefing
- Quick capture
- Inventory lookup
- Notifications
- Project status

Detailed planning belongs on larger screens.

---

# Principle 12
## Steam Deck Is a Workshop Companion

The Steam Deck should function as a portable Foreman terminal.

Its interface should prioritize:

- Large touch targets
- Quick navigation
- Inventory
- Checklists
- Project progress
- Shop reference information

It should remain fully usable while standing in the workshop.

---

# Principle 13
## The Workspace Should Feel Familiar

Preferred design language:

- Rounded corners
- Comfortable spacing
- Gunmetal gray
- Black
- Orange highlights

Avoid visual clutter.

Avoid excessive gradients.

Avoid unnecessary animation.

The interface should feel industrial, modern, and dependable.

---

# Principle 14
## Silence Has Value

The Foreman should never rely on sound.

Notifications should be visual.

Animations should remain subtle.

Silence helps users maintain focus.

---

# Principle 15
## Build Confidence

Every interaction should leave the user feeling more organized than before they opened the application.

The Foreman succeeds when users close it with greater confidence than when they opened it.

---

# Accessibility

Design should prioritize:

- Readable typography
- High contrast
- Keyboard accessibility
- Touch-friendly controls
- Responsive layouts
- Clear spacing

The interface should remain usable by everyone.

---

# Every Screen Should Answer

Every screen should clearly answer one important question.

Every click should move work forward.

Every recommendation should reduce uncertainty.

Every feature should strengthen the person using it.

---

# Final Thought

The Foreman should never feel like software that demands attention.

It should feel like a dependable partner standing quietly beside its owner.

Calm.

Organized.

Prepared.

Always ready to answer the same question:

> Given everything I know...

> What is the best thing to do next?

If the design accomplishes that...

Then it has succeeded.

Keep the work moving.
