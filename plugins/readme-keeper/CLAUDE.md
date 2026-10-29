# CLAUDE.md — readme-keeper plugin maintainer manual

This file guides a maintainer working on the readme-keeper plugin source. It never loads into a
user's session when the plugin is installed.

Governance (branching, commits, changelogs, version bumps) lives in the root `CLAUDE.md`.
Nothing here overrides it.

---
## Developing

```bash
cd plugins/readme-keeper
uv run --with pytest pytest -q                       # checker, fixtures, eval schema
uvx ruff check . && uvx ruff format --check .        # style, line length 100
python3 -m doctest skills/readme-keeper/scripts/check.py
python3 skills/readme-keeper/scripts/check.py --all --root <repo>
```

- `check.py` is one stdlib file (Python 3.11+). The CI template copies it, so it must never
  import another plugin file.
- Every regex in `check.py` must be linear-time. `tests/test_check.py` has a hostile-input limit.
- `references/tells.md` and the lexicon in `check.py` list the same entries. A test enforces it.
- `check.py` never runs target-repo code. `--links` is the only network access, and it is opt-in.
- Type references hold slot descriptions, never sample facts.
- `SKILL.md` stays under 200 lines.

## Evals

`evals/` is development-only. Run them manually per `evals/README.md` after any change to
`SKILL.md`, a reference, or a command.

---
## Documentation

Every folder under this plugin has a `README.md`, except the fixture repos under
`tests/fixtures/`, where `README.md` files are test inputs. A commit that changes a file in a
folder updates that folder's `README.md`.

## Versioning note

Version `0.1.0` held across every commit of the initial branch, because no user had installed
the plugin before its first merge. From the first merge on, the root bump rule applies.

## Attribution

Every adapted file is listed in `NOTICE.md` with its source and license. Never copy text from
`tavva/ben-claude-plugins`: it has no license file.
