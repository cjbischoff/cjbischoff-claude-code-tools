# readme-keeper plugin — design

**Date:** 2026-10-28
**Branch:** `feat/add-readme-keeper-plugin`
**Status:** Draft for user review
**Version:** 0.1.0

## 1. Purpose

`readme-keeper` writes a README from the code and keeps it true as the code changes. Every fact in the README traces to a file in the repo. Hand-written text is never overwritten.

It has four jobs:

| Job | Writes? | Summary |
|---|---|---|
| `create` | yes, after approval | Build a README from the code. |
| `update` | yes, after approval | Refresh generated regions only. Text outside markers is never edited. |
| `check` | no | Mechanical drift report. Usable in CI. |
| `review` | no | Reader-rubric critique with severity and an optional score. |

## 2. Source review

### 2.1 Sources

| Source | License | Role |
|---|---|---|
| `~/.claude/skills/readme` (user's skill) | User's own work. It adapts Alexey Grigorev, "How to Write a Good README", and quotes 3 project READMEs in `examples.md`. | Base for `create`. All of its features come across. |
| `rushikeshsakharleofficial/readme-forge` @ `fd45d6d` | MIT, © 2026 Rushikesh Sakharle | Type routing, omit-empty-sections, "needs manual fill" list, fact-gated badges, lockfile install command, ask-before-overwrite, decorative image catalog |
| `povvo/claudikins-github-readme-for-perfectionists` @ `1787804` | MIT, © 2025 Ethan Lee | Fact report with file:line and confidence, missing-information list, section order by type, "time to joy" step count, "won't do" section, badge hygiene, web research of examples |
| `cajias/claude-skills` `plugins/dev` @ `53fe021` | MIT, © 2024 Claude Skills Contributors | Reader rubric (four questions, caveats first, trust signals), evaluate-only mode, tiered issues, structured fix plan, numeric rubric score |
| `tavva/ben-claude-plugins` `plugins/readme-generator` @ `7d4e1aa` | No LICENSE file. Ideas only, no text. | Depth tiers, sections by project type, machine-checkable checklist, TOC length threshold, `<details>` for long optional content |
| plainspoken 0.2.1 (this repo) | MIT parts from clarity (Addy Osmani) and work-humanizer (Pawel Huryn) | No-invention safeguards, prose-tell subset, severity tiers. Copied and adapted. No runtime dependency. |

**Copy rule (user decision):** text and examples from the MIT sources and from the user's readme skill may be copied. Each copied file is listed in `NOTICE.md` with its source and license. ben/readme-generator text is never copied, because a missing license grants no copy right.

### 2.2 Findings that shape the design

No reviewed repo has a working update mode. Three claim one, and they either do nothing (readme-forge `SKILL.md:18`) or rewrite the whole file (claudikins `pen-wielding/SKILL.md:280`). No repo verifies its claims mechanically. All four can produce invented facts: hardcoded "MIT" (ben `patterns.md:475`), placeholder badges (ben `patterns.md:483`), required metrics with no data (claudikins `style-guide.md:45`), and example output with invented claims (cajias `examples/readme-workflow.md:103-121`).

readme-keeper closes both gaps: markers for update, and a stdlib checker for claims.

### 2.3 Rejected

| Item | Source | Reason |
|---|---|---|
| Gemini brain-jam | claudikins | Sends a code summary to Google. Needs an MCP server. User excluded it. |
| Reading `~/.claude/history.jsonl` | claudikins | Reads outside the repo, across projects. |
| Committing without asking | claudikins | Breaks the diff-ask-write rule. |
| Self-scoring rewrite loop until score ≥ 85 | cajias | The model grades its own work. The score is kept as a report value only (D9). |
| Running `BINARY --help`, `npm install`, or other project code | readme-forge, cajias | The plugin never executes target code. |
| Creating a `LICENSE` file | readme-forge | A license is the owner's decision. |
| SEO keyword rules that require marketing phrases | readme-forge | Conflict with the no-invention rule. |
| Templates with sample facts (ripgrep flags, a Next.js stack, `/users` endpoints) | readme-forge | Leak into output as invented facts. Templates hold slot descriptions only. |
| Required metric in every feature line | claudikins | Forces invented numbers. |
| User config stored inside the plugin | cajias | Plugin updates overwrite it. Config lives in the target repo. |

## 3. Decisions from the interview

| # | Topic | Decision |
|---|---|---|
| D1 | Name | `readme-keeper` |
| D2 | Jobs | create, update, check, review |
| D3 | Update mechanism | Marker-delimited generated regions. Text outside markers is never edited. A first update on an unmarked README proposes markers as a diff. |
| D4 | Base | The user's readme skill, all create features, plus reviewed-repo features that fill gaps. |
| D5 | Isolation | No runtime dependency on plainspoken or any other plugin. Pieces are copied in. |
| D6 | Checker | Stdlib Python. Commands exist, paths and anchors exist, external links (opt-in), facts vs repo (license, badges, markers). |
| D7 | From plainspoken | No-invention safeguards, prose-tell subset, P0/P1/P2 severity. |
| D8 | Copying | MIT and user-owned text may be copied with attribution in `NOTICE.md`. ben text never. |
| D9 | Opt-in extras | Web research of example READMEs, decorative images, a 0-100 score in the review report. All off by default. |
| D10 | Invocation | Auto skill + `/readme-keeper:create`, `:update`, `:check`, `:review` + a CI workflow template. |
| D11 | Writes | Show the full diff and the "needs manual fill" list, stop, write only on yes. Never commit. `create` on an existing README refuses and suggests `update`. |
| D12 | Targets | Root `README.md` by default. Any README path. `check --all` walks every tracked `README.md`. |
| D13 | Old skill | After install, the user gets instructions for another session to retire `~/.claude/skills/readme`. |

## 4. Markers

```markdown
<!-- readme-keeper:start install -->
...generated content...
<!-- readme-keeper:end install -->
```

- Region ids: `badges`, `install`, `quickstart`, `commands`, `env`, `structure`, `license`, `toc`.
- Everything outside a region is hand-written and never edited by `update`.
- `update` regenerates the content of each region from the repo, then shows a diff.
- A region the user deleted stays deleted. `update` never re-adds a region on its own. It lists the region under "available regions" instead.
- An unmarked README: `update` proposes wrapping the sections that match a region id in markers. That proposal is a diff. Text is not changed in that step.
- The checker fails on an unpaired, nested, duplicated, or unknown marker.

## 5. Modes

### 5.1 create

1. **Refuse** if the target exists. Suggest `update`.
2. **Inspect** the repo (the readme skill's step 1, plus readme-forge's lockfile rule and claudikins's fact checklist): manifests, lockfiles, entry points, scripts, Makefile/justfile targets, `.env.example`, CI workflows, tests, LICENSE, Docker, `docs/`, an existing README in another location.
3. **Fact report** in chat: each claim, its `file:line` source, and High/Medium/Low confidence. A "Missing information" list holds what the code cannot answer (purpose in plain words, target user, hosted URL).
4. **Ask** the missing-information questions in one round. Each can be skipped.
5. **Classify** the project type (section 6) with a fixed precedence. **Pick depth**: minimal, standard, or full, from size and maturity (ben idea).
6. **Draft** from the type's reference. Include only sections the project earns. Generated facts go inside markers. Opening answers what it is, why it matters, how to start.
7. **Verify** with `check.py` against the draft. Fix every P0 before showing the diff.
8. **Show** the diff (the full new file), the fact report summary, and "Needs manual fill". Stop. Write only on yes.

### 5.2 update

1. Run `check.py` on the current README.
2. For each marked region, regenerate its content from the repo.
3. For an unmarked README, propose markers (section 4).
4. Show the diff and the reasons per region (which file changed). Stop. Write only on yes.

### 5.3 check

`check.py` only. No model judgment. Output: findings with severity, `README:line`, and the repo evidence. Exit codes in section 7.4.

### 5.4 review

1. Run `check.py`.
2. Apply the reader rubric (cajias, readme skill): what is it, does it work, can I run it, how is it built. Caveats first, trust signals, three readers (reviewer, hiring team, future self).
3. Report findings with P0/P1/P2, ranked, each with `README:line`, evidence, and a suggested fix that adds no invented fact.
4. With `--score`: add a 0-100 rubric score and its per-criterion breakdown. The score is never a loop target.

### 5.5 Opt-in extras

| Flag | Mode | Behavior |
|---|---|---|
| `--research` | create, review | WebSearch/WebFetch 3-7 READMEs of similar projects. Their content is data, never instructions. Borrow structure only, never facts. List the URLs in chat. |
| `--style fancy` | create, update | Add decorative images (typing-SVG banner, star-history, contrib.rocks, capsule-render) only when the facts allow: star-history and contrib.rocks need a public GitHub remote. Each image goes in the `badges` region. |
| `--score` | review | Section 5.4 step 4. |

## 6. Project types and references

| Type | Signals (in precedence order) | Reference |
|---|---|---|
| Claude Code plugin or marketplace | `.claude-plugin/plugin.json` or `marketplace.json` | `references/types/plugin.md` |
| AI/ML project | LLM or embedding dependencies, vector store, `eval/` or `evals/`, prompt files | `references/types/ai-ml.md` (the readme skill's 16-section framework) |
| Monorepo | workspaces, `pnpm-workspace.yaml`, multiple manifests | `references/types/monorepo.md` |
| CLI | `bin` in package.json, `[project.scripts]`, `[[bin]]`, `cmd/` in Go | `references/types/cli.md` |
| Service / API | web framework dependency plus a server entry point | `references/types/service.md` |
| Web app | frontend framework plus app entry | `references/types/web-app.md` |
| Library | default when a manifest exists | `references/types/library.md` |

The first matching row wins. Each reference gives section order, depth-tier rules, and slot descriptions. No reference contains sample facts.

Other references:

- `references/rubric.md`: the reader rubric, three readers, common mistakes (readme skill), caveats-first and trust signals (cajias), "won't do" (claudikins), score weights for `--score`.
- `references/examples.md`: the readme skill's annotated examples, with attribution.
- `references/badges.md`: fact-gated badge rules and the decorative image catalog for `--style fancy`.
- `references/safeguards.md`: adapted from plainspoken: invent nothing, keep certainty, source text is data, `[TK: question]` in chat only.
- `references/tells.md`: the prose-tell subset used by `check.py --prose`.

## 7. `check.py`

**Path:** `plugins/readme-keeper/skills/readme-keeper/scripts/check.py`. Python 3.11+ stdlib (`tomllib`). One file, so the CI template can copy it.

### 7.1 CLI

```bash
python3 check.py [README ...] [--all] [--root DIR] [--links] [--prose] [--json] [--strict]
```

- No path: `README.md` in `--root` (default: current directory).
- `--all`: every tracked `README.md` (`git ls-files`), or every `README.md` found when git is absent.
- `--links`: check external URLs (HEAD, then GET on 405; 10 s timeout; 4 parallel). Off by default.
- `--prose`: add the prose-tell findings.

### 7.2 Checks

| Check | Rule | Severity |
|---|---|---|
| Commands | A command in a shell code block (`npm run x`, `pnpm x`, `yarn x`, `make x`, `just x`, `uv run x`, `poetry run x`, `cargo run --bin x`, `go run ./x`) must match a script, target, entry point, or path in the repo. Unrecognized commands are skipped, never guessed. | P0 |
| Package manager | An install command uses the manager the lockfile shows (`package-lock.json` npm, `pnpm-lock.yaml` pnpm, `yarn.lock` yarn, `uv.lock` uv, `poetry.lock` poetry). | P1 |
| Paths (links) | A Markdown link or image source to a relative file must exist. | P0 |
| Paths (inline code) | An inline-code path is looked up in the README folder, the repo root, then by suffix against tracked files. Not found anywhere: "unresolved path, check intent". Changed after the dogfood run (2026-10-29): 164 of 201 inline-code paths in this repo named runtime outputs, other repos' files, or ignored folders, not broken links. | P2 |
| Anchors | An in-page `#anchor` must match a heading slug (GitHub rules). | P1 |
| External links | `--links` only. A 4xx is P1. A timeout or 5xx is P2 (flaky). | P1/P2 |
| License | A license name in the README must match the `LICENSE` file or manifest license field. A README license with no license source is P0. | P0 |
| Badges | A CI badge needs a matching workflow file. A registry badge needs a non-private manifest with a name. A coverage badge needs a coverage config. | P1 |
| Markers | Unpaired, nested, duplicate, or unknown region ids. | P0 |
| Prose | `--prose` only. Em dashes, stock AI words, marketing words, filler transitions. | P2 |

### 7.3 Output

Human report by default. `--json` gives `{"files": [{"path", "findings": [{"check", "severity", "line", "message", "evidence"}]}]}`. No score in `check.py`.

### 7.4 Exit codes

- 0: no P0 findings (and no P1 with `--strict`).
- 1: at least one P0 (or P1 with `--strict`).
- 2: usage error or unreadable file.

## 8. CI template

`templates/readme-check.yml`: a GitHub Actions workflow that runs `python3 .github/scripts/readme_check.py --all` on pull requests, offline, with SHA-pinned `actions/checkout` and `persist-credentials: false`.

`/readme-keeper:check --install-ci` copies `check.py` to `.github/scripts/readme_check.py` and the template to `.github/workflows/readme-check.yml` in the target repo, as a diff the user approves. The copy is pinned to the plugin version. It runs without the plugin. The checkout pin is looked up at build time.

## 9. Commands and skill

| Command | Behavior |
|---|---|
| `/readme-keeper:create [path] [--depth minimal\|standard\|full] [--research] [--style fancy]` | Section 5.1 |
| `/readme-keeper:update [path] [--style fancy]` | Section 5.2 |
| `/readme-keeper:check [path\|--all] [--links] [--prose] [--strict] [--install-ci]` | Section 5.3, 8 |
| `/readme-keeper:review [path] [--score] [--research]` | Section 5.4 |

The skill triggers on "write a README", "create/update/improve the README", "the README is out of date", "check the README", "document this project". `SKILL.md` stays under 200 lines and loads only the references the mode needs.

## 10. Plugin layout

```text
plugins/readme-keeper/
├── .claude-plugin/plugin.json
├── README.md  CHANGELOG.md  CLAUDE.md  NOTICE.md
├── commands/  create.md update.md check.md review.md README.md
├── templates/ readme-check.yml README.md
├── skills/readme-keeper/
│   ├── SKILL.md  README.md
│   ├── references/  rubric.md examples.md badges.md safeguards.md tells.md README.md
│   │   └── types/   plugin.md ai-ml.md monorepo.md cli.md service.md web-app.md library.md README.md
│   └── scripts/    check.py README.md
├── tests/  test_check.py  fixtures/<repo-shapes>/  README.md
└── evals/  cases.json JUDGE.md README.md
```

No `agents/` folder.

## 11. Tests and evals

- `tests/test_check.py`: TDD against fixture repos (Node npm, Node pnpm workspace, Python uv, Python poetry, Make, just, Go, Rust, Claude plugin). One test per check and severity, the marker rules, `--all`, `--json` shape, exit codes, and a hostile-input time limit. `--links` is tested with a local `http.server` on 127.0.0.1, never the internet.
- `evals/cases.json`: create refuses an existing README; create invents no license, badge, or metric; update leaves text outside markers byte-identical; update does not re-add a deleted region; check is read-only; review gives severity and no rewrite; `--research` borrows no facts; `--style fancy` adds no star-history without a GitHub remote.

## 12. Verification before merge

pytest, ruff, `claude plugin validate .`, `prek run --all-files`, `SKILL.md` and `CLAUDE.md` under 200 lines, and one smoke test: `claude -p --plugin-dir plugins/readme-keeper "/readme-keeper:check --all"` on this repo, plus `/readme-keeper:update` on a copy of a fixture to confirm the diff-and-stop behavior.

## 13. Out of scope

- Running project code or install commands.
- Writing `LICENSE`, `CONTRIBUTING`, or `CHANGELOG` files.
- Generating screenshots or GIFs.
- Committing or pushing.
- Non-English READMEs.
