# Issue Triage Guide

This document explains how Arnio maintainers triage incoming issues. It defines each label category, provides real-world examples, and outlines the standard triage workflow. Contributors are also welcome to read this to understand how their issues get categorized.

---

## Why Triage?

Every issue that lands in our backlog gets categorized along key dimensions:

1. **Priority** — how urgent it is
2. **Difficulty** — how much expertise it needs
3. **Size** — how much effort it'll take
4. **Status** — where it sits in the workflow
5. **Type** — what kind of change it is
6. **Area** — which part of the codebase it touches

This makes the backlog navigable: a beginner GSSoC contributor can filter for `difficulty: beginner` + `size: s` + `status: ready` and instantly find an entry point. Maintainers can spot `priority: critical` + `status: blocked` issues that need unblocking.

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
| `size: xs` | < 30 minutes | Single docstring, tiny fix, comment update |
| `size: s` | < 2 hours | Single function, doc fix, small test addition |
| `size: m` | Half a day | New pipeline step + tests, small refactor |
| `size: l` | 1–2 days | New module, multi-file feature, schema validation |

---

### Type

What kind of change is this?

| Label | Use for |
|:---|:---|
| `type: bug` | Fixing incorrect behavior |
| `type: feature` | Adding new capability |
| `type: docs` | Documentation only |
| `type: tests` | Test suite improvements |
| `type: refactor` | Code restructuring with no behavior change |
| `type: performance` | Speed or memory improvements |
| `type: security` | Security fix or hardening |
| `type: ci` | GitHub Actions, build pipeline, release tooling |
| `type: discussion` | Needs community input before implementation |

---

### Area

Which part of the codebase does this touch?

| Label | Covers |
|:---|:---|
| `area: csv-parser` | CSV reading, RFC 4180 compliance, BOM handling |
| `area: cpp-core` | C++ runtime — types, columns, frames, cleaning engine |
| `area: python-api` | Python API in `arnio/` — IO, pipeline, conversion |
| `area: pipeline` | Step registry, pipeline executor, custom steps |
| `area: cleaning` | Cleaning primitives — drop_nulls, fill_nulls, dedup, etc. |
| `area: pandas-interop` | pandas bridge, zero-copy conversion, buffer protocol |
| `area: quality` | Data quality engine, profiling, validation, suggestions |
| `area: schema` | Schema definition, type casting, validation |
| `area: docs` | README, architecture docs, guides, examples |
| `area: website` | arnio.vercel.app, landing page, tutorials |
| `area: ci-packaging` | GitHub Actions, PyPI wheels, releases |
| `area: benchmarks` | Performance testing, reproduction scripts |
| `area: examples` | Usage examples, notebooks, tutorials |
| `area: developer-experience` | Error messages, CLI tooling, dev setup |
| `area: release` | Version bumping, changelogs, deployment |

---

### Workflow Status

Where is the issue in the lifecycle?

| Label | Meaning |
|:---|:---|
| `status: needs triage` | New issue, not yet categorized or scoped |
| `status: ready` | Triaged, scoped, ready for a contributor to pick up |
| `status: claimed` | Assigned and being actively worked on |
| `status: blocked` | Cannot proceed — waiting on a decision, dependency, or upstream change |
| `status: needs maintainer` | Requires maintainer decision or code review |

---

### GSSoC Labels

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

- For bugs: try to reproduce locally. If the report lacks information, apply `status: needs triage` and ask for: OS, Python version, arnio version, minimal reproduction.
- For feature requests: confirm the proposed behavior fits the project scope. If unclear, apply `status: needs triage` and start a discussion.

### 2. Categorize

Apply labels from each required category:

- ✅ `priority: *` (required)
- ✅ `difficulty: *` (required)
- ✅ `size: *` (required)
- ✅ `status: *` (required — start with `status: needs triage`)
- ✅ `type: *` (required)
- ✅ `area: *` (one or more, required)
- 🟡 `gssoc: *` (only if appropriate for GSSoC contributors)

### 3. Scope the issue

A well-triaged issue includes:

- **Context** — why this matters
- **Suggested files** — pointers to where the work lives
- **Scope** — what's in and out of scope
- **Acceptance criteria** — checkboxes the contributor can tick off

If any of these are missing, keep the issue at `status: needs triage`.

### 4. Set status and assign

- Move to `status: ready` once the issue is fully scoped and ready for pickup
- Move to `status: claimed` when a contributor is assigned
- Move to `status: blocked` if external dependencies appear during work
- Use `status: needs maintainer` if you need another maintainer's input

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
| Type | `type: performance` | Performance improvement |
| Area | `area: cpp-core` | Lives in `cpp/src/cleaning.cpp` |
| GSSoC | `gssoc: level 3` | Advanced-tier scoring if a GSSoC contributor picks it up |

---

## Quick Reference for Maintainers

When in doubt, default to:

- **Priority** → `priority: medium`
- **Difficulty** → match the actual code complexity, not the issue description length
- **Size** → estimate as a maintainer would do it, not as a beginner would
- **Status** → start at `status: needs triage` if anything is unclear; promote to `status: ready` once scoped
- **Type** → `type: discussion` if direction is unclear

For consistency, every issue should reach `status: ready` before being advertised as a good first issue or GSSoC pickup.

---

## Questions?

- Open a [Discussion](https://github.com/im-anishraj/arnio/discussions) for triage process questions
- Tag `@im-anishraj` on the issue for category disputes
- See [CONTRIBUTING.md](CONTRIBUTING.md) for the contributor-side workflow