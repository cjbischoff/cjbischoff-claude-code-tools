# readme-keeper plugin — implementation plan

**Spec:** `docs/superpowers/specs/2026-10-28-readme-keeper-plugin-design.md` (approved 2026-10-28)
**Branch:** `feat/add-readme-keeper-plugin`
**Version:** 0.1.0, held on every commit of this branch
**Finish:** push, open a pull request, wait for checks, ask the user once before the merge.

## Plan decisions

| # | Topic | Decision |
|---|---|---|
| P1 | Version | Hold `0.1.0` across the branch. No user has installed the plugin. Strict bumps start after the first merge. The pull request records the ruling. |
| P2 | Dogfood | The smoke test runs `check --all` on this repo. The findings go into the pull request body. No README edits here. |
| P3 | Smoke tests | Two real sessions: `check --all` on this repo, and `update` on a fixture copy to confirm the diff-and-stop behavior. |
| P4 | Finish | Pull request, green checks, then ask before the merge. |

## Hook facts that shape the commits

- A file under `plugins/readme-keeper/` needs the plugin `CHANGELOG.md` in the same commit.
- A file whose folder has a tracked `README.md` needs that `README.md` in the same commit. A folder README that a later commit must change gets committed in a partial form first, then grows.
- A repo-level file needs root `README.md` and `CHANGELOG.md`. A file under `docs/` also needs `docs/README.md`.

## Commits

| # | Message | Files |
|---|---|---|
| C1 | `docs: add readme-keeper spec and plan` | spec, plan, `docs/README.md`, root `README.md`, root `CHANGELOG.md` |
| C2 | `chore(readme-keeper): scaffold plugin from template` | `plugin.json`, `README.md`, `CHANGELOG.md`, `CLAUDE.md`, `NOTICE.md` |
| C3 | `test(readme-keeper): add failing checker tests` | `tests/test_check.py`, `tests/fixtures/**`, `tests/README.md`, `references/tells.md`, partial `references/README.md`, `CHANGELOG.md` |
| C4 | `feat(readme-keeper): add stdlib README checker` | `scripts/check.py`, `scripts/README.md`, `ruff.toml`, `CHANGELOG.md` |
| C5 | `feat(readme-keeper): add skill and references` | `SKILL.md`, skill `README.md`, `references/*.md`, `references/types/*.md`, full `references/README.md`, `CHANGELOG.md` |
| C6 | `feat(readme-keeper): add commands and CI template` | `commands/*.md`, `templates/readme-check.yml`, `templates/README.md`, `CHANGELOG.md` |
| C7 | `test(readme-keeper): add eval cases` | `evals/*`, `tests/test_evals.py`, `tests/README.md`, `CHANGELOG.md` |
| C8 | `feat: register readme-keeper in marketplace` | `.claude-plugin/marketplace.json`, root `README.md`, root `CHANGELOG.md` |
| C9 | `chore: add readme-keeper test workflow` | `.github/workflows/readme-keeper-tests.yml`, root `README.md`, root `CHANGELOG.md` |

## C3 test list (all fail at C3: `check.py` does not exist)

Fixture repos under `tests/fixtures/`: `node-npm`, `node-pnpm-workspace`, `py-uv`, `py-poetry`, `make`, `just`, `go`, `rust`, `claude-plugin`. Each has a manifest, a lockfile where relevant, and one or more `README.md` files with planted faults.

| Group | Tests |
|---|---|
| Commands | known npm script passes; unknown npm script is P0; make target; just recipe; `uv run` entry point; `poetry run` script; `cargo run --bin`; `go run ./path`; unrecognized command skipped |
| Package manager | `npm install` with a `pnpm-lock.yaml` is P1; matching manager passes |
| Paths | missing relative link is P0; existing path passes; URL-encoded path; path inside inline code |
| Anchors | GitHub slug rules (case, punctuation, duplicates get `-1`); missing anchor is P1 |
| License | README "MIT" vs `LICENSE` Apache-2.0 is P0; README license with no license file or field is P0; match passes |
| Badges | CI badge with no workflow file is P1; registry badge with private manifest is P1; coverage badge with no coverage config is P1 |
| Markers | unpaired, nested, duplicate, unknown id are each P0; well-formed passes |
| Links | `--links` against a local `http.server` on 127.0.0.1: 404 is P1, 200 passes; links skipped without the flag |
| Prose | `--prose` flags an em dash and a stock word as P2; off by default |
| CLI | `--all` finds every README in a fixture; `--json` shape; exit codes 0, 1, 2; `--strict` turns P1 into exit 1 |
| Sync | every `tells.md` `Entries:` item is in the script lexicon |
| Safety | hostile input (80,000 characters of `[`, `<!--`, backticks) finishes in under 1.5 s |

## Build streams (agents, no git writes)

| Stream | Agent | Files |
|---|---|---|
| Checker | builder | `tests/test_check.py`, `tests/fixtures/**`, `references/tells.md`, then `scripts/check.py`, `scripts/README.md` (TDD: red first) |
| Skill | builder | `SKILL.md`, skill `README.md`, `references/{rubric,examples,badges,safeguards}.md`, `references/types/*.md`, `references/README.md` |
| Commands + CI | builder | `commands/*.md`, `commands/README.md`, `templates/readme-check.yml`, `templates/README.md` |
| Evals | builder | `evals/*`, `tests/test_evals.py` |

The orchestrator writes the plugin-root files, `tests/README.md`, the marketplace entry, and the repo workflow. It reviews each stream against the spec and commits C2 to C9 in order.

Rules for every stream:
- Copy only from the user's readme skill and the MIT sources. Never copy text from ben/readme-generator.
- Record every copied or adapted file for `NOTICE.md`: target file, source repo, source file, license.
- No sample facts in any template or type reference.
- No em dashes in new prose.
- Every regex in `check.py` is linear-time.

## Final verification (before push)

1. `uv run --with pytest pytest -q` in `plugins/readme-keeper`: all pass.
2. `uvx ruff check .` and `uvx ruff format --check .`: clean.
3. `claude plugin validate .`: passes (expected warnings only: plugin-root `CLAUDE.md`, `commands/README.md`).
4. `prek run --all-files`: passes.
5. `SKILL.md` and plugin `CLAUDE.md` under 200 lines.
6. `rg` for ben/readme-generator distinctive strings in `plugins/readme-keeper`: no hits.
7. Smoke 1: `claude -p --plugin-dir plugins/readme-keeper "/readme-keeper:check --all"` in this repo. Record the findings.
8. Smoke 2: copy one fixture to the scratchpad, run `/readme-keeper:update` on it with `claude -p`. Pass: the output shows a diff and stops at the question, and the file on disk is byte-identical afterwards.
9. `git log main..HEAD --format='%G? %s'`: 9 signed commits.

## Push and pull request

Title `feat: add readme-keeper plugin`. Body: summary, sources and licenses, test evidence, both smoke-test results, the dogfood findings, the version ruling. No AI attribution. Then wait for checks and ask before the merge.

## After merge

Write instructions for another session to retire `~/.claude/skills/readme` (D13): trash the folder, update `~/.claude/CLAUDE.md` and the inventory docs, add a decision record.
