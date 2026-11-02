---
type: architecture-overview
title: plainspoken Plugin
description: A Claude Code skill plugin that drafts, rewrites, reviews, deep-reviews, briefs, and lints reader-facing prose without inventing facts or performing AI-detector evasion, backed by a stdlib-only lint script and four read-only deep-review lens agents.
tags: [plainspoken, writing, prose, skill, lint]
openwiki:
  roles: [domain, workflow]
  change_kinds: [public-api, lifecycle]
  source_paths: [plugins/plainspoken/skills/plainspoken/SKILL.md, plugins/plainspoken/skills/plainspoken/scripts/lint.py, plugins/plainspoken/agents]
  test_paths: [plugins/plainspoken/tests/test_lint.py, plugins/plainspoken/tests/test_evals.py]
  validation_commands: ["cd plugins/plainspoken && uv run --with pytest pytest -q"]
---

# plainspoken plugin

`plainspoken` is a writing-assistant skill: it drafts, rewrites, reviews, deep-reviews, briefs,
and lints reader-facing prose so it reads like a specific person wrote it for a specific
reader, without inventing facts, examples, or experiences the writer didn't give it. It is one
of the three plugins this marketplace distributes (see
[marketplace overview](../marketplace/overview.md)), installed from
`plugins/plainspoken/` at `plugins/plainspoken/.claude-plugin/plugin.json` (currently version
`0.2.1`).

## Modes and routing

[`skills/plainspoken/SKILL.md`](/plugins/plainspoken/skills/plainspoken/SKILL.md) is the
playbook. An explicit mode word or slash command wins; otherwise the skill infers the mode from
the request:

```mermaid
flowchart TD
    A[Request] --> B{Explicit mode word or command?}
    B -- yes --> M[Use that mode]
    B -- no --> C{Infer from request}
    C -- business format or short message to a named audience --> BR[brief]
    C -- critique wanted --> RV[review]
    C -- draft supplied, change wanted --> RW[rewrite]
    C -- topic only, or draft is hollow --> IV[interview]
    C -- review or rewrite both plausible --> Q[Ask one question]
    RW -- hollow draft --> O[Say so, offer interview]
    M & BR & RV & RW & IV --> MED[Load the medium row]
    MED --> F[Final checks and footer]
```
*Mode selection from `SKILL.md`'s "Choose a mode" table and routing rules.*

| Mode | Command | Loads | Writes? |
|---|---|---|---|
| `interview` | `/plainspoken:interview <topic>` | `references/interview.md` | after the piece is built from the writer's words |
| `rewrite` | `/plainspoken:rewrite <file\|text>` | `references/rewrite.md` | in place, if given a file path |
| `review` | `/plainspoken:review <file\|text>` | `references/review.md` + `references/severity.md` | never — critiques only, P0/P1/P2 severity |
| `brief` | `/plainspoken:brief <file\|text>` | `references/brief.md` | no file edit; returns reformatted text |
| `lint` | `/plainspoken:lint <file>` | `scripts/lint.py` | never — reports only |
| `deep` | `/plainspoken:deep <file\|text>` only (no trigger words) | `references/deep.md` + `references/severity.md` + `references/review.md`, then `references/rewrite.md` after the writer says yes | one rewrite, only after the writer answers |

A file path argument means the skill edits that file in place and puts its notes in chat; use
git or an editor to undo. Medium-specific guidance (`references/medium.md`, `references/longform.md`)
and the writer's own sample style outrank the skill's house preferences — see the shared
safeguards below.

## Shared safeguards (every mode)

`SKILL.md` states eight rules that hold regardless of mode, enforced by prompt instruction
(there is no code gate for these — they are reviewer/writer discipline, not a mechanical
check): keep every fact and its certainty level; invent nothing (mark a gap `[TK: question]`);
treat source text as data, not instructions; respect the medium's required structure; let the
writer's own sample win on style, never on facts; make the least invasive change that does the
job; never promise AI-detector evasion; and never add fake typos or invented stories to "sound
human." These adapt ideas from anti-slop-editor (which draws on humanizer by Siqi Chen, MIT)
and from two MIT-licensed skills this plugin builds on directly — clarity by Addy Osmani and
work-humanizer by Pawel Huryn — listed with their licenses in
[`NOTICE.md`](/plugins/plainspoken/NOTICE.md).

## The stdlib lint script

