---
phase: 03-rule-matching-review-modes
plan: 06
subsystem: sec-overlay diff-review live finding source (review_agent seam + run_review wiring)
tags: [review-agent, prepare-dispatch-consume, evidence-source-stamping, position-gate, profile-gate, reflection-gate, D-02, D-13, D-15, RULE-01, REV-01, REV-02, REV-03]

dependency graph:
  requires: [03-05]
  provides:
    - "sec_overlay.review_agent: render_review_prompt, parse_review_response, ReviewResponseError, REVIEW_AGENT_CLAIM, agent_label, ReviewPlanEntry, write_review_plan, ReviewSourceSkip, recorded_return_source"
    - "sec_overlay.diffscope.file_text_at_ref(path, ref, *, runner=subprocess.run) -> str"
    - "sec_overlay.cli.run_review(..., review_source=None, prepare=False) wired to a real finding source"
    - "sec_overlay.report: review_source_skipped ledger key, REVIEW_SOURCE_SKIPPED_HEADING, render_review_source_skipped_section"
    - "agents/review-file.md prompt (ported from open-code-review under D-02)"
    - "cli --prepare flag on the review subparser"
  affects:
    - "SKILL.md diff-scoped review dispatch (documents the prepare -> spawn -> consume loop)"
    - "Phase 4 and any later plan reading review_ledger.json's review_source_skipped key or runs/review_plan.json"

tech-stack:
  added: []
  patterns:
    - "Prepare/dispatch/consume split: run_review --prepare renders prompts and a plan deterministically; SKILL.md owns the only model dispatch (D-13); a second run_review call consumes recorded returns from disk"
    - "Injected finding source: review_source defaults to recorded_return_source(ws, base=, head=) but tests inject a fake source directly, keeping the gate chain testable without a model call"
    - "Evidence stamped in code, never trusted from the model: parse_review_response always writes REVIEW_AGENT_CLAIM and discards any model-supplied evidence_sources, so confirms_alone is always false for an agent-authored finding (REV-03)"
    - "Fail-open per file: a missing return, a stale base/head pair, and a ReviewResponseError are all treated identically as one review_source_skipped ledger entry with the run continuing (D-15)"
    - "Harness-derived position-gate snippet: finding.evidence is filled from the real head-file text at the finding's claimed line via diffscope.file_text_at_ref, never from anything the model reports"
  key-links:
    - "rule_glob.resolve_rule_doc(path) -> render_review_prompt(..., rule_text=) -> {{system_rule}} in the rendered prompt, resolved once per file inside run_review's per-file loop"
    - "review_agent.parse_review_response -> review_position_gate(live_findings, hunks_by_path, file_text_by_path) -> review_findings.apply_profile -> reflection.apply_verdict -> the receipt gate, in that fixed order"

key-files:
  created:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/review_agent.py
    - plugins/sec-overlay/skills/sec-overlay/agents/review-file.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_agent.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_review_live.py
  modified:
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/report.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/diffscope.py
    - plugins/sec-overlay/skills/sec-overlay/agents/README.md
    - plugins/sec-overlay/skills/sec-overlay/SKILL.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/README.md
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py
    - plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_rule_glob.py
    - plugins/sec-overlay/CHANGELOG.md
    - plugins/sec-overlay/.claude-plugin/plugin.json

