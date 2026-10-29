# scripts

| File | Purpose |
|---|---|
| `check.py` | Check a README against the repo it describes. Python 3.11+, standard library only, one file. |

`check.py` is one file so the CI template can copy it into a target repo and run without the plugin.

## Usage

```bash
python3 check.py [README ...] [--all] [--exclude GLOB] [--root DIR] [--links] [--prose] [--json] [--strict]
```

| Argument | Effect |
|---|---|
| `README ...` | README files to check. A relative path is relative to `--root`. With no path and no `--all`, the checker reads `README.md` in `--root`. |
| `--all` | Check every tracked `README.md` (`git ls-files`). When git is absent, fails, or lists no README, the checker walks the tree. Both ways skip any README under a directory named `node_modules`, `.git`, `.venv`, `venv`, `fixtures`, `__fixtures__`, `testdata`, or `test-data`, at any depth. The names are matched on the path relative to `--root`, so a root inside a fixture directory still finds its own READMEs. |
| `--exclude GLOB` | With `--all`, also skip READMEs whose repo-relative path matches the `fnmatch` glob (`*` matches `/` too). Repeat the flag for more globs, for example `--exclude 'vendor/*' --exclude 'docs/archive/*'`. A README named as a path argument is never excluded. |
| `--root DIR` | Repo root. Default: the current directory. Manifests are read from each README's directory up to this root. |
| `--links` | Check external URLs. HEAD first, then GET after a 405. 10 second timeout, 4 requests at once. Off by default. |
| `--prose` | Add the prose-tell findings (P2). The word lists are in `../references/tells.md`. |
| `--json` | Print `{"files": [{"path", "findings": [{"check", "severity", "line", "message", "evidence"}]}]}`. No score. |
| `--strict` | Exit 1 on a P1 finding as well as a P0 finding. |

## Checks

| Check | Rule | Severity |
|---|---|---|
| `commands` | A command in a shell code block must match a script, target, entry point, or path in the repo. Recognized: `npm run`, `pnpm`, `yarn`, `make`, `just`, `uv run`, `poetry run`, `cargo run --bin`, `go run ./path`. Any other command is skipped, never guessed. | P0 |
| `package-manager` | An install command uses the manager the lockfile shows. A global install (`-g`) is skipped. | P1 |
| `paths` (links) | A relative Markdown link, image, or `<img src>` must point to an existing file. A link that leaves the repo root (such as `../../issues`) is skipped. | P0 |
| `paths` (inline code) | An inline-code span that looks like a file path is looked up in the README folder, the repo root, then by suffix against tracked files. Not found anywhere: "unresolved path, check intent". Inline code often names runtime outputs or files in other repos, so this never fails CI. | P2 |
| `anchors` | An in-page `#anchor` must match a heading slug (GitHub rules) or an HTML `id` or `name`. | P1 |
| `links` | `--links` only. A 4xx answer is P1. A timeout, a refused connection, a 5xx answer, or a 429 answer is P2, because those can be temporary. | P1 or P2 |
| `license` | A license named in the README must match the `LICENSE` file or a manifest `license` field. A license named with no license source is P0. | P0 |
| `badges` | A CI badge needs its workflow or config file. A registry badge needs a non-private manifest with a name. A coverage badge needs a coverage config. | P1 |
| `markers` | A `readme-keeper` region marker that is unpaired, nested, duplicate, or has an unknown region id. | P0 |
| `prose` | `--prose` only. Em dashes, stock AI words, marketing words, filler transitions. | P2 |

Markers inside fenced code and inside other HTML comments are not read as markers, so a README can show the marker syntax in a code block.

## Exit codes

| Code | Meaning |
|---|---|
| 0 | No P0 finding (and no P1 finding with `--strict`). |
| 1 | At least one P0 finding (or P1 with `--strict`). |
| 2 | Usage error, an unreadable file, or no README at the default path. |

## CI usage

Copy `check.py` into the target repo (the `/readme-keeper:check --install-ci` command does this) and run it on pull requests. Add `--strict` to fail the job on P1 findings too.

```bash
python3 .github/scripts/readme_check.py --all
```

Do not add `--links` to a pull request job unless you accept network access from the runner. The checker sends a request to every URL in the README, including any URL that points at an internal host.

## Never executes target code

- The checker reads files. It never runs a command from a README and never runs a script from the target repo.
- Manifests are parsed as data: `json` for `package.json`, `tomllib` for `pyproject.toml` and `Cargo.toml`, and line scans for `Makefile` and `justfile`.
- The only subprocess is `git ls-files` for `--all`, with `core.fsmonitor` turned off so the target repo cannot start a program.
- The only network access is `--links`.
- Every regular expression is linear-time, and the comment and fence scanners use `str.find` loops. A test feeds 80,000 characters of unclosed `[`, `<!--`, and backticks and requires a result in under 1.5 seconds.

## Development

```bash
cd plugins/readme-keeper
uv run --with pytest pytest -q                                    # tests
python3 -m doctest skills/readme-keeper/scripts/check.py          # doctests
uvx ruff check --line-length 100 . && uvx ruff format --line-length 100 --check .
```

`../references/tells.md` and the lexicon constants in `check.py` list the same entries. A test fails when they differ.

A license badge counts as a license claim only when its parsed hostname is `shields.io` or `badgen.net` (or a subdomain), never when that string appears elsewhere in the URL.
