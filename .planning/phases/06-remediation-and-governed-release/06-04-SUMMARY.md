---
phase: 06-remediation-and-governed-release
plan: 04
subsystem: sec-overlay test suite
tags: [tdd-detection-proof, frozen-contract, profile-gating, rel-03, e-12]
dependency-graph:
  requires: [06-03]
  provides: [rel-03-closed, e-12-closed-at-unit-level]
  affects: [plugins/sec-overlay/skills/sec-overlay/helpers/tests]
tech-stack:
  added: []
  patterns: [sha256 byte-identity guard, golden-value pinning, tomllib packaging-table assertion, detection-proof-instead-of-red-green]
key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_frozen_contract.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_profiles.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/.claude-plugin/plugin.json
    - plugins/sec-overlay/CHANGELOG.md
decisions:
  - "Boundary category for E-12's boundary probe: `injection` (a real member of `GENERAL_DEFECT_CLASSES` in `review_findings.py`), attached to a `gate=None` finding. `gate is None` is the only route by which `apply_profile` ever keeps a finding under the `security` profile — there is no broader or narrower route, so this is 'the narrowest possible margin' the plan asks for. Picking a `cls` that also happens to be in `GENERAL_DEFECT_CLASSES` proves the subset relation holds even for a finding that looks classification-eligible: `gate is None` short-circuits the `or` in `apply_profile` before `classify()` is ever consulted, so the general profile's bypass path is never reached for it either — both profiles keep it via the same unconditional rule."
  - "REL-03 assertion uses stdlib `tomllib` directly against the real `pyproject.toml` (no fallback needed) — confirmed available under the pinned interpreter."
  - "Both commits landed on `test/frozen-contract-and-profile-subset-guards` (forked from `docs/milestone-v5-diff-review`, per D-14/D-16), each `test` type, each a patch bump (1.69.8 -> 1.69.9 -> 1.69.10)."
actuals:
  tokens: 42000
  tasks: 2
  commits: 2
metrics:
  duration: "~2.5h across two sessions (compaction boundary)"
  completed: 2026-08-21
status: complete
---

# Phase 6 Plan 04: Frozen-contract and profile-subset guards Summary

Installed a sha256 byte-identity + `fingerprint()` golden-value tripwire for the frozen `models.py`/`evidence.py` contract, a REL-03 test that reads the real `pyproject.toml` to assert zero runtime dependencies, and four `apply_profile()` edge probes (vacuous, single-element, boundary, permutation) that turn Phase 5's E-12 vacuous-subset observation into a non-vacuous, unit-level guarantee — five detection proofs run and quoted below, none committed.

## What was built

**Task 1 (D-15, REL-03):** `tests/test_frozen_contract.py` (new file, 6 tests):
- Two sha256 byte-identity guards pinning `models.py` and `evidence.py` against committed digests, with an actionable failure message naming the Go-port mirror requirement and the sign-off/update procedure.
- Three `fingerprint()` golden-value tests reaching the same pinned 12-hex value (`b90035da86f7` = `sha256("R100|sqli|my_func")[:12]`) from a fully-populated `Finding`, a minimally-populated one (every optional field at its dataclass default), and one built with the same required fields passed in reverse keyword order — proving the digest depends only on `rule_id`/`cls`/`anchor`, independent of every other field and of construction order.
- `test_helpers_declare_zero_runtime_dependencies` reads `[project] dependencies` out of the real `helpers/pyproject.toml` via stdlib `tomllib` and asserts it equals `[]`, closing **REL-03** with a running check.

**Task 2 (D-08, E-12):** four new tests appended to `tests/test_review_profiles.py`:
- `test_apply_profile_vacuous_subset_is_distinguishable_from_a_real_pass` — asserts the subset relation over two empty runs, AND separately asserts both sides were in fact empty.
- `test_apply_profile_subset_holds_at_a_single_kept_finding` — exercises the same relation at size one.
- `test_apply_profile_narrowest_margin_boundary_finding_is_kept_by_both` — the boundary probe (rationale above).
- `test_apply_profile_kept_set_is_stable_under_input_permutation` — reruns `_dual_run_fixture()` and its reverse through both profiles, comparing kept sets by `finding.id`.

All four reuse `_dual_run_fixture()` unmodified (via direct call, slice, or empty-list literal) — no second fixture, no change to its signature, no new function/class/module added to `helpers/sec_overlay/` (`git diff --stat` for that directory is empty for this plan).

## Detection proofs (5 total, all reverted before staging)

**Task 1 — Guard 1, byte-identity (`models.py`):** appended a trailing comment line, ran `test_models_byte_identity_pinned_to_go_port_mirror`:
```
E       AssertionError: sec_overlay/models.py's sha256 changed — this file is a frozen, byte-identical mirror of a separate Go port (D-15) and must never be edited on its own. If this edit is intentional: apply the identical change to the Go port by hand, get sign-off, then update _MODELS_SHA256 in this test to the new digest (got 09081a2434ed65de74ce5e1710d5bb06d036a2973e5aef813e10ab5913e07a11).
```
Reverted with `git checkout --`.

**Task 1 — Guard 2, fingerprint golden value:** changed `rule_id="R100"` to `rule_id="R999"` in the minimally-populated case, ran `test_fingerprint_golden_value_minimally_populated`:
```
E       AssertionError: assert '663ab8c29135' == 'b90035da86f7'
```
Reverted with the Edit tool (file had no other pending changes at that point).

**Task 1 — Guard 3, REL-03:** changed `helpers/pyproject.toml`'s `dependencies = []` to `dependencies = ["placeholder"]`, ran `test_helpers_declare_zero_runtime_dependencies`:
```
E       AssertionError: assert ['placeholder'] == []
```
Reverted with `git checkout --`. Running `uv run pytest` under the perturbed `pyproject.toml` also rewrote `uv.lock`; that stray lockfile diff was caught (`git status --short`) and reverted with a second `git checkout --` before staging anything.

