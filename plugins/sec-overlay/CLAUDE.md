# CLAUDE.md — sec-overlay plugin maintainer manual

This file guides a maintainer working on the sec-overlay plugin source. It never loads into a
user's session when the plugin is installed (docs-verified against the Claude Code plugin
runtime). For running the skill, see [`skills/sec-overlay/CLAUDE.md`](skills/sec-overlay/CLAUDE.md).

Governance — branching, commits, changelogs, version bumps — lives in the root `CLAUDE.md`;
nothing here overrides it.

---
## Developing the skill

From `skills/sec-overlay/helpers/`:

```bash
uv run pytest -q                                   # full suite (2 env-only failures — see
                                                     # skill CLAUDE.md §1)
uv run pytest tests/test_fingerprint.py -q         # single file
uv run pytest tests/test_x.py::test_name           # single test
uv run ruff check sec_overlay/ bench/ tests/       # lint (line-length 100)
uv run ruff format sec_overlay/ bench/ tests/
uv run ty check                                    # static types
uv run python -m sec_overlay.preflight             # tool availability
```

**Conventions:**
- The core is **stdlib-only by design** — no runtime dependencies in `pyproject.toml` (dev deps:
  pytest, ruff, ty only). Do not add a dependency without a strong justification and user sign-off.
- **TDD for skill code.** The missing-`secrets.py` fix already has failing tests waiting — reconstruct
  to make them pass. `tests/test_contracts.py` + `tests/test_wiring.py` catch prompt↔schema drift and
  silent-backend regressions; keep them green.
- **`helpers/bench/` is dev-only** — a labelled-corpus precision/recall + regression harness, **not**
  part of an audit run. A `locked` positive that stops being detected is a hard failure. Run:
  `python -m bench.run --corpus bench/corpus_seed --run-dir /tmp/bench --workspaces <dir>`.
- **Semgrep rules are a vendored, gitignored clone** (`helpers/rules/semgrep/`), not a git
  submodule — there is no `.gitmodules` entry. Seed it with
  `git clone --depth 1 https://github.com/semgrep/semgrep-rules helpers/rules/semgrep`
  (the exact command `preflight.py` prints when the directory is missing).
- When editing an `agents/*.md` prompt, preserve its hard rules verbatim (model-family diversity,
  tool-receipt safety contract, count-invariant verdict tables) — these are load-bearing, not prose.
- CLI-callable modules (`python -m sec_overlay.<module>`): `cli`, `preflight`, `postflight`,
  `calibrate`, `dedupe`, `verify`, `report`, `redteam`, `bugchain`, `astgrep`, `structural_index`,
  `citations`, `findings_gate`, `rule_gaps`, `redactor`, `graph`, `artifact_gate`, `diagram_gate`,
  `ste_lint`.

---
## Documentation — READMEs track code (enforced)

Each of the three working folders carries a **human-oriented README** that over-explains what
lives there and how it works, with mermaid diagrams and worked flows. They are the entry point
for a person (not just an LLM) trying to understand this codebase — keep them current.

| README | Covers |
|--------|--------|
| [`skills/sec-overlay/README.md`](skills/sec-overlay/README.md) | the map: invariants, architecture, the pipeline, and a full end-to-end **worked example** (one SQLi finding from candidate → confirmed → fixed → redteam-plan). Points at the three folder READMEs and `SKILL.md`. |
| [`skills/sec-overlay/agents/README.md`](skills/sec-overlay/agents/README.md) | every LLM prompt: role, model tier (sonnet producer / opus adversary), inputs/outputs, the producer→adversary rule, the investigate gate ladder, and the `classes/` extensions. |
| [`skills/sec-overlay/helpers/README.md`](skills/sec-overlay/helpers/README.md) | the ~70 Python modules grouped by job, the CLI-callable list, the deterministic pipeline diagram, the finding serialization/schema contract, and the two in-code invariants. |
| [`skills/sec-overlay/references/README.md`](skills/sec-overlay/references/README.md) | the rule book: the 12 `prompt-constants.md` blocks, `attack-classes.md`, the schemas, the crypto-policy YAMLs, and which module/agent consumes each file. |

**Hard rule — docs track code in the same commit.** When you change anything under `agents/`,
`helpers/`, or `references/` (or any folder that has a `README.md`), update that folder's
`README.md` in the **same commit**.

This is enforced repo-wide by the marketplace's prek pre-commit hook
(`scripts/hooks/pre-commit-check.sh`, wired in `.pre-commit-config.yaml`): for every staged file
whose folder contains a tracked `README.md`, that `README.md` must also be staged, or the commit
is rejected with the folder named. Activate the hooks once per clone with `prek install`.

Do **not** bypass with `--no-verify`. A genuinely doc-neutral change still updates the folder
README (a one-line note is enough) — the rule has no exception.

---
## History

`skills/sec-overlay/helpers/sec_overlay/secrets.py` was **reconstructed 2026-07-31** (TDD; it had
been missing, which broke `redactor` and `prefilter` at import). The secrets backend +
secret-masking helper now work and `uv run pytest` collects cleanly. Note
`skills/sec-overlay/helpers/sec_overlay/envelope.py:12`'s `import secrets` is the **stdlib**
module, unrelated to this file.
