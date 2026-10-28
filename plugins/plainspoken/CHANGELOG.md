# Changelog

This file follows the [Common Changelog](https://common-changelog.org) format.

## 0.2.0 - 2026-10-28

### Added

- Add `/plainspoken:deep`: four read-only lens agents (structure, fluff, pattern, flow) run in parallel, the findings are merged and ranked by severity, and one rewrite runs only after the writer approves.
- Add P0/P1/P2 severity tiers (`references/severity.md`) to review and deep findings. Casual text reports P0 only.
- Add eleven pattern families, structure and flow checks, tighten tests, and four edge rules (acronyms, emoji, predicate hyphens, curly quotes) to `references/rewrite.md`.
- Add investor-email, social-post, and casual rows to `references/medium.md`.
- Add twelve `lint.py` sweep keys, including cluster words per paragraph and density words.

### Changed

- Route "tighten" and "cut the fluff" to `rewrite` instead of `brief`.

- Add failing tests for the twelve new lint sweep keys.
- Add 8 eval cases for deep mode, severity, casual P0-only review, `tighten` routing, word swaps, false breadth, and unresolved acronyms, plus two hard gates in `evals/JUDGE.md`.

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
