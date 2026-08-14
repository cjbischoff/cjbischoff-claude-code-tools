# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## 0.2.1 - 2026-08-14

### Changed

- Split the plugin documentation by audience: maintainer manual at the plugin root, trimmed skill CLAUDE.md focused on running the harness, and a SKILL.md pointer to it.

## 0.2.0 - 2026-08-12

### Changed

- Default SARIF output to suppressed-full and populate driver.rules.

### Added

- Add systemic finding clustering, per-run self-score, and run-economics report section.
- Add external-boundary disposition: risk cap, ingested-package scope check, lead bucket.

## 0.1.0 - 2026-08-11

### Added

- Initial release: agentic security-audit harness (SAST prefilter, multi-agent gate ladder, SARIF + Markdown reports).