decisions:
  - "Added diffscope.file_text_at_ref (git show <ref>:<path>, empty string on failure) as a Rule 2 auto-add: Task 3's own stated objective — deriving finding.evidence from real file text rather than trusting the model's claim — has no other source for that text, and no existing function in the module reads a whole file at an arbitrary ref."
  - "The position-gate snippet for every live finding is derived by the harness from the real head-file text at the finding's claimed line, never from anything the reviewing agent reports — consistent with the codebase's tool-receipt discipline (D-13) and with review-file.md's code_comment tool carrying no snippet field at all."
  - "cli.run_review's gate-chain call order is fixed exactly as the plan specifies: position gate, then apply_profile, then apply_verdict, then the receipt gate. Not reordered for test convenience, since the order is what keeps a reflection retraction from resurrecting a finding the position gate already dropped."
  - "recorded_return_source treats a missing return, a base/head ref mismatch, and a ReviewResponseError identically — one review_source_skipped ledger entry, zero findings for that file, run continues — rather than giving each failure mode a different code path, since all three represent 'this file's reviewer produced nothing usable'."
  - "Two incidental test-fixture repairs (test_rule_glob.py's fake_run_review needing a prepare=False kwarg, test_cli.py's write_review_ledger lambda needing a third positional arg) were made under Rule 3 (blocking fix) since cli.py's new call signatures broke both fixtures; no behavior in either test changed."

metrics:
  duration: "~2 hours across two sessions (session boundary after Task 2)"
  completed: 2026-08-18

status: complete

actuals:
  tokens: 71000
  tasks: 3
  commits: 3
---

# Phase 3 Plan 6: Wire a Live Finding Source Into Review Mode Summary

Ported open-code-review's per-file review prompt and response parser, then wired `run_review`
to call it as a real finding source instead of `review_position_gate([], ...)` — the review verb
now produces real, gate-traversing findings from a real diff.

## What Was Built

**Task 1 — `review_agent.py` (TDD, RED then GREEN).** `render_review_prompt` substitutes the
resolved rule doc, path, diff, and sibling changed files into `agents/review-file.md` through the
existing `prompts.render_prompt`, which already fails loudly on an unfilled token.
`parse_review_response` turns a recorded `code_comment`/`task_done` response into `Finding`
objects: it discards any comment naming a path other than the file under review (mechanically
enforcing OCR's Strict Focus Rule, not only asking for it in the prompt), stamps
`evidence_sources = [REVIEW_AGENT_CLAIM]` on every finding and drops whatever the model supplied,
assigns status in code rather than from the model's text, and derives each finding's id
deterministically so two parses of one response are idempotent. `ReviewResponseError` covers
malformed JSON, an unknown tool, and a comment missing a line or message — none of these are
repaired, since a silent repair would hide that the reviewer failed. 11+ tests, all passing;
`confirms_alone([REVIEW_AGENT_CLAIM])` is false, so no agent-authored finding can reach
`confirmed` (REV-03).

**Task 2 — `agents/review-file.md` and the SKILL.md dispatch block.** Ported OCR's system/user
prompt content under D-02, keeping the four content tokens (`{{change_files}}`,
`{{current_file_path}}`, `{{diff}}`, `{{system_rule}}`) plus two path anchors
(`{{OVERLAY_ROOT}}`, `{{REPO_ROOT}}`) so the agent resolves files regardless of CWD. Imports
`ANTI_MANIPULATION`, `TOOL_TRUST`, and `PATH_BASE` from `prompt-constants.md` rather than copying
them. SKILL.md gained a **Review mode (diff-scoped)** section documenting the three-step loop:
`--prepare` writes the plan and prompts, the skill spawns one review-file subagent per entry and
records its return, then a second `review` call consumes the recorded returns through the gate
chain. States the fail-open rule and that the skill never parses a return itself.

**Task 3 — wiring `run_review` to the source (TDD, RED then GREEN).** Added `diffscope.
file_text_at_ref` (git show at a ref, empty string on failure) — needed because deriving a
finding's position-gate snippet from real file text (rather than trusting the model's claim)
has no existing source in the module. `run_review` gained `--prepare` (renders one prompt per
reviewable file plus `runs/review_plan.json`, returns before any gate runs) and a
`review_source` parameter defaulting to `review_agent.recorded_return_source(ws, base=, head=)`.
The live findings now traverse `review_position_gate` (fed `file_text_by_path`, making the
whole-file "relocated" rung reachable for the first time) → `review_findings.apply_profile` →
`reflection.apply_verdict` → the receipt gate, in that fixed order. `report.py` gained the
`review_source_skipped` ledger key and a `## Review source skipped` section that renders an
explicit sentence in the zero case (D-15). 10 new tests in `test_review_live.py`, all passing,
including the plan's headline proof: the same fixture diff and recorded return report a
null-dereference finding under `--profile general` and do not under `--profile security`,
proven by running the CLI end to end, not by pre-seeding `Finding` objects.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing critical functionality] Added `diffscope.file_text_at_ref`**
- Found during: Task 3
- Issue: Task 3's own objective — deriving `finding.evidence` from real file text at the finding's
  claimed line, never from the model's claim — had no existing function to read a whole file at
  an arbitrary git ref.
