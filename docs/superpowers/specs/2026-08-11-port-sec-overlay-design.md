# Design: port `sec-harness` into the `sec-overlay` plugin

Date: 2026-08-11
Status: approved (design), pending spec review
Branch: `feat/port-sec-overlay`

## Goal

Convert the `sec-harness` skill from
`github.com/cjbischoff/security-harness` (path `skills/sec-harness/`) into a
plugin named `sec-overlay` in this marketplace. Port all source files and rename
the `sec-harness` / `sec_harness` identifier to `sec-overlay` / `sec_overlay`
throughout. The ported plugin must pass its own test suite and
`claude plugin validate`.

## Source facts (verified against a shallow clone, 2026-08-11)

- Source path `skills/sec-harness/` holds 272 files, 2.1 MB.
- It is a full Python package `sec_harness` (~90 modules under
  `helpers/sec_harness/`) with ~50 tests under `helpers/tests/`, a `pyproject.toml`,
  and a `uv.lock`.
- 34 subagent prompt files under `agents/`.
- 28 internal planning/dogfooding docs under `docs/`.
- `references/` holds schemas, `hunting/`, `codeguard/`, and `asvs/` data.
- `helpers/rules/semgrep` is a **git submodule** pointing at
  `github.com/semgrep/semgrep-rules`. Submodules are not copied into the plugin
  cache on install, so it cannot ship as a submodule.
- The identifier appears as `sec_harness` (underscore) in 179 files and
  `sec-harness` (hyphen) in 90 files.
- The current local `plugins/sec-overlay/` is a placeholder (stub `run.py`,
  generic `SKILL.md`) that does not match the real skill and will be replaced.

## Decisions

1. **Rename depth: full.** Rename the human-facing identity and the Python import
   package `sec_harness` -> `sec_overlay`. Re-run the full test suite to prove the
   rename did not break anything.
2. **Port scope: everything.** Port all 272 files, including internal `docs/` and
   the `bench/` harness. Apply the rename to all ported files.
3. **semgrep submodule: document as prerequisite.** Ship the real
   `rules/smoke.yaml`; drop the submodule; document that `--config` points at the
   user's own semgrep ruleset.

## Target structure

```
plugins/sec-overlay/
├── .claude-plugin/plugin.json          # name sec-overlay, version kept 0.1.0, description updated
├── README.md                           # short marketplace folder README (governance)
└── skills/sec-overlay/                 # = source skills/sec-harness/, all files, renamed
    ├── SKILL.md, README.md, CLAUDE.md, .githooks/
    ├── agents/        (34 prompt files)
    ├── docs/          (28 internal docs — ported verbatim, rename applied)
    ├── references/    (schemas, hunting/, codeguard/, asvs/, rules docs)
    └── helpers/
        ├── pyproject.toml   # name -> sec-overlay, packages -> ["sec_overlay"]
        ├── uv.lock
        ├── sec_overlay/     # renamed from sec_harness/ (~90 modules)
        ├── tests/           # ~50 files, imports updated
        ├── bench/, fixtures/
        └── rules/           # smoke.yaml + README only; NO semgrep submodule
```

The plugin name and the single skill name are both `sec-overlay`, so the skill
lives at `plugins/sec-overlay/skills/sec-overlay/`.

## Rename rules (precise, not blanket)

Replace exactly two tokens wherever they occur:

- `sec-harness` -> `sec-overlay`
- `sec_harness` -> `sec_overlay` (includes the directory
  `helpers/sec_harness/` -> `helpers/sec_overlay/`)

Do **not** change:

- the bare English word "harness" in prose (the skill refers to "the harness"
  throughout);
- internal token names such as `{{HARNESS_ROOT}}` and `{{HELPERS_DIR}}` (they are
  not the `sec-harness` identifier).

## Plugin-path adaptation

The source `SKILL.md` instructs the driving agent to compute `{{HARNESS_ROOT}}`
and `{{HELPERS_DIR}}` as absolute paths to `skills/sec-harness/...`. For the
installed plugin these must derive from `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay`,
otherwise the tokens resolve outside the plugin cache. Edit the `SKILL.md` run
instructions accordingly. This is the only functional change beyond renaming.

## Verification gates (all must pass before merge)

1. `uv run pytest -q` in `plugins/sec-overlay/skills/sec-overlay/helpers` — green.
   The suite includes `test_wiring.py` and `test_docs_invariants.py`, which assert
   on SKILL/agent/doc references; an inconsistent rename fails loudly. This is the
   main safety net for the namespace change.
2. `uv run ruff check` and `uv run ty check` — clean (zero-warnings rule).
3. `claude plugin validate plugins/sec-overlay` — passes.
4. Marketplace manifest description updated; `plugins/README.md`, root `README.md`,
   and `CHANGELOG.md` updated in the same commit as the code (governance).

## Process

- Work on branch `feat/port-sec-overlay`.
- Version stays `0.1.0` (no bump without user approval).
- User approves the merge into `main`.

## Risks and tradeoffs

- The namespace rename touches 179 files; it is mechanical but error-prone.
  Mitigation: the test suite, not inspection alone.
- Ported internal `docs/` carry dated development history and source-repo path
  references. If a doc-invariant test asserts on them, fix to keep the suite green.
- Not shipping semgrep rules is a coverage gap for anyone who does not supply their
  own ruleset. The bundled `smoke.yaml` scan still works out of the box.

## Out of scope

- Bumping the plugin version.
- Cosmetic renames of `{{HARNESS_ROOT}}`-style token names or the word "harness".
- Fetching or vendoring the semgrep-rules content.
