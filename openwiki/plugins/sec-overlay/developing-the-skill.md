---
type: how-to-guide
title: Developing the sec-overlay Skill
description: Test and lint commands, the stdlib-only dependency rule, the structural guard tests, the dev-only bench harness with its committed public-only seed corpus, the phase-table doc generator, and the folder-README-tracks-code rule as it applies inside the sec-overlay skill.
tags: [sec-overlay, testing, ruff, bench, folder-readme, phase-docs]
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
uv run python -m sec_overlay.phase_docs --check    # fail if a phase-table doc is stale
uv run python -m sec_overlay.phase_docs --write    # regenerate every phase-table doc in place
```

The suite is 142 pytest files, 1830 tests (`helpers/tests/README.md`'s own count). One failure
on a clean checkout is environmental, not a code defect — the vendored semgrep rules clone is
gitignored, so `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` fails
until it is fetched; see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run). This is down
from two known environmental failures in earlier milestones: the bench corpus used to be
gitignored too, but it now ships committed (below), so its tests pass on a clean checkout.

## The stdlib-only rule

The core has **no runtime dependencies** in `pyproject.toml` — only dev deps (`pytest`, `ruff`,
`ty`). External SAST binaries are shelled out to, never imported. Do not add a dependency
without a strong justification and user sign-off (skill `CLAUDE.md`). This is a design
constraint the [tool-receipt gate](helpers.md#the-tool-receipt-gate) and the rest of the
deterministic core depend on staying auditable and portable.
`tests/test_frozen_contract.py::test_helpers_declare_zero_runtime_dependencies` pins it.

## TDD and the structural guard tests

New or changed executable logic ships with a test in the same change (root `CLAUDE.md`'s
repo-wide rule: Python under `helpers/tests/`, shell scripts get a colocated invocation test —
see [commit governance](../../governance/hooks-and-commits.md)). Several tests specifically
guard against silent drift rather than testing one module's behavior:

| Test | Guards against |
|---|---|
| `test_contracts.py` | Prompt↔schema drift — a `Finding` JSON example embedded in an agent prompt must parse against the real `models.py` |
| `test_finding_schema.py` | `models.py`'s `Finding` record staying consistent with `references/finding.schema.json` |
| `test_contract_lint.py` | Closed-vocabulary / schema-enum drift, dispatch-token single-sourcing, and that the `<!-- BEGIN PHASE NOTES -->` region names every `PHASE_TABLE` phase and nothing else |
| `test_wiring.py` | silent-backend regressions, `clsmap` routing gaps, dead links between `attack-classes.md` and its `hunting/` companions, and that `classes/*.md` prompts carry the proof tuple + anti-collapse rule |
| `test_docs_invariants.py` | documentation contracts — `prompt-constants.md` block presence, `finding-template.md` section structure, agent-prompt rules (determinism, tool-receipt trust, evidence chains), and the attack-class/dependency-catalog wiring |
| `test_phase_docs.py` | that `SKILL.md`, the skill root `README.md`, `agents/README.md`, and `helpers/README.md` all carry a current `<!-- BEGIN GENERATED: phase-table -->` block matching `phases.PHASE_TABLE` — a renamed/reordered phase that skips `--write` fails this test, not just a manual `--check` |
| `test_no_dead_helpers.py` | a public helper function with no caller and no listed allowlist reason |

Keep these green when touching a schema, a class-routing table, an agent prompt's structure, or
`phases.PHASE_TABLE` itself — they are how prompt↔code drift gets caught before it reaches a
real audit. Run `phase_docs --write` any time `PHASE_TABLE` changes (a rename, reorder, or
added/removed phase); `--check` exits 1 and names every stale document without writing.

## The bench harness (dev-only, not part of an audit)

`helpers/bench/` measures and locks detection quality; it is never invoked during a real scan.
A labelled corpus (positives to find, negatives to stay silent on) is scanned via a swappable
adapter, judged, and scored for precision/recall by source and class plus an FP rate. Its
**regression gate**: a `locked` finding that stops being detected fails the run.

`corpus_seed/` now ships **committed** — public entries only (public-app advisories pinned to a
commit, dependency-CVE lockfiles, synthetic fixtures), at least 30 entries across the required
source mix — so its validity/count tests run in CI as well as locally (see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run)). Never add a
confirmed vulnerability from private code to the seed. Beyond the original `corpus.py`/`judge.py`
/`tally.py`/`adapter.py`/`run.py` core, the harness has grown `aacr_adapter.py` (maps an external
AACR review-dataset into benchmark-only corpus entries, excluded from the real-confirmed
headline) and `ocr_ingest.py` (parses `ocr review --format json` output into benchmark-only
`llm-claimed:ocr` findings) — both dev-only ingestion adapters, never harness findings.

```bash
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
```

## The semgrep rules — gitignored clone, not a git submodule

`helpers/rules/semgrep/` is a **plain gitignored directory**, fetched with
`git clone --depth 1 https://github.com/semgrep/semgrep-rules rules/semgrep` — `preflight.py`'s
own remediation text prints this exact command. It is not a tracked git submodule and is not
restored by `git submodule update`. See
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for the test
that fails without it. `helpers/rules/absence/` is a separate, **tracked** first-party pack that
ships with the plugin — never put a first-party rule under `helpers/rules/semgrep/` itself,
since `preflight.py` recreates that directory with a fresh clone, deleting anything placed there.

## The folder-README-tracks-code rule, inside this skill

The repo-wide [doc-update-guard hook](../../governance/hooks-and-commits.md) requires a
folder's `README.md` to be staged whenever a file inside that folder changes, for every folder
that has a *tracked* `README.md` — no skill-specific exception. Inside
`skills/sec-overlay/`, that reaches:

- [`agents/README.md`](/plugins/sec-overlay/skills/sec-overlay/agents/README.md) — every LLM
  prompt: role, model tier, inputs/outputs, the gate ladder, the `classes/` extensions.
- [`helpers/README.md`](/plugins/sec-overlay/skills/sec-overlay/helpers/README.md) — the ~95
  Python modules grouped by job, the CLI-callable list, the finding schema contract.
- [`references/README.md`](/plugins/sec-overlay/skills/sec-overlay/references/README.md) — the
  rule book: the 16 prompt-constants blocks, schemas, crypto YAMLs.
- Plus the nested folder READMEs one level deeper:
  `helpers/sec_overlay/README.md`, `helpers/tests/README.md`, `helpers/bench/README.md`,
  `helpers/bench/corpus_seed/README.md`, `helpers/rules/README.md`, `agents/classes/README.md`,
  `references/asvs/README.md`, `references/codeguard/README.md`, `references/hunting/README.md`.

The skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) states the
policy in human terms: these READMEs "over-explain what lives there and how it works, with
mermaid diagrams and worked flows... the entry point for a person (not just an LLM)". A
skill-local script, `.githooks/pre-commit`, also documents part of this same rule but is not
the mechanism that actually enforces it — see
[commit governance](../../governance/hooks-and-commits.md#a-second-non-primary-hook-inside-the-sec-overlay-skill)
for why the repo-root prek hook is the one that matters.

## Related pages

- [Helpers](helpers.md) — the module map and the tool-receipt gate these tests protect.
- [Agents](agents.md) — the prompt contract `test_contracts.py`/`test_wiring.py` enforce.
- [References](references.md) — the schemas/policy these drift tests pin.
- [Running an audit](running-an-audit.md) — the one remaining environmental test failure in
  full context.
