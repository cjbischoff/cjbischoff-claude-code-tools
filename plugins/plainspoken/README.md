# plainspoken

Draft, rewrite, review, brief, and lint prose so it is specific, useful, and the writer's own,
without inventing facts.

## Install

```text
/plugin marketplace add cjbischoff/cjbischoff-claude-code-tools
/plugin install plainspoken@cjbischoff-claude-code-tools
```

## Prerequisites

None for the skill. The `lint` mode runs a stdlib-only script and needs Python 3.10 or later on
`PATH`.

## Quick start

```text
/plainspoken:rewrite draft.md
/plainspoken:brief <paste meeting notes>
```

Or ask in plain words ("rewrite this", "make this a BLUF email to my VP"). The skill picks the
mode.

## Modes

| Mode | Command | What it does |
|---|---|---|
| `interview` | `/plainspoken:interview <topic>` | Asks for your unorganized take, then at most 5 follow-up questions, then writes from your words |
| `rewrite` | `/plainspoken:rewrite <file or text>` | Fixes substance first, then AI tells and rhythm. Keeps every fact at the same certainty |
| `review` | `/plainspoken:review <file or text>` | Critiques the piece. Never rewrites it or changes a file |
| `brief` | `/plainspoken:brief <file or text>` | Reformats into a BLUF email, 3-sentence executive summary, action items, or a 75-word message |
| `lint` | `/plainspoken:lint <file>` | Runs the stdlib diagnostic script. Reports, never edits |

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

A file path means the skill edits the file in place and puts its notes in chat. Use git or your
editor to undo.

## What it will not do

- Invent a fact, number, quote, example, or personal experience. A gap becomes `[TK: question]`.
- Promise that text will pass an AI detector.
- Add fake typos, slang, or stories to sound human.

## Development

Maintainer commands are in [`CLAUDE.md`](CLAUDE.md). `ruff.toml` sets the Python line length to 100.

## Attribution

plainspoken adapts two MIT-licensed skills: [clarity](https://github.com/addyosmani/clarity) by
Addy Osmani and [work-humanizer](https://github.com/phuryn/work-humanizer) by Pawel Huryn. See
[`NOTICE.md`](NOTICE.md) for both licenses and the list of adapted files.

## More

| To understand… | Read |
|-----------------|------|
| What changed between releases | [`CHANGELOG.md`](CHANGELOG.md) |
| The skill in depth | [`skills/plainspoken/SKILL.md`](skills/plainspoken/SKILL.md) |
| How to develop and test it | [`CLAUDE.md`](CLAUDE.md) |
