# tests/

Offline `pytest` checks for the plugin. They need no network and no API key.

## Run

```bash
cd plugins/plainspoken && uv run --with pytest pytest -q
```

## Files

| File | Checks |
|------|--------|
| `test_lint.py` | `skills/plainspoken/scripts/lint.py`, called as a real command-line program: Markdown stripping, `--raw`, dashes and semicolons, stock words and phrases, sentence-start transitions, pause-and-point lines and closers, bold labels and exclamation marks, the uniform sentence-length band, the JSON groups, the absence of any score, verdict, or risk key, standard input, exit code 2 on a missing file, a quiet result on plain text, and that every entry in `references/tells.md` is also in the script |
| `test_evals.py` | `evals/cases.json`: the file parses, every case has the required keys, ids are unique, and each mode is one of `interview`, `rewrite`, `review`, `brief`, `lint` |

The model evals in `evals/` are manual and do not run here.
