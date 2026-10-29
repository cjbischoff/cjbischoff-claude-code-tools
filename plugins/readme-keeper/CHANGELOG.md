# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## 0.1.0 - 2026-10-28

_Initial release._

### Added

- Add the readme-keeper plugin scaffold: manifest, README, maintainer manual, and license notices.
- Add failing tests for the README checker against nine fixture repos, and the `tells.md` prose lexicon.
- Add `scripts/check.py`, a stdlib README checker: commands, link and image paths, inline-code paths (advisory), anchors, license, badges, markers, opt-in `--links` and `--prose`, JSON output, and CI exit codes.
- Add the `readme-keeper` skill: create, update, check, and review modes, seven project-type references, the reader rubric, fact-gated badges, safeguards, and annotated examples.
- Add the `/readme-keeper:create`, `:update`, `:check`, and `:review` commands, and a GitHub Actions template that `check --install-ci` copies into a repo with the checker.
- Add 15 development-only eval cases with a judge protocol and a schema test.