**Task 2 — Proof 1, profile-table perturbation:** in `review_findings.py`, flipped `bypassed = profile == "general" and ...` to `profile == "security" and ...` (security now bypasses instead of general), ran `test_review_profiles.py`. The subset probe failed as the direct consequence:
```
E       AssertionError: assert False
E        +  where False = <built-in method issubset of set object at 0x1109ef760>({'F-1'})
E        +    where <built-in method issubset of set object at 0x1109ef760> = {'F-1', 'F-2', 'F-4'}.issubset
```
(from `test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`; 9 tests failed in total from this one-line perturbation, confirming the subset relation is load-bearing across the suite, not just the new probes). Reverted with the Edit tool.

**Task 2 — Proof 2, shrink-to-empty (the E-12 point):** temporarily changed `test_dual_run_general_profile_is_a_strict_superset_of_the_security_baseline`'s two `_dual_run_fixture()` calls to `[]`. Result: the subset assertion (`security_ids.issubset(general_ids)`) passed silently (∅ ⊆ ∅), while the companion non-vacuity assertion failed:
```
E       AssertionError: general profile must add at least one finding over security
E       assert set()
```
This is the direct, reproduced demonstration of the exact defect E-12 flagged in Phase 5: a subset check alone cannot distinguish "held" from "had nothing to hold". Reverted with the Edit tool.

## REL-03 status

**REL-03 is now asserted by a test**, not a one-time manual read: `test_helpers_declare_zero_runtime_dependencies` reads the live `pyproject.toml` at test time via stdlib `tomllib` on every suite run. Plan 05's ledger should cite this test rather than re-deriving the claim.

## E-12 status

E-12 (`05-DEFECTS.md` row 5) was filed against a **live agent-dispatched review run** that only ever produced an empty-versus-empty comparison — a fully non-vacuous re-verification would require a real reviewer dispatch against a diff range with live findings, which is out of scope for a test-only plan. This plan closes the underlying contract concern at the **unit level**: `apply_profile()` itself is now exercised at the empty, single-element, boundary, and permuted cases, with the empty case explicitly required to be non-vacuous-or-fail via a `git checkout --`-reverted regression demonstration (Proof 2 above). The live-run re-verification E-12 originally asked for remains open as a separate, larger-scoped item if the team wants a real agent-dispatched receipt in addition to this unit-level guarantee.

## Deviations from Plan

### Auto-fixed / incidental

**1. [Rule 1 - accuracy] `tests/README.md` test-count staleness.** The header line still read "1177 tests" as of Task 1 in an earlier compaction boundary, then "1280 tests" after Task 1; corrected again to "1284 tests" after Task 2's four additions, and a new narrative paragraph added for each task's guards, matching the file's established documentation convention. No test count for this repository has ever needed to be estimated — each was read directly off the actual `pytest` collection count.

**2. [Environmental, out of scope] Nested disconnected git repository under `helpers/`.** `plugins/sec-overlay/skills/sec-overlay/helpers/` contains its own independent `.git` directory (branch `main`, commits `46b59db`/`240b4f0`, no remote), completely unrelated to the outer marketplace repository's history. This is invisible to the outer repo's `git status` — git treats a directory containing `.git` as a gitlink/embedded-repo boundary and does not descend into it. **Hazard:** any `git` command run with a working directory inside `helpers/` (including via a chained `cd ... &&` in one Bash call, since shell cwd resets between separate Bash tool calls but persists within one chained command) operates on the wrong, nested repo — this was reproduced twice during this session (once via a stray `git status` inside a `cd`-chained command that silently returned nothing instead of erroring, once during the prior compacted session's earlier detection-proof reverts). No corruption occurred in either case — verified by comparing file contents/digests to the outer repo's actual `HEAD` after each incident, both matching exactly. **Mitigation applied going forward:** every git command in this plan's second half was run from the outer repo root explicitly, confirmed via `git rev-parse --show-toplevel` before staging or committing. This nested repo is a pre-existing environmental anomaly, not something this plan's scope covers fixing or removing (Scope Boundary rule) — flagged here for whoever next works in that directory.
**3. [Environmental, out of scope, unrelated file] `test_cli.py:778` ruff `I001` (unsorted import block)** and **`test_bench.py::test_seed_corpus_is_valid`** (gitignored bench corpus absent, 0 positives found) both fail/warn on a clean run of the full suite. Neither file was touched by this plan (`git status --short` confirms only the five files this plan modifies were ever staged); both are documented as pre-existing/environmental in `skills/sec-overlay/CLAUDE.md` §1. Left untouched per Scope Boundary.

None of the above required a Rule 4 (architectural) decision.

## CodeRabbit / PR status

Both commits (`5743d3a`, `cdfbe49`) shipped via PR #26 (`test/frozen-contract-and-profile-subset-guards` -> `docs/milestone-v5-diff-review`, merge commit `498597a`), pushed and merged by the orchestrator since `gh`/`git push` are blocked inside this executor agent. A courtesy `@coderabbitai review` was posted; per this phase's standing waiver (auto-review disabled on non-main bases, manual trigger rate-limited — established across PRs #23-#25), the merge did not wait on a walkthrough. The head branch is deleted, both remotely and locally (no local branch existed after the post-merge checkout).

## Self-Check: PASSED

- FOUND: `plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_frozen_contract.py`
- FOUND: commit `5743d3a` (Task 1)
- FOUND: commit `cdfbe49` (Task 2)
- FOUND: this file, `.planning/phases/06-remediation-and-governed-release/06-04-SUMMARY.md`
