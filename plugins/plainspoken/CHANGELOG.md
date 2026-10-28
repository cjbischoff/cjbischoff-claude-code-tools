# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## Unreleased

### Added

- Add failing tests for the twelve new lint sweep keys.

## 0.1.1 - 2026-10-28

### Fixed

- Fix the work-humanizer attribution: credit Pawel Huryn and include its MIT license in `NOTICE.md`, which 0.1.0 omitted.

## 0.1.0 - 2026-10-28

_Initial release._

### Added

- Add the plainspoken plugin scaffold: manifest, README, maintainer manual, and the clarity MIT notice.
- Add `references/tells.md`, the merged AI-tell lexicon from work-humanizer and clarity, and 14 failing tests for the lint script.
- Add `scripts/lint.py`, a stdlib diagnostic script that merges clarity's prose statistics with the work-humanizer tell sweep and reports no score or verdict. Every regular expression in it runs in linear time on hostile input.
- Add the `plainspoken` skill: a five-mode router with shared safeguards and a unified footer, plus the interview, rewrite, review, brief, medium, and long-form references.
- Add the `/plainspoken:interview`, `:rewrite`, `:review`, `:brief`, and `:lint` slash commands.
- Add 19 development-only eval cases (11 adapted from clarity, 8 new for brief and rewrite), the judge protocol, and a schema test.
