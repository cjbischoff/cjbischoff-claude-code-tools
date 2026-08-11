# sec-overlay Documentation Overhaul — Design

**Date:** 2026-08-11
**Status:** Approved (design); pending spec review before plan.

## Goal

Refocus the sec-overlay documentation on how this fork actually works. Remove
stale Go-rewrite prose, rewrite the root marketplace README to a fixed
template, refocus the skill CLAUDE.md on repo mechanics, write an overview
README for the skill with diagrams and a worked example, add per-folder
READMEs to the meaningful folders that lack one, and extend the pre-commit
hook to keep folder READMEs fresh.

## Non-goals

- No change to Python behavior, the finding gate, or the pipeline logic.
- No edits to archival planning docs (`docs/plans`, `docs/gsd`,
  `docs/dogfooding`) or test fixtures.
- No plugin `version` bump.

## Constraints (governance)

- Work on branch `docs/sec-overlay-doc-overhaul`; never commit to `main`.
- Conventional Commits; summary under 50 chars; body wrapped at 72.
- Every commit updates `README.md` and `CHANGELOG.md` in the same commit.
- A commit that changes a tracked file inside a Directory-Guide folder updates
  that folder's `README.md` in the same commit.
- No `Co-Authored-By` trailer; no `--no-verify`.
- Name normalization everywhere: `sec_overlay` / `sec-overlay` /
  `$SEC_OVERLAY_HOME` / `.sec-overlay` / `{{OVERLAY_ROOT}}`.

## Verified facts

- Go port does not exist in this fork: no `go/`, `gen_golden.py`, or
  `TestParity`. The "frozen contract with the Go port" prose is fully stale.
- Python project root is `plugins/sec-overlay/skills/sec-overlay/helpers/`;
  `pyproject.toml` there sets `line-length = 100`; stdlib-only runtime, dev
  deps pytest/ruff/ty.
- `sec_overlay.preflight` module exists.
- Test baseline: 573 pass, exactly 2 env-only failures
  (`test_bench.py::test_seed_corpus_is_valid` — gitignored bench corpus;
  `test_preflight.py::test_report_finds_vendored_rules_regardless_of_cwd` —
  excluded semgrep submodule).
- Contract tests that already enforce serialization/schema stability:
  `test_contracts.py`, `test_finding_schema.py`.
- Pre-commit hook: `scripts/hooks/pre-commit-check.sh` (doc-update-guard),
  `pass_filenames: false`, `always_run: true`.
- No git remote configured; no `LICENSE` file.

## Confirmed assumptions

- Install repo slug: `cjbischoff/cjbischoff-claude-code-tools`.
- License stated as MIT in the README only; no `LICENSE` file added.

---

## Section 1 — Remove Go-rewrite prose (live docs only)

Edit four live docs; remove every Go/frozen-contract-with-Go passage.

| File | Action |
|------|--------|
| `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` | Delete the entire §1 "protecting the parallel Go conversion" section; scrub the Go references at the intro line, `BinaryAdapter` line, helpers/README row, and hook-install notes. |
| `plugins/sec-overlay/skills/sec-overlay/README.md` | Remove the "Go port" callout and the CLAUDE.md-row Go reference. |
| `plugins/sec-overlay/skills/sec-overlay/helpers/README.md` | Remove the "frozen contract with the Go port" block. |
| `plugins/sec-overlay/skills/sec-overlay/references/README.md` | Remove the frozen-contract parenthetical. |

**Replacement for the "change carefully" intent** (retarget, do not just
delete): a short note that `models.py` and `evidence.py` define the finding
serialization/schema contract, and changing a field requires updating
`finding.schema.json` and the contract tests (`test_contracts.py`,
`test_finding_schema.py`). No mention of Go, goldens, or byte-parity.

Archival docs and fixtures untouched.

## Section 2 — Root marketplace README (template)

Rewrite `README.md` to this template shape:

```
# cjbischoff-claude-code-tools

Claude Code plugin marketplace — personal plugins for Christopher Bischoff.

## Installation
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install sec-overlay@cjbischoff-claude-code-tools

## Plugins
- **sec-overlay**: agentic security-audit harness (static analysis, tool-receipt gate)

## Development
claude plugin validate .      # validate plugin + marketplace manifests
prek run                      # run governance hooks
uv run pytest -q              # Python core tests (run from skills/sec-overlay/helpers)

## Governance
(branch-per-change, Conventional Commits, forced README/CHANGELOG + folder-README updates)

## License
MIT
```

