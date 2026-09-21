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
uv run pytest -q                                   # full suite (1 named env-only failure, see below)
uv run pytest tests/test_fingerprint.py -q         # single file
uv run pytest tests/test_x.py::test_name           # single test
uv run ruff check sec_overlay/ bench/ tests/       # lint (line-length 100)
uv run ruff format sec_overlay/ bench/ tests/
uv run ty check                                    # static types
uv run python -m sec_overlay.preflight             # tool availability
uv run python -m sec_overlay.phase_docs --check    # fail if a phase-table doc is stale
```

The suite is 145 pytest files under `helpers/tests/` (filesystem-verified; `helpers/README.md`'s
own prose count lags additions and should not be trusted over a direct file count). The one
named env-only failure on a clean checkout is environmental, not a code defect — see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for exactly
which test and why.

## CI

[`.github/workflows/sec-overlay-tests.yml`](/.github/workflows/sec-overlay-tests.yml) runs on
every pull request touching `plugins/sec-overlay/skills/sec-overlay/helpers/**`, offline (no
repo cloning, no network SAST): the full `uv run pytest` suite, a smoke-scan of the
`fixtures/vulnerable_repo` fixture, and a **detection-regression gate** —
`python -m bench.run --corpus bench/corpus_seed --grade-mode detection --only-local` — that
fails the job if a `locked` positive stops being detected. Detection mode only checks whether a
Tier-1 mechanical receipt located a ground-truth finding; it never checks confirmation, since a
deterministic-only CI run has no adversarial LLM pass to confirm anything. Third-party Actions
are avoided per repo policy: `uv` installs via the official script, semgrep via `pip`, and only
the GitHub-owned, SHA-pinned `actions/checkout` is used.

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
adapter, judged, and scored for precision/recall by source and class plus an FP rate.
`bench/corpus_seed/` ships **committed** — public entries only (pinned public-app advisories,
dep-CVE lockfiles, and synthetic absence/dogfood fixtures under `helpers/fixtures/`) — so the
CI workflow above and any contributor can run it without seeding private data; never add a
confirmed vulnerability from private code to the seed. Its **regression gate**: a `locked`
finding that stops being detected fails the run.

```bash
python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>
```

## The vendored semgrep rules — not a submodule

`helpers/rules/semgrep/` is a **gitignored shallow clone**, not a git submodule:
`git clone --depth 1 https://github.com/semgrep/semgrep-rules helpers/rules/semgrep` — see
[running an audit](running-an-audit.md#environment-prerequisites-for-a-full-run) for the one
test that fails without it. Do not add a `.gitmodules` entry or otherwise reintroduce a
submodule instruction: `test_docs_invariants.py::test_no_live_doc_claims_a_git_submodule_that_does_not_exist`
scans every live doc surface for that stale phrasing and fails if it reappears.

## The folder-README-tracks-code rule, inside this skill

The repo-wide [doc-update-guard hook](../../governance/hooks-and-commits.md) requires a
folder's `README.md` to be staged whenever a file inside that folder changes, for every folder
that has a *tracked* `README.md` — no skill-specific exception. Inside
`skills/sec-overlay/`, that reaches:

- [`agents/README.md`](/plugins/sec-overlay/skills/sec-overlay/agents/README.md) — every LLM
  prompt: role, model tier, inputs/outputs, the gate ladder, the `classes/` extensions.
- [`helpers/README.md`](/plugins/sec-overlay/skills/sec-overlay/helpers/README.md) — the ~100
  Python modules grouped by job, the CLI-callable list, the finding schema contract.
- [`references/README.md`](/plugins/sec-overlay/skills/sec-overlay/references/README.md) — the
  rule book: the 12 prompt-constants blocks, schemas, crypto YAMLs.
- Plus the nested folder READMEs one level deeper:
  `agents/classes/README.md`, `helpers/sec_overlay/README.md`, `helpers/tests/README.md`,
  `helpers/bench/README.md`, `helpers/bench/corpus_seed/README.md`, `helpers/rules/README.md`,
  `references/asvs/README.md`, `references/codeguard/README.md`, `references/hunting/README.md`.

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
