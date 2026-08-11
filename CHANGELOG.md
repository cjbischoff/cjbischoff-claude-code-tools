# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format:

- One `## <version> - <YYYY-MM-DD>` section per release, newest first.
- Entries are grouped under `### Changed`, `### Added`, `### Removed`, `### Fixed` — in that order.
- Each entry is one sentence in the imperative mood, describing the change from the user's point of view.
- Every commit that changes a tracked file adds an entry here in the same commit.

## 0.1.0 - 2026-08-11

### Added

- Scaffold the plugin marketplace manifest and the sec-overlay plugin (v0.1.0) with a placeholder skill script.
- Add commit governance: Conventional Commits check, main-branch block, and forced README/CHANGELOG updates via prek hooks.
- Add the design spec for porting the sec-harness skill into the sec-overlay plugin.
- Add the implementation plan for the sec-overlay port and extend the rename scope to the HARNESS_ROOT and SEC_HARNESS_HOME tokens.
- Add the design spec for incorporating upstream's KB doc/diagram redesign into the sec-overlay plugin.
- Import the sec-harness skill source tree into the sec-overlay plugin (semgrep submodule excluded).
- Rename the ported identifiers to sec-overlay: the `sec_overlay` Python package, the `sec-overlay` distribution name, and the `SEC_OVERLAY_HOME` and `OVERLAY_ROOT` tokens.
- Point the SKILL.md run instructions at `${CLAUDE_PLUGIN_ROOT}` and document the semgrep ruleset as a prerequisite (the semgrep-rules submodule is not shipped).
- Verify the rename preserved behavior: 552 tests pass; the two failures are environment-only (gitignored bench corpus, excluded semgrep submodule), not rename regressions.
- Update sec-overlay manifest descriptions to the agentic security-audit harness.
- Add the DIAGRAM_STYLE, FIELD_OWNERSHIP, and QUALIFIER_PROOF prompt-constants blocks.
- Add the `open_questions` field to `Finding` and the finding schema.
- Flag comment-only `file:line` citations in the phase gate as a scrutiny note.
- Add the `deployment_config` context kind, `deployed_in` tag, and `Context.diagram` slot rendered into `CONTEXT.md`.

### Fixed

- Prevent the report renderer from crashing when a red-team agent writes `runtime_test.expected_signal` as a bare string; the report and red-team renderers now share one tolerant helper and the finding schema validates the `runtime_test` inner shape.
- Reject placeholder-version deps bumps and stop `verify_findings` from overriding a `validate-fix` not-fixed verdict.