- Drop the docs-site section (no site).
- Keep the Directory Guide and Artifact inventory (they carry governance
  meaning) but collapse the running per-task Status log to a short
  current-state summary.
- Keep the Decisions section.

## Section 3 — Skill CLAUDE.md refocus

Rewrite `plugins/sec-overlay/skills/sec-overlay/CLAUDE.md` around repo
mechanics: updating READMEs, the CHANGELOG, the git protocol, "tests required
for all scripts," and how to test. Name-normalized, path-corrected command
block, corrected to the real 2 env-only failures (run from `helpers/`):

```
uv run pytest -q                              # full suite (2 env-only failures; see §2)
uv run pytest tests/test_x.py::test_name      # single test
uv run ruff check sec_overlay/ bench/ tests/  # lint (line-length 100)
uv run ty check                               # static types
uv run python -m sec_overlay.preflight        # verify SAST tooling + CodeQL packs
git submodule update --init --recursive       # check out the semgrep rules submodule
```

State plainly: Python core is stdlib-only (no runtime deps); dev deps are
pytest, ruff, ty. Add a §on the folder-README freshness rule (see Section 6).

## Section 4 — Skill top-level README (overview)

Rewrite `skills/sec-overlay/README.md` as the overview. Contents:

1. **The four invariants** (name-normalized):
   - Never executes or modifies the reviewed source — static analysis only;
     patches applied to a throwaway copy.
   - Writes only its own sidecar — `<target>/.sec-overlay/<slug>/`; override
     base with `$SEC_OVERLAY_HOME`, whole workspace with `--workspace`;
     seeded `.sec-overlay/.gitignore`.
   - Tool-receipt gate — confirmed/fixed only with >=1 mechanical receipt
     (semgrep / codeql / ast-grep / tree-sitter / ripgrep / structural-index
     / secrets / sca); LLM reasoning namespaced `llm-claimed:`, can
     corroborate never confirm; enforced in `helpers/…/findings_gate.py`.
   - Signal over noise — every load-bearing Sonnet "producer" claim is
     attacked by an Opus "adversary" on a different model family;
     false-positive ladder + needs-deployment-testing verdict.
2. **Mermaid architecture diagram** — components and their relationships.
3. **Mermaid pipeline-flow diagram** — the phase sequence.
4. **Worked example** — one SQL-injection finding, end to end.
5. **How to run it.**
6. **What you get** — the output workspace layout.
7. **Pointers** to each sub-folder README.
8. Reference: https://github.com/cjbischoff/security-harness/tree/main/skills/sec-harness

Both diagrams and the worked example are hand-authored from the current
pipeline and must be checked against the code, not asserted.

## Section 5 — Per-folder READMEs (meaningful folders)

Add a `README.md` describing each file's form and function to the six folders
that lack one:

| Folder | Files |
|--------|-------|
| `agents/classes` | 11 |
| `helpers/sec_overlay` | 71 (the Python core package) |
| `helpers/tests` | 81 |
| `references/asvs` | 1 |
| `references/codeguard` | 7 |
| `references/hunting` | 8 |

Archival subtrees and fixtures skipped.

## Section 6 — Hook: per-folder README freshness

Extend `scripts/hooks/pre-commit-check.sh`: when a commit stages files inside
a folder that contains a `README.md`, that folder's `README.md` must also be
staged, else block the commit with an actionable message naming the folder.

- Test is a pytest that shells out to the script inside a temporary git repo
  (red first, then green) — bash logic, tested by invocation.
- Document the rule in prose in the skill `CLAUDE.md` and the root README
  governance section.

---

## Commit grouping

1. Remove Go prose from the four live docs (+ contract-note replacement).
2. Root README rewrite to the template.
3. Skill CLAUDE.md refocus.
4. Skill overview README with diagrams and worked example.
5. Six per-folder READMEs.
6. Hook extension + pytest + governance-doc note.

Each commit carries its own README/CHANGELOG/folder-README updates per
governance.

## Trade-offs accepted

- Docs-only except the one hook change.
- Diagrams and the worked SQLi example need a correctness pass against the
  code; they are the highest-risk content for drift.
- The hook change adds an enforcement point that blocks commits when a folder
  README is forgotten — intended.
