# cjbischoff-claude-code-tools

Claude Code plugin marketplace.

## Directory Guide

Each folder below has its own README.md describing what it holds, its naming convention, and who writes to it. A commit that changes a tracked file inside one of these folders must update that folder's README.md in the same commit.

| Folder | Purpose |
|--------|---------|
| `plugins/` | One directory per distributed plugin |
| `scripts/` | Repo-level tooling (git hook scripts) |
| `docs/` | Design specs and planning documents |

## Artifact inventory

| Path | Purpose |
|------|---------|
| `.claude-plugin/marketplace.json` | Marketplace manifest; lists all plugins |
| `plugins/sec-overlay/.claude-plugin/plugin.json` | sec-overlay plugin manifest (v0.1.0) |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook: agentic security-audit harness |
| `plugins/sec-overlay/skills/sec-overlay/helpers/` | Python core (`sec_overlay` package) that runs tools and enforces gates |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | LLM subagent prompts for the investigate/validate/patch phases |
| `docs/superpowers/specs/2026-08-11-port-sec-overlay-design.md` | Design for porting the sec-harness skill into the sec-overlay plugin |
| `docs/superpowers/plans/2026-08-11-port-sec-overlay.md` | Task-by-task implementation plan for the sec-overlay port |
| `docs/superpowers/specs/2026-08-11-sec-overlay-kb-redesign-design.md` | Design for porting upstream's KB doc/diagram redesign into sec-overlay |
| `.pre-commit-config.yaml` | prek hook config: doc-update guard + commit message check |
| `scripts/hooks/` | Hook scripts that enforce commit governance |
| `CHANGELOG.md` | Common Changelog; one entry per functionality commit |

## Commit governance

- Direct commits to `main` are blocked by a pre-commit hook.
- Branch naming: `<type>/<short-kebab-description>` (e.g. `feat/poc-reproducer-retry`).
- Commit messages: Conventional Commits, summary under 50 chars, body wrapped at 72.
- Every commit that changes tracked files must update `README.md` and add a `CHANGELOG.md` entry in the same commit — hooks enforce this.
- Run `prek install` once after cloning to activate the hooks.

## Status

- Ported the sec-harness skill into the sec-overlay plugin (branch `feat/port-sec-overlay`).
- Renamed all identifiers to sec-overlay; run instructions resolve from `${CLAUDE_PLUGIN_ROOT}`; test suite green (552 pass, 2 env-only skips); plugin and marketplace manifests validate.
- Hardened the finding renderers against an agent-authored `expected_signal` that arrives as a bare string; the report and red-team renderers now share one tolerant helper (`render_util.signal_lines`). Branch `fix/redteam-signal-and-docs`.
- Pending user approval to merge `feat/port-sec-overlay` into `main`.
- Task 3 (KB doc/diagram redesign): flagged comment-only `file:line` citations in the phase gate as a scrutiny note (`is_comment_line`); 562 tests pass, 2 env-only failures unchanged.
- Started the KB doc/diagram redesign port (Task 1: prompt-constants added on branch `feat/kb-doc-diagram-redesign`).
- Task 2: added the `open_questions` field to `Finding` and the finding schema (TDD; 559 pass, 2 env-only failures).
- Task 4: `verify.py` rejects placeholder-version deps bumps and `verify_findings` no longer overrides a `validate-fix` not-fixed verdict (TDD; 565 pass, 2 env-only failures unchanged).
- Task 5: added the `deployment_config` context kind, `deployed_in` tag, and `Context.diagram` slot rendered into `CONTEXT.md` (TDD; 571 pass, 2 env-only failures unchanged).
- Task 6 (final): added `_question_block()` and a "Questions to ask" section to the red-team plan; wired `FIELD_OWNERSHIP`/`DIAGRAM_STYLE`/`QUALIFIER_PROOF` imports and the diagram/deployment-config prompt guidance into the agent prompts and docs (TDD; 573 pass, 2 env-only failures unchanged). KB doc/diagram redesign port complete on `feat/kb-doc-diagram-redesign`.
- Doc fix: synced `references/README.md`'s `finding.schema.json` row with the `open_questions` field, and corrected the skill `CLAUDE.md` §6 and §8 block counts (six and nine) to the actual twelve `prompt-constants.md` blocks.

## Next steps

- Merge `feat/port-sec-overlay` into `main` after user approval.
- Merge `feat/kb-doc-diagram-redesign` into `main` after user approval.
- Test local install: `/plugin marketplace add <this repo>` then `/plugin install sec-overlay@cjbischoff-claude-code-tools`.

## Decisions

- plugin.json declares no components; the default `skills/` directory scan handles discovery, and strict mode stays at its default (true).
- Version stays at 0.1.0 until the user approves a bump.
- Governance is enforced with prek local hooks rather than convention only, per user request for forced updates.
