---
type: how-to-guide
title: Developing the sec-overlay Skill
description: Test and lint commands, the stdlib-only dependency rule, the structural guard tests, the bench harness (now with a committed public seed corpus and CI detection-regression gate), and the folder-README-tracks-code rule as it applies inside the sec-overlay skill.
tags: [sec-overlay, testing, ruff, bench, folder-readme, ci]
---

# Developing the sec-overlay skill

All commands below run from `skills/sec-overlay/helpers/`.

## Test and lint commands

```bash
uv run pytest -q                                   # full suite (one env-only failure, see below)
uv run pytest tests/test_fingerprint.py -q         # single file
uv run pytest tests/test_x.py::test_name           # single test
uv run ruff check sec_overlay/ bench/ tests/       # lint (line-length 100)
uv run ruff format sec_overlay/ bench/ tests/
uv run ty check                                    # static types
uv run python -m sec_overlay.preflight             # tool availability
uv run python -m sec_overlay.phase_docs --check    # fail if a generated phase-table doc is stale
```

The suite is 145 pytest files under `helpers/tests/`. **One** failure on a clean checkout is
environmental, not a code defect — see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for exactly
which test and why. (An earlier release also treated the bench seed corpus as gitignored,
giving two env-only failures; the corpus now ships committed — see
[the bench harness](#the-bench-harness) below.)

## Keeping the generated phase tables in sync

`sec_overlay/phases.py`'s `PHASE_TABLE` is the single source of truth for phase order. Run
`phase_docs --write` any time it changes — a rename, reorder, or added/removed phase:

```bash
uv run python -m sec_overlay.phase_docs --write   # regenerate every phase-table doc in place
```

This rewrites the generated tables inside `SKILL.md`, the root `README.md`, `agents/README.md`,
and `helpers/README.md` (the skill `CLAUDE.md` is not one of them — it points at `SKILL.md`
instead of carrying its own copy). `--check` exits 1 and names every stale document without
writing; `tests/test_phase_docs.py` calls the same regeneration code inside `uv run pytest`, so
a `PHASE_TABLE` change that skips `--write` fails the normal test run, not just a manual
`--check`.

## The stdlib-only rule

The core has **no runtime dependencies** in `pyproject.toml` — only dev deps (`pytest`, `ruff`,
`ty`). External SAST binaries are shelled out to, never imported. "Do not add a dependency
without a strong justification and user sign-off" (skill `CLAUDE.md` §7). This is a design
constraint the [tool-receipt gate](helpers.md#the-tool-receipt-gate) and the rest of the
deterministic core depend on staying auditable and portable.

## TDD and the structural guard tests

New or changed executable logic ships with a test in the same change (root `CLAUDE.md`'s
repo-wide rule: Python under `helpers/tests/`, shell scripts get a colocated invocation test —
see [commit governance](../../governance/hooks-and-commits.md)). Several tests specifically
guard against silent drift rather than testing one module's behavior:

| Test | Guards against |
|---|---|
| `test_contracts.py` | Prompt↔schema drift — a `Finding` JSON example embedded in an agent prompt must parse against the real `models.py` |
| `test_finding_schema.py` | `models.py`'s `Finding` record staying consistent with `references/finding.schema.json` |
| `test_frozen_contract.py` | `models.py`/`evidence.py` staying byte-identical (sha256-pinned) and `fingerprint()` staying stable — a separate Go port must receive any change by hand |
| `test_wiring.py` | silent-backend regressions, `clsmap` routing gaps, dead links between `attack-classes.md` and its `hunting/` companions, and that `classes/*.md` prompts carry the proof tuple + anti-collapse rule |
| `test_docs_invariants.py` | documentation contracts — `prompt-constants.md` block presence, `finding-template.md` section structure, agent-prompt rules, the generated phase-table block staying in sync with `PHASE_TABLE` |
| `test_phase_docs.py` | `phase_docs.py`'s regeneration staying byte-identical to what's checked in |
| `test_references_caps.py` | `mermaid-caps.md`'s stated caps staying identical to `diagram_gate.py`'s `CAPS`/`SEQ_CAPS` constants |

Keep these green when touching a schema, a class-routing table, an agent prompt's structure, or
the phase order — they are how prompt↔code drift gets caught before it reaches a real audit.

## The bench harness

`helpers/bench/` measures and locks detection quality; it is never invoked during a real scan.
A labelled corpus (positives to find, negatives to stay silent on) is scanned via a swappable
adapter, judged, and scored for precision/recall by source and class plus an FP rate. Its
**regression gate**: a `locked` finding that stops being detected fails the run.

```bash
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
# offline, CI-safe detection-regression gate (no clone, no confirmation LLM pass):
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir> \
  --grade-mode detection --only-local
```

**The seed corpus now ships committed** — `bench/corpus_seed/*.json` (`dogfood.json`,
`absence.json`, `negatives.json`, `dep_cves.json`, `public_apps.json`) holds only public
entries: synthetic fixtures under `helpers/fixtures/`, dep-CVE lockfile pins, and public-app
advisories pinned to a commit. Never add a confirmed vulnerability from private code to it. Two
new adapters widened what the corpus can ingest: `aacr_adapter.py` maps external AACR
review-dataset rows into corpus entries (excluded from the real-confirmed headline; a
security-category row gets its own `aacr-security` slice), and `ocr_ingest.py` parses `ocr
review --format json` output into benchmark-only findings tagged `llm-claimed:ocr`. `driver.py`
is a headless benchmark driver that can run repeated trials and aggregate a scorecard
(`--repeats N`) with mean/range per metric.

`.github/workflows/sec-overlay-tests.yml` runs the offline form on every pull request touching
`helpers/`: the full pytest suite, then a smoke-scan of `fixtures/vulnerable_repo` graded in
`detection` mode against the two `locked` dogfood entries — a **detection**-mode CI gate, not a
confirmation gate, since a deterministic-only scan never reaches `confirmed` (that needs the
adversarial LLM pass).

## The vendored semgrep ruleset

`helpers/rules/semgrep/` is a gitignored, shallow-cloned directory (not a git submodule,
despite older prose that once claimed otherwise) — populate it with
`git clone --depth 1 https://github.com/semgrep/semgrep-rules rules/semgrep` — see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for the test
that fails without it. First-party detection rules (the [absence rule
pack](helpers.md#route-census-and-the-dependency-sink-catalog--closing-recons-blind-spots))
live in the separate, tracked `helpers/rules/absence/` directory instead — never place a
first-party rule under `rules/semgrep/`, since a refresh clone deletes anything placed there.

## The folder-README-tracks-code rule, inside this skill

The repo-wide [doc-update-guard hook](../../governance/hooks-and-commits.md) requires a
folder's `README.md` to be staged whenever a file inside that folder changes, for every folder
that has a *tracked* `README.md` — no skill-specific exception. Inside
`skills/sec-overlay/`, that reaches:

- [`agents/README.md`](/plugins/sec-overlay/skills/sec-overlay/agents/README.md) — every LLM
  prompt: role, model tier, inputs/outputs, the gate ladder, the `classes/` extensions.
- [`helpers/README.md`](/plugins/sec-overlay/skills/sec-overlay/helpers/README.md) — the
  ~100 Python modules grouped by job, the CLI-callable list, the finding schema contract.
- [`references/README.md`](/plugins/sec-overlay/skills/sec-overlay/references/README.md) — the
  rule book: the 16 prompt-constants blocks, schemas, crypto YAMLs.
- Plus the nested folder READMEs one level deeper:
  `helpers/sec_overlay/README.md`, `helpers/tests/README.md`, `helpers/bench/README.md`,
  `helpers/bench/corpus_seed/README.md`, `helpers/rules/README.md`, `references/asvs/README.md`,
  `references/codeguard/README.md`, `references/hunting/README.md`.

The skill's own [`CLAUDE.md`](/plugins/sec-overlay/skills/sec-overlay/CLAUDE.md) §8 states the
policy in human terms: these READMEs "over-explain what lives there and how it works, with
mermaid diagrams and worked flows... the entry point for a person (not just an LLM)". A
skill-local script, `.githooks/pre-commit`, also documents part of this same rule but is not
the mechanism that actually enforces it — see
[commit governance](../../governance/hooks-and-commits.md#a-second-non-primary-hook-inside-the-sec-overlay-skill)
for why the repo-root prek hook is the one that matters.

## Related pages

- [Helpers](helpers.md) — the module map these tests exercise.
- [Agents](agents.md) — the prompt structure `test_wiring.py`/`test_docs_invariants.py` guard.
- [Commit governance](../../governance/hooks-and-commits.md) — the doc-update-guard hook and
  the legacy skill-local hook.
- [Running an audit](running-an-audit.md) — the environment prerequisites these tests reveal
  as missing on a clean checkout.
