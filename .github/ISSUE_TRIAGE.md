# Issue Triage Guide

This document explains how Arnio maintainers triage incoming issues. It defines each label category, provides real-world examples, and outlines the standard triage workflow. Contributors are also welcome to read this to understand how their issues get categorized.

---

## Why Triage?

Every issue that lands in our backlog gets categorized along four dimensions:

1. **Priority** — how urgent it is
2. **Difficulty** — how much expertise it needs
3. **Size** — how much effort it'll take
4. **Status** — where it sits in the workflow

Plus optional tags for `area`, `type`, and `gssoc` participation.

This makes the backlog navigable: a beginner GSSoC contributor can filter for `difficulty: beginner` + `size: s` + `status: ready` and instantly find an entry point. Maintainers can spot `priority: high` + `status: blocked` issues that need unblocking.

---

## Label Categories

### Priority

How urgent is this issue?

| Label | Meaning | Example |
|:---|:---|:---|
| `priority: critical` | Production-breaking bug, security issue, or release blocker. Drop everything. | A regression that crashes `read_csv()` on valid input |
| `priority: high` | Important and time-sensitive. Should be picked up this week. | A documented public API returns wrong results for common case |
| `priority: medium` | Solid improvement, not urgent. Pick up this milestone. | Add new pipeline step or improve an existing one |
| `priority: low` | Nice-to-have. May sit in backlog for a while. | Tweak terminology in an internal log message |

---

### Difficulty

How much expertise does this need?

| Label | Meaning | Who should pick it up |
|:---|:---|:---|
| `difficulty: beginner` | Self-contained, well-scoped, no prior repo context required. Touching one or two files. | First-time contributors, students new to open source |
| `difficulty: intermediate` | Requires reading existing code, following established patterns, writing tests. | Contributors comfortable with Python and the codebase |
| `difficulty: advanced` | Architecture-level work, C++ optimization, performance-critical paths. | Contributors with C++ experience or deep familiarity |

---

### Size

How much effort will this take?

| Label | Estimate | Typical scope |
|:---|:---|:---|
| `size: s` | < 2 hours | Single function, doc fix, small test addition |
| `size: m` | Half a day | New pipeline step + tests, small refactor |
| `size: l` | 1–2 days | New module, multi-file feature, schema validation |
| `size: xl` | Multi-day | Parallel column processing, streaming reader, major engine work |

---

### Status

Where is the issue in the workflow?

| Label | Meaning |
|:---|:---|
| `status: ready` | Triaged, scoped, ready for a contributor to pick up |
| `status: in-progress` | Assigned and being actively worked on |
| `status: blocked` | Cannot proceed — waiting on a decision, dependency, or upstream change |
| `status: needs-info` | Reporter needs to clarify or provide reproduction steps |
| `status: needs-design` | Direction unclear — needs discussion in a thread or RFC before code |

---

### Area

Which part of the codebase does this touch?

| Label | Covers |
|:---|:---|
| `area: cpp` | C++ runtime in `cpp/` — types, columns, frames, cleaning engine |
| `area: bindings` | pybind11 bridge in `bindings/` |
| `area: python` | Python API in `arnio/` — IO, pipeline, conversion |
| `area: docs` | README, architecture docs, guides, examples |
| `area: ci` | GitHub Actions, build pipeline, release tooling |
| `area: tests` | Test suite, fixtures, benchmarks |

---

### Type

What kind of change is this?

| Label | Use for |
|:---|:---|
| `type: feat` | Adding new capability |
| `type: fix` | Correcting incorrect behavior |
| `type: docs` | Documentation only |
| `type: chore` | Tooling, CI, refactors with no behavior change |
| `type: perf` | Performance improvement |

These map directly to Conventional Commit prefixes used in PR titles.

---

### GSSoC

For [GSSoC 2026](https://gssoc.girlscript.tech/) participants:

| Label | Meaning |
|:---|:---|
| `gssoc` | Issue is eligible for GSSoC contribution credit |
| `gssoc: good first issue` | Strongly recommended starting point for new GSSoC contributors |
| `gssoc: level 1` | Beginner-tier scoring |
| `gssoc: level 2` | Intermediate-tier scoring |
| `gssoc: level 3` | Advanced-tier scoring |

See [GSSOC_GUIDE.md](../GSSOC_GUIDE.md) for full scoring details.

---

## Triage Workflow

When a new issue arrives, work through these steps in order:

### 1. Read and reproduce

- For bugs: try to reproduce locally. If the report lacks information, apply `status: needs-info` and ask for: OS, Python version, arnio version, minimal reproduction.
- For feature requests: confirm the proposed behavior fits the project scope. If unclear, apply `status: needs-design` and start a discussion.

### 2. Categorize

Apply exactly one label from each required category:

- ✅ `priority: *` (required)
- ✅ `difficulty: *` (required)
- ✅ `size: *` (required)
- ✅ `status: *` (required)
- ✅ `type: *` (required)
- ✅ `area: *` (one or more, required)
- 🟡 `gssoc: *` (only if appropriate for GSSoC contributors)
- 🟡 `good first issue` / `help wanted` (visibility tags)

### 3. Scope the issue

A well-triaged issue includes:

- **Context** — why this matters
- **Suggested files** — pointers to where the work lives
- **Scope** — what's in and out of scope
- **Acceptance criteria** — checkboxes the contributor can tick off

If any of these are missing, add them before marking `status: ready`.

### 4. Set status

- Move to `status: ready` once the issue is fully scoped and unassigned
- Move to `status: in-progress` when a contributor is assigned
- Move to `status: blocked` if external dependencies appear during work

---

## Worked Example

**Incoming issue title:** "drop_duplicates is slow on large datasets"

**Triage decision:**

| Label | Value | Reasoning |
|:---|:---|:---|
| Priority | `priority: high` | Performance is a roadmap focus for v1.2 |
| Difficulty | `difficulty: advanced` | Requires C++ work in the cleaning engine |
| Size | `size: l` | Hash-based comparison replacement is multi-file |
| Status | `status: ready` | Reproducible, well-scoped, fix path is clear |
| Type | `type: perf` | Performance improvement |
| Area | `area: cpp` | Lives in `cpp/src/cleaning.cpp` |
| GSSoC | `gssoc: level 3` | Advanced-tier scoring if a GSSoC contributor picks it up |

---

## Quick Reference for Maintainers

When in doubt, default to:

- **Priority** → `medium`
- **Difficulty** → match the actual code complexity, not the issue description length
- **Size** → estimate as a maintainer would do it, not as a beginner would
- **Status** → start at `needs-info` if anything is unclear; promote to `ready` once scoped

For consistency, every issue should reach `status: ready` before being publicly advertised as a good first issue or GSSoC pickup.

---

## Questions?

- Open a [Discussion](https://github.com/im-anishraj/arnio/discussions) for triage process questions
- Tag `@im-anishraj` on the issue for category disputes
- See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for the contributor-side workflow