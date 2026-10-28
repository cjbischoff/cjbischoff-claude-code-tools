# plainspoken plugin — implementation plan

**Spec:** `docs/superpowers/specs/2026-10-28-plainspoken-plugin-design.md` (approved 2026-10-28)
**Branch:** `feat/add-plainspoken-plugin`
**Finish:** push the branch and open a pull request. Do not merge.

## Plan decisions

| # | Topic | Decision |
|---|---|---|
| P1 | Commits | Small commits, one logical change each, all signed, each passes the prek hooks. |
| P2 | Diagrams | No archify, no oh-my-mermaid. The spec's Mermaid flowchart goes inline in the plugin README. |
| P3 | CI | New workflow `.github/workflows/plainspoken-tests.yml`. It runs pytest when `plugins/plainspoken/**` changes. |
| P4 | Finish | Push and open a pull request. The user waits for CodeRabbit and merges. |

## Ruling: version stays 0.1.0 on this branch

The governance rule bumps a plugin version for each commit that changes a shipping file. That rule protects installed users. `plainspoken` has no installed users until the first merge, so `0.1.0` was never released. All commits on this branch keep `0.1.0`, and the plugin `CHANGELOG.md` has one `0.1.0` entry that grows with each commit. The pull request body states this ruling, so a CodeRabbit "version not bumped" warning has a recorded answer.

## Hook facts that shape the commits

- A file under `docs/` requires `docs/README.md` in the same commit.
- A repo-level file requires root `README.md` and `CHANGELOG.md`.
- A file under `plugins/<name>/` requires `plugins/<name>/CHANGELOG.md`.
- A file whose folder has a tracked `README.md` requires that `README.md`. Each new folder therefore gets its README in the commit that creates the folder.
- The commit summary is lowercase, imperative, and under 50 characters.

## Commits

### C1 — `docs: add plainspoken spec and plan`

Files: the spec, this plan, `docs/README.md` (2 rows), root `README.md` (artifact inventory line for `docs/`), root `CHANGELOG.md`.

Check: `prek run` passes.

### C2 — `chore(plainspoken): scaffold plugin from template`

Copy `docs/templates/plugin/` to `plugins/plainspoken/` and fill every placeholder.

| File | Content |
|---|---|
| `.claude-plugin/plugin.json` | name `plainspoken`, the spec description, version `0.1.0` |
| `README.md` | install, prerequisites (none for the skill, Python 3 for `lint`), quick start, the mode table, the Mermaid flowchart, attribution to clarity |
| `CHANGELOG.md` | `## 0.1.0 - 2026-10-28` with an Added list |
| `CLAUDE.md` | maintainer manual: test command, eval run, folder-README rule, the version ruling |
| `NOTICE.md` | clarity MIT license text and copyright line, copied from the clarity repo `LICENSE`, plus a list of the adapted files |

Delete the template `skills/skill-name/` copy. C5 creates the real skill folder.

Check: `claude plugin validate .` passes. (The plugin is not in `marketplace.json` until C8, so this checks the manifest only.)

### C3 — `test(plainspoken): add failing lint tests`

Files: `plugins/plainspoken/tests/test_lint.py`, `tests/README.md`, `skills/plainspoken/references/tells.md` (the merged lexicon, which the sync test reads), `references/README.md`, `CHANGELOG.md`.

`tells.md` merges the work-humanizer lists and the clarity lexicons (`LEXIS`, `CHATBOT`, `CLOSERS`, `OPENER_PHRASES`, `SIGNPOSTS`) into one file. Each list has a heading and comma-separated entries, so that a test can parse it.

Tests (all fail with `ModuleNotFoundError` at this commit):

| # | Test | Asserts |
|---|---|---|
| 1 | `test_strips_markdown_by_default` | frontmatter, fenced code, inline code, tables, URLs, and HTML comments do not count |
| 2 | `test_raw_keeps_markdown` | `--raw` counts text inside a code fence |
| 3 | `test_counts_dashes_and_semicolons` | em dash, spaced en dash, `--`, and `;` counts |
| 4 | `test_flags_stock_words_and_marketing` | `delve`, `seamless`, and one AI phrase appear in `sweep` |
| 5 | `test_transition_only_at_sentence_start` | "However, x" flags. "x, however, y" does not. |
| 6 | `test_pause_and_point_and_closers` | "Here's the thing:" and "The bottom line" flag |
| 7 | `test_bold_label_and_exclamations` | `**Speed.**` at line start and `!` counts |
| 8 | `test_uniform_band_flagged` | 6 sentences of 12-14 words report the band as uniform |
| 9 | `test_json_has_all_groups` | `--json` keys: `size`, `cadence`, `density`, `high_signal_clusters`, `look_here`, `sweep` |
| 10 | `test_no_score_or_verdict` | no key named `score`, `verdict`, or `risk` at any depth |
| 11 | `test_stdin_dash` | `-` reads stdin |
| 12 | `test_missing_file_exits_2` | exit code 2 and a message on stderr |
| 13 | `test_tells_md_in_sync` | each entry in each `tells.md` list is in the script lexicon |
| 14 | `test_plain_human_text_is_quiet` | a short plain paragraph gives an empty `sweep` |

The tests call the script with `subprocess` and `sys.executable`, so they test the real CLI.

