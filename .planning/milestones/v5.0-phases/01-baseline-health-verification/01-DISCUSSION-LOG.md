# Phase 1: Baseline Health Verification - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-08-16
**Phase:** 1-Baseline Health Verification
**Areas discussed:** Failure policy, Evidence format, Tool pinning, Gate scope

---

## Failure Policy

| Option | Description | Selected |
|--------|-------------|----------|
| Fix in-phase | Fix whatever breaks until all gates green | ✓ |
| Triage split | Fix trivial breaks; defer real defects to a backlog | |
| Record only | Run gates and record pass/fail; defer all fixes | |

**User's choice:** Fix in-phase.

| Option | Description | Selected |
|--------|-------------|----------|
| Frozen files hard-stop | Fix anything except models.py/evidence.py; escalate if required | ✓ |
| Minimal-diff anywhere | Fix wherever needed, including frozen files | |
| Tests/config only | Limit fixes to tests, lint config, manifests | |

**User's choice:** Frozen files hard-stop.

| Option | Description | Selected |
|--------|-------------|----------|
| Judge each case | Fix code or test based on which asserts intended behavior | ✓ |
| Code only | Never edit a failing test | |
| Escalate all test edits | Any test change needs user sign-off | |

**User's choice:** Judge each case; rationale recorded per fix commit.

| Option | Description | Selected |
|--------|-------------|----------|
| Per governance | Each fix commit bumps patch as normal | ✓ |
| Batch fixes | One commit, one patch bump | |

**User's choice:** Per governance.

---

## Evidence Format

| Option | Description | Selected |
|--------|-------------|----------|
| VERIFICATION.md only | Standard GSD artifact holds all gate evidence | ✓ |
| Receipt-style report | Committed report with full transcripts | |
| Commit messages only | Evidence in fix-commit bodies | |

**User's choice:** VERIFICATION.md only.

| Option | Description | Selected |
|--------|-------------|----------|
| Command + exit + tail | Exact command, exit code, decisive summary lines | ✓ |
| Full transcripts | Complete stdout/stderr per gate | |
| Pass/fail table only | One row per gate, no output quoted | |

**User's choice:** Command + exit + tail.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, version block | Record each tool's version at run time | ✓ |
| No | Skip versions | |

**User's choice:** Yes, version block.

| Option | Description | Selected |
|--------|-------------|----------|
| Yes, fix ledger | Table: gate, failure, fix summary, commit SHA | ✓ |
| No, commits suffice | Git history records fixes | |

**User's choice:** Yes, fix ledger.

---

## Tool Pinning

| Option | Description | Selected |
|--------|-------------|----------|
| Use installed, record | Run installed versions; version block dates the baseline | ✓ |
| Pin in pyproject | Add version pins before running gates | |
| Pin ty only | Pin only the highest-churn tool | |

**User's choice:** Use installed, record.

| Option | Description | Selected |
|--------|-------------|----------|
| uv run in helpers dir | `uv run pytest` from the helpers directory | ✓ |
| System pytest | Run pytest from PATH | |
| You decide | Planner picks from pyproject.toml contents | |

**User's choice:** uv run in helpers dir.

| Option | Description | Selected |
|--------|-------------|----------|
| Record only | Record interpreter version; floor decision stays with Phase 3 | ✓ |
| Declare floor now | Set requires-python in this phase | |

**User's choice:** Record only.

---

## Gate Scope

| Option | Description | Selected |
|--------|-------------|----------|
| prek run --all-files | Whole-repo hook run, matches VAL-03 wording | ✓ |
| Staged only | Hooks on staged changes only | |

**User's choice:** prek run --all-files.

| Option | Description | Selected |
|--------|-------------|----------|
| Helpers package | ruff/ty on plugins/sec-overlay/skills/sec-overlay/helpers only | ✓ |
| All repo python | Lint and type-check every .py in the repo | |

**User's choice:** Helpers package.

| Option | Description | Selected |
|--------|-------------|----------|
| Justified ignores OK | Zero unaddressed warnings; justified inline ignores count as clean | ✓ |
| Zero ignores | Remove every suppression | |
| Ignores audited | Ignores allowed but counted in VERIFICATION.md | |

**User's choice:** Justified ignores OK.

| Option | Description | Selected |
|--------|-------------|----------|
| Root + per-plugin | Validate at repo root and inside plugins/sec-overlay | ✓ |
| Root only | Single validate at repo root | |

**User's choice:** Root + per-plugin.

---

## Claude's Discretion

- Order of gate execution.
- Structure of fix commits within governance rules.

## Deferred Ideas

None.
