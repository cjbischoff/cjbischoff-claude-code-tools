# CLAUDE.md — plainspoken plugin maintainer manual

This file guides a maintainer working on the plainspoken plugin source. It never loads into a
user's session when the plugin is installed.

Governance (branching, commits, changelogs, version bumps) lives in the root `CLAUDE.md`.
Nothing here overrides it.

---
## Developing

```bash
cd plugins/plainspoken
uv run --with pytest pytest -q                     # lint script + eval schema tests
uvx ruff check . && uvx ruff format --check .      # style, line length 100
python3 skills/plainspoken/scripts/lint.py <file>  # run the linter on a draft
```

- `skills/plainspoken/references/tells.md` and the lexicon constants in
  `skills/plainspoken/scripts/lint.py` must list the same entries. `tests/test_lint.py`
  enforces this. Change both in the same commit.
- `skills/plainspoken/SKILL.md` stays under 200 lines. Detail goes into `references/`.
- `lint.py` is stdlib only. Do not add dependencies.

## Evals

`evals/` is development-only. A run is manual, one fresh session per case, judged per
`evals/JUDGE.md`. Steps are in `evals/README.md`. Run the evals after any change to `SKILL.md`
or a reference file, and record the result in the pull request.

---
## Documentation

Every folder under this plugin has a `README.md`: `commands/`, `skills/plainspoken/`,
`skills/plainspoken/references/`, `skills/plainspoken/scripts/`, `tests/`, `evals/`. A commit that
changes a file in one of those folders updates that folder's `README.md`.

## Versioning note

Version `0.1.0` held across every commit of the initial branch, because no user had installed
the plugin before its first merge. From the first merge on, the root bump rule applies to each
shipping-file commit.

## Attribution

Material adapted from clarity (MIT, Addy Osmani) is listed in `NOTICE.md`. Keep that table
current when an adapted file is added, renamed, or removed.