Run: `cd plugins/plainspoken && uv run --with pytest pytest -q`. Expected: 14 failures.

### C4 — `feat(plainspoken): add merged lint script`

Files: `skills/plainspoken/scripts/lint.py`, `scripts/README.md`, `CHANGELOG.md`.

Build `lint.py` from clarity `prose_stats.py` (metrics and report) and `strip_markdown.py` (as a `strip()` function), then add the work-humanizer `check.py` sweep as the `sweep` group. Stdlib only. Full Google-style docstrings. Keep clarity's "no composite score" reason in the module docstring.

Run: pytest, expected 14 passed. Also `uvx ruff check` and `uvx ruff format --check` on `lint.py` and the tests.

### C5 — `feat(plainspoken): add skill and mode references`

Files under `skills/plainspoken/`: `SKILL.md`, `README.md`, and in `references/`: `interview.md`, `rewrite.md`, `review.md`, `brief.md`, `medium.md`, `longform.md`, plus `references/README.md` and `CHANGELOG.md`.

| Reference | Built from |
|---|---|
| `interview.md` | clarity `interview.md` + work-humanizer interview and notes sections, merged per spec 5.1 |
| `rewrite.md` | work-humanizer rewrite steps + tells A-G + "sound like a person" + final checks, with clarity `edit.md` diagnosis order and pattern names (spec 5.2) |
| `review.md` | clarity `review.md`, pattern names point to `rewrite.md` and `tells.md` |
| `brief.md` | brief-sharp formats and rules, changed per spec 5.4 |
| `medium.md`, `longform.md` | clarity, adapted only where spec section 4 resolves a conflict |

`SKILL.md` stays under 200 lines. It holds the frontmatter, the mode table and routing, the 8 safeguards, the "establish the job" block, the footer table, the STE100 sentence, and the final check. The frontmatter `description` names all five modes and the trigger words.

Check: `wc -l SKILL.md` is under 200. Run `lint.py` on `SKILL.md` as a smoke test. The output is for information only and does not gate.

### C6 — `feat(plainspoken): add slash commands`

Files: `commands/interview.md`, `rewrite.md`, `review.md`, `brief.md`, `lint.md`, `commands/README.md`, `CHANGELOG.md`.

Each command has frontmatter (`description`, `argument-hint`) and one body line: "Use the `plainspoken` skill in <mode> mode on: $ARGUMENTS", plus the mode's one hard constraint (for example, review: "Do not rewrite and do not change any file"). `lint.md` gives the script path as `${CLAUDE_PLUGIN_ROOT}/skills/plainspoken/scripts/lint.py`.

Check: `claude plugin validate .`.

### C7 — `test(plainspoken): add eval cases and judge`

Files: `evals/cases.json`, `evals/JUDGE.md`, `evals/README.md`, `CHANGELOG.md`.

Copy clarity's 11 cases (renamed from clarity to plainspoken where the text names the skill) and add the 6 cases in spec section 9. `evals/README.md` gives the manual run steps. Add a pytest test that `cases.json` parses and that each case has `id`, `mode`, `prompt`, `input`, `requirements`, and unique ids, with `mode` in the 5 modes.

Run: pytest, expected 15 passed.

### C8 — `feat: register plainspoken in marketplace`

Files: `.claude-plugin/marketplace.json`, root `README.md` (Plugins list, Development command, artifact inventory rows), root `CHANGELOG.md`.

Check: `claude plugin validate .`.

### C9 — `chore: add plainspoken test workflow`

Files: `.github/workflows/plainspoken-tests.yml`, root `README.md` (inventory row), root `CHANGELOG.md`.

Copy the shape of `sec-overlay-tests.yml`: `pull_request` on `main`, `paths: plugins/plainspoken/**` and the workflow file, `permissions: contents: read`, concurrency group, `actions/checkout` with `persist-credentials: false`. Before pinning, look up the current `actions/checkout` release SHA with `gh api`. Reuse the pin from `sec-overlay-tests.yml` only if it is still the latest release. Install uv with the official script, then run `uv run --with pytest pytest -q` in `plugins/plainspoken`.

Check: `prek run`. Lint the YAML with `actionlint` if it is installed. If it is not, say so in the pull request.

## Final verification (before push)

1. `cd plugins/plainspoken && uv run --with pytest pytest -q`: all pass.
2. `uvx ruff check plugins/plainspoken` and `uvx ruff format --check plugins/plainspoken`: clean.
3. `claude plugin validate .`: passes.
4. `prek run --all-files`: passes.
5. `wc -l` on every new `CLAUDE.md` and `SKILL.md`: under 200.
6. `git log main..HEAD --format='%G? %s'`: 9 commits, each signed (`G`).
7. Smoke test: run `lint.py` on the spec file, then on stdin.

## Push and pull request

1. `git push -u origin feat/add-plainspoken-plugin`.
2. `gh pr create` with title `feat: add plainspoken writing plugin`. The body has the summary, the test evidence from the final verification, the version ruling, and a note that model evals are manual. No AI attribution.
3. Stop. Report the pull request URL.

## After merge (not part of this plan)

Spec section 10: install, check, retire the two global skills, update `~/.claude/CLAUDE.md`, add the superseding decision record. Each step needs user confirmation at that time.
