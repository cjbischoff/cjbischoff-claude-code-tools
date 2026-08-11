# Incorporate sec-harness KB doc/diagram redesign into sec-overlay

**Date:** 2026-08-11
**Status:** Approved for implementation
**Branch:** `feat/kb-doc-diagram-redesign`

## Goal

Bring the local `sec-overlay` plugin to feature parity with upstream `sec-harness`
for the "KB doc/diagram redesign" series. Preserve the local-only
`render_util` / `expected_signal`-object divergence — do not overwrite it.

## Background

The local `plugins/sec-overlay` skill is a renamed fork of upstream
`cjbischoff/security-harness` (`skills/sec-harness`). The rename maps
`sec_harness`→`sec_overlay` (Python identifiers) and `sec-harness`→`sec-overlay`
(kebab names). Since the local import point, upstream landed one coherent feature
series — 19 commits from 2026-08-11 12:23 to 13:39, the "KB doc/diagram redesign".
That series is the entire feature gap.

The local fork also carries one improvement upstream lacks: the `render_util.py`
module and object-form `expected_signal` handling (local commit a9bceda). The port
must keep this intact.

## Method

Semantic feature port, name-normalized — not a `git cherry-pick` or patch apply
(the fork's prose has diverged: rewritten READMEs, plugin-ization, so a raw patch
would conflict widely). Apply each feature's intent to the renamed files.

- ~22 files take the upstream change cleanly (with rename normalization).
- 7 files need a real merge because the local `render_util` work also touched them;
  the edit regions do not overlap, so both survive:
  `SKILL.md`, `agents/README.md`, `agents/redteam.md`, `helpers/README.md`,
  `references/README.md`, `references/finding.schema.json`, `helpers/sec_overlay/redteam.py`.
- TDD for every helper change: port the upstream test first, confirm it fails
  against local code, then port the implementation to green.

All paths below are relative to
`plugins/sec-overlay/skills/sec-overlay/`.

## Features and commit grouping

One branch, six logical commits. Each commit updates `README.md`, `CHANGELOG.md`
(Common Changelog format), and the affected folder's `README.md`, and leaves
`helpers/` tests green.

### Commit 1 — prompt-constants

Add three shared prompt blocks to `references/prompt-constants.md`:

- `DIAGRAM_STYLE` — mermaid rules: one diagram one job, hard cap of 10 entities
  (nodes + subgraphs), short IDs, detail in legend/edge labels, diagrams are a
  navigational layer never a citation, use ` ```mermaid ` fences.
- `FIELD_OWNERSHIP` — every `Finding` field belongs to exactly one phase; only
  populate the fields your phase's Output section names; never overwrite a
  non-null field outside your remit
  (`reachability`, `runtime_disposition`, `runtime_test`, `open_questions`,
  `risk_score`, `patch_diff`, `verification`).
- `QUALIFIER_PROOF` — a blanket qualifier ("mitigated", "sanitized", "allowlisted",
  "single chokepoint", …) is a claim about every path; enumerate all call
  sites/paths, confirm on all, cite each, or state only the specific path verified.

Update `references/README.md` to list the new blocks.

### Commit 2 — open_questions model

- `helpers/sec_overlay/models.py`: add `open_questions: list[dict] = field(default_factory=list)`
  to `Finding`, with the docstring describing item shape
  `{"question", "why_it_matters", "who_to_ask_or_check"}` and the note that it is
  unrelated to `coverage_ledger`'s same-named list.
- `references/finding.schema.json`: add
  `"open_questions": {"type": "array", "items": {"type": "object"}}`
  (merge alongside the local `expected_signal` schema addition).
- `helpers/tests/test_models.py`: port upstream test cases (default empty,
  round-trip through `to_dict`).

### Commit 3 — phase-gate comment flagging

- `helpers/sec_overlay/phase_gate.py`: add `is_comment_line(root, ref) -> bool | None`
  (language-agnostic leading-symbol heuristic; prose files only flag `<!--`), the
  `_COMMENT_PREFIXES` / `_PROSE_*` constants, and wire the flag into
  `run_phase_checks` as a gate note (not a hard verdict change).
- `helpers/tests/test_phase_gate.py`: port upstream cases (comment line, code line,
  prose heading, unresolved ref → `None`).

### Commit 4 — verify placeholder-version FP fix

- `helpers/sec_overlay/verify.py`: add `_PLACEHOLDER_VERSION_RE` and
  `_placeholder_version_bump(patch_diff)`; short-circuit `verify_patch` to
  `"not-fixed"` when `cls == "deps"` and the diff adds a literal `vX.Y.Z`
  placeholder.
- `helpers/tests/test_verify.py`: port upstream cases (placeholder bump not
  credited; real version bump unaffected; non-deps class unaffected).

### Commit 5 — context deployment_config + diagram slot

- `helpers/sec_overlay/context.py`:
  - add `"deployment_config"` to `KINDS`.
  - add `_DEPLOYMENT_CONFIG_GLOBS` (Pulumi, tfvars, helm values, k8s, docker-compose,
    serverless).
  - add `ContextItem.deployed_in: str = ""`.
  - add `Context.diagram: str = ""`, include it in `to_dict`/`from_dict` and render
    it into `CONTEXT.md` via `render_markdown`.
- `helpers/tests/test_context.py`: port upstream cases (new kind validates, IaC
  glob discovery, diagram round-trip and render).

### Commit 6 — prompt wiring, redteam questions, doc sync

- `helpers/sec_overlay/redteam.py`: add `_question_block(f)` and the
  "Questions to ask" section in `render_plan` (merge with the local
  `signal_lines` delegation — non-overlapping).
- `helpers/tests/test_redteam.py`: port upstream cases (questions rendered when
  present, `_none_` when absent).
- Agent-prompt edits (name-normalized): `architecture.md` (canonical structural
  doc, 3-diagram sequence), `threat-model.md` (attacker-lens diagrams, stop
  restating boundaries), `context-ingest.md` (narrowed lens, deployment-config
  cross-check + diagram), `recon.md` (QUALIFIER_PROOF), `patch.md`/`critic.md`
  (FIELD_OWNERSHIP), `investigate.md`, `validate.md`/`validate-fix.md`,
  `trace.md`/`redteam.md` (populate `open_questions`), `context-adversary.md` /
  `phase-adversary.md` / adversary prompts (check diagrams for consistency),
  `variant-hunt.md`/`tune-config.md`/`factcheck.md`/`judge.md`/`bugchain.md`/
  `cross-repo-adversary.md` where the upstream series touched them.
- Doc sync: `CLAUDE.md`, `SKILL.md`, `agents/README.md`, `helpers/README.md`
  (KB lens split, `open_questions` rendering, new helper functions) — merge with
  local `render_util` doc lines.

## Merge-sensitive files (local render_util work coexists)

`SKILL.md`, `agents/README.md`, `agents/redteam.md`, `helpers/README.md`,
`references/README.md`, `references/finding.schema.json`,
`helpers/sec_overlay/redteam.py`. In each, the upstream edit region and the local
edit region are disjoint; keep both.

## Governance

- Branch: `feat/kb-doc-diagram-redesign`; Conventional Commits.
- Every commit updates `README.md` + `CHANGELOG.md` and the affected folder's
  `README.md` in the same commit.
- Run `pytest -q` in `plugins/sec-overlay/skills/sec-overlay/helpers/` per commit;
  fix all failures before committing.
- Run `claude plugin validate .` before merge.
- Do **not** bump the plugin `version` field (user bumps manually on release).
- Merge to `main` only after user approval; delete the branch after merge.

## Success criteria

1. All five new test modules (`test_context`, `test_models`, `test_phase_gate`,
   `test_redteam`, `test_verify`) present and green.
2. Full `helpers/` suite passes after each commit.
3. Local `render_util` / `expected_signal` behavior and its tests still pass.
4. `claude plugin validate .` passes.
5. `references/prompt-constants.md` contains `DIAGRAM_STYLE`, `FIELD_OWNERSHIP`,
   `QUALIFIER_PROOF`; `Finding` has `open_questions`; `context.py` has the
   `deployment_config` kind and `Context.diagram`.

## Out of scope

- Upstream's internal plan/spec docs (`docs/superpowers/plans/2026-08-11-…`,
  `docs/superpowers/specs/2026-08-09-…`).
- Plugin `version` bump.
- Prose refactoring beyond what a feature requires.
- Any ongoing upstream-sync mechanism (this is a one-time catch-up).
