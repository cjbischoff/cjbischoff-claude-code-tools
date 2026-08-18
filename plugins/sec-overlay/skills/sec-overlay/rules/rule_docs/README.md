# rule_docs/

Per-language LLM prompt payloads. `rule_glob.resolve_rule_doc(path)` reads one of these files and
injects its text as the reviewing agent's rule block for `sec-overlay review` — not human
documentation, not a coding-style guide.

| File | Pattern in `BUILTIN_PATH_RULE_MAP` | Covers |
|------|-------------------------------------|--------|
| `java.md` | `**/*.java` | Null/Optional dereference, thread safety, SQL/XSS injection, resource leaks, swallowed errors |
| `go.md` | `**/*.go` | Nil dereference/type assertions, goroutine capture, SQL/XSS injection, resource leaks, swallowed errors |
| `ts_js_tsx_jsx.md` | `**/*.{ts,js,tsx,jsx}` | Null/undefined dereference, unhandled promise rejection, SQL/XSS injection, resource leaks, swallowed errors |
| `kotlin.md` | `**/*.kt` | Platform-type nullability, coroutine scope leaks, SQL/XSS injection, resource leaks, swallowed errors |
| `rust.md` | `**/*.rs` | Panics on `unwrap`/`expect`, lock-order inversion, SQL/XSS injection, resource leaks, swallowed errors |
| `python.md` | `**/*.py` | Null/None dereference, thread safety, SQL/XSS injection, resource leaks, swallowed errors |
| `php.md` | `**/*.php` | Loose-comparison/type-juggling errors, shared process state, SQL/XSS injection, resource leaks, swallowed errors |
| `swift.md` | `**/*.swift` | Force unwrap/implicitly unwrapped optionals, actor isolation, SQL/XSS injection, resource leaks, swallowed errors |
| `default.md` | `**/*` fallback — no other pattern matched | Same five families in language-agnostic form |

Pattern order above is match order — the first pattern in `BUILTIN_PATH_RULE_MAP` that
matches a path wins, mirroring OCR's `system_rules.json` order (D-02).

## Format

Terse imperative checklists, `####` section headings, each ending with an explicit "Do not
report in the following cases:" block. No STE100 prose pass (D-05) — these are machine-consumed
instructions the reviewing agent reads verbatim, not prose for a person to read.

## Adding a rule doc

Adding a language doc here means adding its glob pattern to `rule_glob.BUILTIN_PATH_RULE_MAP` in
the same commit — an unresolvable doc is a config no reviewer sees. Pattern order is match
order: the first pattern in the map that matches wins, so a more specific pattern must precede a
broader one.