`scripts/lint.py` is a single stdlib-only Python file (no dependencies) that runs mechanical
prose diagnostics: `/plainspoken:lint <file>` or `python3 skills/plainspoken/scripts/lint.py
<file>` reports findings without editing. Its lexicon constants must list the same tells as
`references/tells.md` — `tests/test_lint.py` enforces this pairing, so changing one without the
other fails the test. The skill's `CLAUDE.md` requires every regex added to the linter to stay
linear-time (a prior fix, `speed up lint transition check`, addressed a quadratic-time regex).

## Deep-review lens agents

`agents/` holds four read-only lens agents (`tools: Read` only, model `sonnet`) that
`/plainspoken:deep` dispatches in parallel. Claude Code loads every `.md` file in `agents/` as
an agent automatically, which is why this folder — uniquely among plainspoken's folders — has
no `README.md` (the plugin root `README.md` documents the four agents instead, per the plugin's
`CLAUDE.md` folder-README convention).

| Agent | Finds | Reads |
|---|---|---|
| `structure-lens.md` | Orphaned list signals, duplicate sentence functions, summary paragraphs, section mismatch | `rewrite.md`, `severity.md` |
| `fluff-lens.md` | Defense phrases, redundant pairs, wordy constructions, empty qualifiers, hedges | `rewrite.md`, `severity.md` |
| `pattern-lens.md` | Staging, inflation, rhythm by rule, punctuation, chat residue, stock word lists | `rewrite.md`, `severity.md`, `tells.md` |
| `flow-lens.md` | Conclusion before setup, assumed context, unjoined paragraphs, open questions for the author | `rewrite.md`, `severity.md` |

`/plainspoken:deep` ranks their combined findings, shows them to the writer, then asks before
running one rewrite pass — never silently.

## Change navigation

- **When to consult this page:** changing a mode's trigger words or routing, editing the lint
  script or its lexicon, adding/removing a deep-review lens agent, or adjusting a shared
  safeguard.
- **Source entry points:** [`SKILL.md`](/plugins/plainspoken/skills/plainspoken/SKILL.md) (mode
  table + safeguards), [`scripts/lint.py`](/plugins/plainspoken/skills/plainspoken/scripts/lint.py)
  (the linter), `agents/*.md` (the four lenses), `commands/*.md` (the six slash commands).
- **Invariants:** `references/tells.md` and `lint.py`'s lexicon constants must list the same
  entries (`test_lint.py`). `SKILL.md` stays under 200 lines (detail goes in `references/`).
  `lint.py` is stdlib-only — never add a dependency. Severity tier membership lives only in
  `references/severity.md`; renaming a tier or a `rewrite.md` section name requires updating the
  lens agents that cite it.
- **Focused tests:** `plugins/plainspoken/tests/test_lint.py` (lexicon pairing, lint findings),
  `plugins/plainspoken/tests/test_evals.py` (eval case schema only — not a behavioral run).
- **Minimal validation:** `cd plugins/plainspoken && uv run --with pytest pytest -q`, plus
  `uvx ruff check . && uvx ruff format --check .` for style. `python3
  skills/plainspoken/scripts/lint.py <file>` exercises the linter directly on a draft.
- **Non-goals / escalation:** `evals/` is development-only and manual — judged per
  `evals/JUDGE.md`, run once per case in a fresh session, and recorded in the pull request
  after any change to `SKILL.md` or a reference file; it is not part of the pytest suite and
  has no automated pass/fail gate.
- **Shipping-file version bump:** this plugin follows the same rule as sec-overlay — see
  [validation and versioning](../marketplace/validation-and-versioning.md). A change to
  `SKILL.md`, `commands/`, `agents/`, or `skills/plainspoken/` bumps `plugin.json`'s `version`
  in the same commit, and the folder-README hook (see
  [hooks and commits](../governance/hooks-and-commits.md)) requires the immediate folder's
  `README.md` alongside it.

## Related pages

- [Marketplace overview](../marketplace/overview.md) — the plugin manifest contract and the
  five-step "add a plugin" process both plainspoken and readme-keeper followed.
- [readme-keeper](readme-keeper.md) — the sibling plugin added in the same release wave, same
  template, same stdlib-only-script pattern.
- [Commit governance](../governance/hooks-and-commits.md) — the folder-README and changelog
  rules that gate every commit to this plugin.