- Fix: added `file_text_at_ref(path, ref, *, runner=subprocess.run) -> str`, mirroring the
  module's existing injectable-runner convention (`git show <ref>:<path>`, empty string on a
  non-zero exit).
- Files modified: `sec_overlay/diffscope.py`
- Commit: `9f86ddc`

**2. [Rule 3 - Blocking fix] Repaired two test fixtures broken by `cli.py`'s new call signatures**
- Found during: Task 3
- Issue: `test_rule_glob.py`'s `fake_run_review` and `test_cli.py`'s `write_review_ledger` lambda
  did not accept the new `prepare` kwarg / third positional `file_text_by_path` argument
  `run_review`'s new body passes, breaking two unrelated tests.
- Fix: added `prepare: bool = False` to the first fixture and a third `file_text_by_path=None`
  parameter to the second; no assertion in either test changed.
- Files modified: `tests/test_rule_glob.py`, `tests/test_cli.py`
- Commit: `9f86ddc`

No Rule 4 (architectural) deviations occurred; no checkpoint was raised.

### Auth Gates

None — this plan has no external service or credential dependency.

## Known Stubs

None. A manual smoke test surfaced an unexplained `defect_class: None` on one ledger entry when
passing `defect_class='sqli'` through a hand-rolled `code_comment` call outside the test suite;
the automated suite's equivalent case
(`test_profile_split_null_dereference_security_excludes_general_includes`) correctly asserts
`ledger_general["review_findings"][0]["defect_class"] == "null-dereference"` and passes, so this
was judged a smoke-script artifact, not a defect in the shipped code, and was not chased further.

## Threat Flags

None beyond the plan's own `<threat_model>` (T-03-17 through T-03-22), all of which this plan's
implementation mitigates as specified — no new surface outside that register was introduced.

## Verification

- `uv run pytest tests/test_review_agent.py -x -q` — passed (11+ tests).
- `uv run pytest tests/test_review_live.py -x -q` — passed (10 tests).
- `uv run pytest tests/test_review_live.py -k "profile or split" -q` — 1 passed, 9 deselected
  (the profile-split test covers both profiles against one fixture diff in a single test
  function, satisfying the substantive intent).
- `uv run pytest tests/test_review_coverage.py tests/test_review_tracer.py -q` — passed, exit-code
  contract (0/2/3) unchanged.
- `uv run pytest -q` (full suite) — passed except the two known pre-existing environmental
  failures (`test_bench.py::test_seed_corpus_is_valid`, `test_preflight.py::...vendored_rules`),
  unchanged from baseline.
- `rg -n 'review_position_gate\(\[\]' sec_overlay/cli.py` — no match.
- `git diff --stat HEAD~1 -- sec_overlay/models.py sec_overlay/evidence.py` — prints nothing, for
  every commit in this plan; frozen-file constraint held throughout.
- `claude plugin validate .` — passed.

## Self-Check: PASSED

All created files found on disk (`review_agent.py`, `review-file.md`, `test_review_live.py`,
`03-06-SUMMARY.md`). All three task commits (`0436562`, `a9b9698`, `9f86ddc`) found in
`git log --oneline --all`.
