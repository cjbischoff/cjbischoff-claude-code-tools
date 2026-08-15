# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## 0.5.0 - 2026-08-15

### Added

- Add `sec_overlay.driver.render_dispatch`: a deterministic, side-effect-free printer that names an agent phase's `agents/<prompt>` file and the `{{TARGET}}`/`{{WORKSPACE}}`/`{{SHA}}` substitutions the orchestrator must apply.

## 0.4.0 - 2026-08-15

### Added

- Add `sec_overlay.driver`: `run_deterministic_phase` gates a `PhaseSpec` on inputs/outputs, runs its registered `DETERMINISTIC_ACTIONS` entry, and records the stage — raising `PhaseHalt` when an input or output artifact is missing.

## 0.3.0 - 2026-08-15

### Added

- Add `sec_overlay.phases`: a frozen, ordered `PhaseSpec` table (`PHASE_TABLE`) and pure sequencer helpers (`missing_inputs`, `outputs_present`, `next_actionable_phase`) for the audit driver.

## 0.2.1 - 2026-08-14

### Changed

- Split the plugin documentation by audience: maintainer manual at the plugin root, trimmed skill CLAUDE.md focused on running the harness, and a SKILL.md pointer to it.
- Fix the README quick-start command to `cd` into `skills/sec-overlay/helpers` (the README sits at the plugin root, not inside `helpers`), and note the `${CLAUDE_PLUGIN_ROOT}` path for an installed plugin.

## 0.2.0 - 2026-08-12

### Changed

- Default SARIF output to suppressed-full and populate driver.rules.

### Added

- Add systemic finding clustering, per-run self-score, and run-economics report section.
- Add external-boundary disposition: risk cap, ingested-package scope check, lead bucket.

## 0.1.0 - 2026-08-11

### Added

- Initial release: agentic security-audit harness (SAST prefilter, multi-agent gate ladder, SARIF + Markdown reports).
