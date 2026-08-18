# rule_docs/

Per-language LLM prompt payloads. `rule_glob.resolve_rule_doc(path)` reads one of these files and
injects its text as the reviewing agent's rule block for `sec-overlay review` — not human
documentation, not a coding-style guide.

| File | Pattern in `BUILTIN_PATH_RULE_MAP` | Covers |
|------|-------------------------------------|--------|
| `python.md` | `**/*.py` | Null/None dereference, thread safety, SQL/XSS injection, resource leaks, swallowed errors |
| `default.md` | fallback — no pattern matched | General correctness, security, resource handling, concurrency, maintainability |

## Format

Terse imperative checklists, `####` section headings, each ending with an explicit "Do not
report in the following cases:" block. No STE100 prose pass (D-05) — these are machine-consumed
instructions the reviewing agent reads verbatim, not prose for a person to read.

## Adding a rule doc

Adding a language doc here means adding its glob pattern to `rule_glob.BUILTIN_PATH_RULE_MAP` in
the same commit — an unresolvable doc is a config no reviewer sees. Pattern order is match
order: the first pattern in the map that matches wins, so a more specific pattern must precede a
broader one.
