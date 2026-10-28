# plainspoken deep review — implementation plan

**Spec:** `docs/superpowers/specs/2026-10-28-plainspoken-deep-review-design.md` (approved 2026-10-28)
**Branch:** `feat/plainspoken-deep-review`
**Version:** 0.1.1 → 0.2.0
**Finish:** push, open a pull request, wait for checks, ask the user once before the merge.

## Plan decisions

| # | Topic | Decision |
|---|---|---|
| P1 | Commits | Four commits. Only C4 changes shipping files, so only C4 bumps the version (`feat` → minor → 0.2.0). |
| P2 | Smoke test | One `claude -p --plugin-dir` run of `/plainspoken:deep` before the push. |
| P3 | Finish | Pull request, checks green, then ask before the merge. |

## Hook facts that shape the commits

- `tests/`, `evals/`: not shipping files. A change there needs `plugins/plainspoken/CHANGELOG.md` and the folder `README.md`, and no version bump.
- Shipping files (`plugin.json`, `SKILL.md`, `commands/`, `skills/`, `agents/`, `references/`, their folder READMEs) bump the version in the same commit.
- C2 and C3 add their changelog lines under a new `## Unreleased` section. C4 renames it to `## 0.2.0 - 2026-10-28`.

## Commits

### C1 — `docs: add plainspoken deep review spec and plan`

Files: the spec, this plan, `docs/README.md` (2 rows), root `README.md` (docs inventory line), root `CHANGELOG.md`.

### C2 — `test(plainspoken): add failing tests for new lint keys`

Files: `tests/test_lint.py`, `tests/README.md`, `CHANGELOG.md`.

New tests. Each fails at C2 because `lint.py` does not report the key yet:

| # | Test | Asserts |
|---|---|---|
| 1 | `test_cluster_words_per_paragraph` | A paragraph with "harness" and "empower" reports paragraph 1 with both words. One cluster word alone reports nothing. |
| 2 | `test_cluster_words_count_paragraphs_separately` | One cluster word in each of two paragraphs reports nothing. |
| 3 | `test_density_words_need_two_hits_and_three_percent` | "significant" twice in 40 words is reported. Once in 30 words is not. Twice in 200 words is not. |
| 4 | `test_wordy_and_redundant_and_defense` | "due to the fact that", "past history", "needless to say" each appear under their key. |
| 5 | `test_social_breadth_cutoff_ack_reasoning` | One phrase per key: `social_openers`, `false_breadth`, `cutoff_phrases`, `acknowledgment_loops`, `reasoning_residue`. |
| 6 | `test_analogy_scaffolding_sentence_start_only` | "Imagine a gateway." flags. "You can imagine it." does not. |
| 7 | `test_curly_quotes_counted` | Two curly double quotes and one curly apostrophe give 3. |
| 8 | `test_emoji_lines_headings_and_bullets` | A heading with an emoji and a bullet with an emoji give 2. An emoji in a prose line does not count. |
| 9 | `test_new_keys_quiet_on_plain_text` | The existing plain paragraph still gives an empty `sweep`. |

Markdown stripping removes heading and list markers, so `emoji_lines` always reads the raw text, with or without `--raw`. Test 8 runs without `--raw` to prove this.

Run: `uv run --with pytest pytest -q`. Expected: 8 failed, the rest passed (test 9 passes at C2 and must keep passing).

### C3 — `test(plainspoken): add deep and severity eval cases`

Files: `evals/cases.json` (8 cases from spec section 8), `evals/README.md` (case count 19 → 27), `tests/test_evals.py` (`deep` added to the allowed modes), `tests/README.md`, `CHANGELOG.md`.

Run: pytest. The eval tests pass. The C2 lint tests still fail.

### C4 — `feat(plainspoken): add deep review and severity tiers`

All shipping changes in one commit:

| Area | Files |
|---|---|
| Lint | `scripts/lint.py` (spec 7.2), `references/tells.md` (spec 7.1), `scripts/README.md` |
| Skill | `SKILL.md` (spec 4 routing, deep row, under 200 lines), `references/severity.md` (new), `references/deep.md` (new), `references/rewrite.md` (spec 5.3-5.6), `references/review.md` (5.2), `references/brief.md` (5.8), `references/medium.md` (5.7), `references/README.md`, `skills/plainspoken/README.md` |
| Agents | `agents/structure-lens.md`, `fluff-lens.md`, `pattern-lens.md`, `flow-lens.md`, `agents/README.md` (spec 6.2) |
| Commands | `commands/deep.md` (new), `commands/brief.md` (description), `commands/README.md` |
| Plugin root | `.claude-plugin/plugin.json` → `0.2.0`, `CHANGELOG.md` (Unreleased → 0.2.0), `README.md` (modes table, deep, agents), `CLAUDE.md` (agents folder, severity single source), `NOTICE.md` (blader/humanizer and Wikipedia section) |

`NOTICE.md` addition: pattern names and the severity idea come from the user's anti-slop-editor 1.1.0, which draws on blader/humanizer (MIT, © 2025 Siqi Chen) and Wikipedia "Signs of AI writing". No text or example is copied. Include the blader/humanizer MIT license text from a fresh clone.

Run: pytest (all pass), ruff, `claude plugin validate .`, `wc -l SKILL.md` < 200.

## Build streams (agents, no git writes)

| Stream | Agent | Files |
|---|---|---|
| Lint | builder | `tests/test_lint.py` (red first), then `lint.py`, `tells.md`, `scripts/README.md` |
| Skill | builder | `SKILL.md`, all `references/*` except `tells.md`, `skills/plainspoken/README.md`, `commands/deep.md`, `commands/brief.md`, `commands/README.md` |
| Agents | builder | `agents/*.md` |
| Evals | builder | `evals/*`, `tests/test_evals.py` |

The orchestrator writes `tests/README.md`, `plugin.json`, `CHANGELOG.md`, `README.md`, `CLAUDE.md`, `NOTICE.md`, then reviews each stream against the spec and commits C2 to C4 in order.

Every stream keeps these rules:
- No example text from anti-slop-editor or blader/humanizer. Every "After" example contains no fact the "Before" lacks.
- No em dashes in new prose.
- Severity lists live only in `severity.md`.

## Final verification (before push)

1. `uv run --with pytest pytest -q`: all pass.
2. `uvx ruff check .` and `uvx ruff format --check .` in `plugins/plainspoken`: clean.
3. `claude plugin validate .`: passes.
4. `prek run --all-files`: passes.
5. `wc -l` on `SKILL.md` and plugin `CLAUDE.md`: under 200.
6. `rg` for anti-slop and humanizer example strings in `plugins/plainspoken` ("Catalonia", "Alamata", "Gallery 825", "Korattur", "bouncer at a nightclub", "six hours to forty minutes"): no hits.
7. Smoke test: `claude -p --plugin-dir plugins/plainspoken "/plainspoken:deep <sample>"` on a ~120-word sample with known chat residue, false breadth, and an orphaned list signal. Pass: findings from all four lenses, ranked P0 first, and the output stops at the rewrite question.
8. `git log main..HEAD --format='%G? %s'`: 4 signed commits.

## Push and pull request

1. Push. `gh pr create`, title `feat(plainspoken): add deep review and severity tiers`. The body has the summary, test evidence, smoke-test output, and the rejected items from spec 2.3. No AI attribution.
2. Wait for checks. Ask the user once before the merge.
