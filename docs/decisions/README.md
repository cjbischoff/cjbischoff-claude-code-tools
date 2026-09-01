# docs/decisions/

Project-level architecture decisions for this repository. One file per decision. A decision belongs
here when it affects more than the task that produced it: a shared contract, a new capability lane,
a tool or framework choice, or a rule a later session may need to reverse.

## Naming

`YYYY-MM-DD-{topic}.md`, kebab-case topic.

## Structure

Each file carries these sections, in this order:

1. `## Decision:` — one sentence.
2. `## Context` — what triggered the need to decide.
3. `## Alternatives considered` — each option with why it was rejected or selected.
4. `## Reasoning` — why the selected option won.
5. `## Trade-offs accepted` — what the choice gives up.
6. `## Supersedes` — the prior decision file this replaces, or `none`.

## Rules

- Add a row to [INDEX.md](INDEX.md) in the same commit that adds a decision file.
- Add a row to the `docs/README.md` contents table in the same commit, and name the decision in the
  `docs/decisions/` row of the root `README.md` inventory. The doc-update guard requires both files.
- Never delete a superseded decision file. The chain is the record.
- Read this folder before you make a decision in the same area.
- Global Claude Code configuration decisions live in `~/.claude/docs/decisions/`, not here.
