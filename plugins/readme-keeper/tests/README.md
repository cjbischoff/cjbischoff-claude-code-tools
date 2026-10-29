# tests/

Offline `pytest` checks for the plugin. They need no network and no API key. The `--links`
tests start a local `http.server` on 127.0.0.1.

## Run

```bash
cd plugins/readme-keeper && uv run --with pytest pytest -q
```

## Files

| File | Checks |
|------|--------|
| `test_check.py` | `skills/readme-keeper/scripts/check.py` as a real command-line program, against the fixture repos: commands per manager (npm, pnpm, yarn, make, just, uv, poetry, cargo, go) including `cd DIR &&` and dependency groups, package manager vs lockfile, link and image paths (P0) and inline-code paths (P2 after a suffix match), anchors by GitHub slug rules, license vs `LICENSE` or manifest (license badges by parsed host), fact-gated badges, marker pairing, `--links` against a local server, `--prose`, `--all`, `--json`, exit codes, `--strict`, the `tells.md` sync, markers inside code spans, `--all` default excludes for fixture folders and `--exclude`, and a hostile-input time limit |
| `test_evals.py` | `evals/cases.json`: the file parses, every case has the required keys, ids are unique, each mode is `create`, `update`, `check`, or `review`, every mode has at least one case, and an optional `followup` is a non-empty string |

## Fixtures

`fixtures/<shape>/` holds one minimal repo per project shape: `node-npm`, `node-pnpm-workspace`,
`py-uv`, `py-poetry`, `make`, `just`, `go`, `rust`, `claude-plugin`. Their `README.md` files are
test inputs with planted faults, not documentation. `node-npm/package-lock.json` is matched by a
global gitignore pattern on some machines; it is committed with `git add -f`.
