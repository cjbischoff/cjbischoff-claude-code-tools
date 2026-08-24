---
type: how-to-guide
title: Developing the sec-overlay Skill
description: Test and lint commands, the stdlib-only dependency rule, the structural guard tests, the dev-only bench harness, and the folder-README-tracks-code rule as it applies inside the sec-overlay skill.
tags: [sec-overlay, testing, ruff, bench, folder-readme]
---

# Developing the sec-overlay skill

All commands below run from `skills/sec-overlay/helpers/`.

## Test and lint commands

```bash
uv run pytest -q                                   # full suite (1 env-only failure, see below)
uv run pytest tests/test_fingerprint.py -q         # single file
uv run pytest tests/test_x.py::test_name           # single test
uv run ruff check sec_overlay/ bench/ tests/       # lint (line-length 100)
uv run ruff format sec_overlay/ bench/ tests/
uv run ty check                                    # static types
uv run python -m sec_overlay.preflight             # tool availability
```

The suite is 120 pytest files under `helpers/tests/` (file count verified against the
filesystem; treat any specific function-count claim in a source README as a snapshot, not a
promise — it drifts with every test-adding commit). One failure on a clean checkout is
environmental, not a code defect — see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for exactly
which test and why.

## The stdlib-only rule

The core has **no runtime dependencies** in `pyproject.toml` — only dev deps (`pytest`, `ruff`,
`ty`). External SAST binaries are shelled out to, never imported. "Do not add a dependency
without a strong justification and user sign-off" (skill `CLAUDE.md` §7). This is a design
constraint the [tool-receipt gate](helpers.md#the-tool-receipt-gate) and the rest of the
deterministic core depend on staying auditable and portable.

## TDD and the structural guard tests

New or changed executable logic ships with a test in the same change (root `CLAUDE.md`'s
repo-wide rule: Python under `helpers/tests/`, shell scripts get a colocated invocation test —
see [commit governance](../../governance/hooks-and-commits.md)). Four tests specifically guard
against silent drift rather than testing one module's behavior:

| Test | Guards against |
|---|---|
| `test_contracts.py` | Prompt↔schema drift — a `Finding` JSON example embedded in an agent prompt must parse against the real `models.py` |
| `test_finding_schema.py` | `models.py`'s `Finding` record staying consistent with `references/finding.schema.json` |
| `test_wiring.py` | silent-backend regressions, `clsmap` routing gaps, dead links between `attack-classes.md` and its `hunting/` companions, and that `classes/*.md` prompts carry the proof tuple + anti-collapse rule |
| `test_docs_invariants.py` | documentation contracts — `prompt-constants.md` block presence, `finding-template.md` section structure, agent-prompt rules (determinism, tool-receipt trust, evidence chains) |

Keep all four green when touching a schema, a class-routing table, or an agent prompt's
structure — they are how prompt↔code drift gets caught before it reaches a real audit.

## The bench harness (dev-only, not part of an audit)

`helpers/bench/` measures and locks detection quality; it is never invoked during a real scan.
A labelled corpus (positives to find, negatives to stay silent on) is scanned via a swappable
adapter, judged, and scored for precision/recall by source and class plus an FP rate. Its
**regression gate**: a `locked` finding that stops being detected fails the run.
`bench/corpus_seed/*.json` **ships committed** (public-app advisories pinned to a commit,
dependency-CVE lockfiles, and synthetic fixtures under `helpers/fixtures/`) — never add a
confirmed vulnerability from private code to it. `aacr_adapter.py` and `ocr_ingest.py` add
external-dataset ingest adapters; `driver.py` is a headless benchmark driver that can run
without a live agent session.

```bash
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
```

## CI: the detection-regression gate

`.github/workflows/sec-overlay-tests.yml` gates every pull request that touches
`helpers/**` (or the workflow file itself) on two offline jobs, both run from
`plugins/sec-overlay/skills/sec-overlay/helpers/`: the full `uv run pytest -q` suite, then a
smoke-scan of the committed `fixtures/vulnerable_repo` fixture followed by
`python -m bench.run --corpus bench/corpus_seed --grade-mode detection --only-local
--no-resume` — a `locked` positive that stops being detected fails the job. Detection mode
grades whether a Tier-1 mechanical receipt located a ground-truth finding; it never runs the
adversarial LLM pass, so the confirmation gate (`reportable`) is untouched and cannot run in
CI. Only GitHub-owned `actions/checkout` (SHA-pinned) is used; `uv` and `semgrep` install from
their own official installers to avoid third-party Actions.

## The vendored semgrep rules mirror

`helpers/rules/semgrep/` is a **gitignored, shallow-cloned mirror** of
[semgrep/semgrep-rules](https://github.com/semgrep/semgrep-rules) — **not** a git submodule
(there is no `.gitmodules` entry in this repository). Seed it with
`git clone --depth 1 https://github.com/semgrep/semgrep-rules skills/sec-overlay/helpers/rules/semgrep`
— see [running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for the
test that fails without it. Never add a first-party rule under this directory: `preflight.py`
recreates it with a fresh shallow clone, which deletes anything placed there. First-party rules
belong under the **tracked** `helpers/rules/absence/` pack instead (pairs of `pattern`/
`pattern-not` rules that fire only on a dangerous construction missing its safe option).

## The folder-README-tracks-code rule, inside this skill

The repo-wide [doc-update-guard hook](../../governance/hooks-and-commits.md) requires a
folder's `README.md` to be staged whenever a file inside that folder changes, for every folder
that has a *tracked* `README.md` — no skill-specific exception. Inside
`skills/sec-overlay/`, that reaches:

- [`agents/README.md`](/plugins/sec-overlay/skills/sec-overlay/agents/README.md) — every LLM
  prompt: role, model tier, inputs/outputs, the gate ladder, the `classes/` extensions, and the
  diff-review-track prompts.
- [`helpers/README.md`](/plugins/sec-overlay/skills/sec-overlay/helpers/README.md) — the ~90
  Python modules grouped by job, the CLI-callable list, the finding schema contract.
- [`references/README.md`](/plugins/sec-overlay/skills/sec-overlay/references/README.md) — the
  rule book: the 15 prompt-constants blocks, schemas, crypto YAMLs, diagram/prose standards.
- Plus the nested folder READMEs one level deeper:
  `helpers/sec_overlay/README.md`, `helpers/tests/README.md`, `helpers/bench/README.md`,
  `helpers/rules/README.md`, `references/asvs/README.md`, `references/codeguard/README.md`,
  `references/hunting/README.md`, `agents/classes/README.md`, `rules/rule_docs/README.md`.

The skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §8 states the
policy in human terms: these READMEs "over-explain what lives there and how it works, with
mermaid diagrams and worked flows... the entry point for a person (not just an LLM)". A
skill-local script, `.githooks/pre-commit`, also documents part of this same rule but is not
the mechanism that actually enforces it — see
[commit governance](../../governance/hooks-and-commits.md#a-second-non-primary-hook-inside-the-sec-overlay-skill)
for why the repo-root prek hook is the one that matters.

## Related pages

- [Helpers](helpers.md) — the module map these tests exercise.
- [Review mode](review-mode.md) — the review-track modules and their own focused tests
  (`test_review_*.py`, `test_bundle.py`, `test_reflection.py`, `test_sessions.py`, `test_pr_poster.py`).
- [Agents](agents.md) — the prompt structure `test_wiring.py`/`test_docs_invariants.py` guard.
- [Commit governance](../../governance/hooks-and-commits.md) — the doc-update-guard hook and
  the legacy skill-local hook.
- [Running an audit](running-an-audit.md) — the environment prerequisites these tests reveal
  as missing on a clean checkout.
