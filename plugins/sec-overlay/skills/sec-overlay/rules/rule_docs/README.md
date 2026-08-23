# rule_docs/

Per-language LLM prompt payloads. `rule_glob.resolve_rule_doc(path)` reads one of these files and
injects its text as the reviewing agent's rule block for `sec-overlay review` — not human
documentation, not a coding-style guide.

Rows are in `BUILTIN_PATH_RULE_MAP` order, which is match order — the first pattern that
matches a path wins. The patterns, doc filenames, and order mirror OCR's `system_rules.json`
exactly (D-02, REQ-P2); the trailing `**/*` catch-all makes `default.md` a reachable map value.
Every doc covers the same five families (null/absent-value dereference, thread safety, injection,
resource leaks, swallowed errors); the Covers column names the file type and its distinctive angle.

| File | Pattern in `BUILTIN_PATH_RULE_MAP` | Covers |
|------|-------------------------------------|--------|
| `properties.md` | `**/*.properties` | Java `.properties`: missing/null keys, duplicate-key override races, injection, resource limits, swallowed load errors |
| `mapper_dao_xml.md` | `**/*{mapper,dao}*.xml` | MyBatis mapper/DAO XML: `${}` SQL injection vs `#{}` binding, unbounded result sets |
| `pom_xml.md` | `**/pom.xml` | Maven manifest: missing coordinates, version/snapshot pinning, dependency-source injection |
| `build_gradle.md` | `**/build.gradle` | Gradle build: dynamic versions, build-script injection, suppressed build/test failures |
| `package_json.md` | `**/package.json` | npm manifest: unpinned/untrusted deps, lifecycle-script injection, resource/version drift |
| `cargo_toml.md` | `**/Cargo.toml` | Rust manifest: version wildcards, git-source injection, feature/resource pitfalls |
| `composer_json.md` | `**/composer.json` | PHP manifest: constraint wildcards, script injection, source-repo trust |
| `json.md` | `**/*.{json,json5}` | Generic JSON/JSON5: missing/null keys, key-order assumptions, secrets/injection values, unbounded collections |
| `github_workflows.md` | `.github/workflows/**/*.{yaml,yml}` | GitHub Actions: `${{ }}` script injection, unpinned actions, `continue-on-error` masking |
| `github_config.md` | `.github/**/*.{yaml,yml}` | Other `.github/` config (dependabot, etc.): required keys, injection, permission scope |
| `yaml.md` | `**/*.{yaml,yml}` | Generic YAML config: missing keys, interpolation injection, resource limits, swallowed errors |
| `java.md` | `**/*.java` | Java: Null/Optional dereference, thread safety, SQL/XSS injection, resource leaks, swallowed errors |
| `go.md` | `**/*.go` | Go: nil dereference/type assertions, goroutine capture, injection, resource leaks, swallowed errors |
| `freemarker.md` | `**/*.{ftl,ftlh,ftlx}` | FreeMarker templates: unescaped output/XSS, SSTI, null interpolation |
| `arkts.md` | `**/*.ets` | ArkTS/OpenHarmony: null/undefined, async/worker races, DOM/eval injection |
| `astro.md` | `**/*.astro` | Astro components: `set:html`/raw-interpolation XSS, null interpolation |
| `ts_js_tsx_jsx.md` | `**/*.{ts,js,tsx,jsx}` | TS/JS: null/undefined dereference, unhandled promise rejection, injection, resource leaks, swallowed errors |
| `kotlin.md` | `**/*.{kt}` | Kotlin: platform-type nullability, coroutine scope leaks, injection, resource leaks, swallowed errors |
| `rust.md` | `**/*.rs` | Rust: panics on `unwrap`/`expect`, lock-order inversion, injection, resource leaks, swallowed errors |
| `cpp.md` | `**/*.{cpp,cc,hpp}` | C++: null/moved-from optional deref, data races, command/format injection, RAII leaks, swallowed exceptions |
| `c.md` | `**/*.c` | C: NULL/use-after-free, data races, command/format/buffer injection, handle leaks, ignored return codes |
| `python.md` | `**/*.py` | Python: null/None dereference, thread safety, injection, resource leaks, swallowed errors |
| `php.md` | `**/*.{php,phtml}` | PHP: type-juggling errors, shared process state, injection, resource leaks, swallowed errors |
| `protobuf.md` | `**/*.proto` | Protobuf: presence/optional semantics, wire/registry migration, payload injection, unbounded fields |
| `po.md` | `**/*.po` | gettext catalog: missing `msgstr`, format-placeholder mismatch/injection (most families N/A) |
| `pot.md` | `**/*.pot` | gettext template: same as `.po`, template scope (most families N/A) |
| `graphql.md` | `**/*.{graphql,gql}` | GraphQL SDL: nullability misuse, resolver concurrency, injection/introspection, unbounded queries |
| `prisma.md` | `**/*.prisma` | Prisma schema: optional-relation mismatch, migration races, `$queryRaw` injection, index/pool sizing |
| `julia.md` | `**/*.jl` | Julia: `nothing`/`missing`, `@threads` races, injection, missing `close`, swallowed errors |
| `terraform.md` | `**/*.{tf,hcl,tfvars}` | Terraform/HCL: missing vars, interpolation injection, open SGs/overbroad IAM, ignored failures |
| `bicep.md` | `**/*.bicep` | Azure Bicep: insecure nullable defaults, deployment ordering, injection/permissions, resource limits |
| `nix.md` | `**/*.nix` | Nix: null/undefined refs, override races, unpinned-source injection, sandbox/resource isolation |
| `haskell.md` | `**/*.{hs,lhs}` | Haskell: partial functions/`Maybe` misuse, `MVar`/`STM` races, injection, missing `bracket` |
| `nim.md` | `**/*.{nim,nims,nimble}` | Nim: `nil` deref, thread/GC races, injection, missing `defer`, discarded errors |
| `swift.md` | `**/*.swift` | Swift: force-unwrap optionals, actor isolation, injection, resource leaks, swallowed errors |
| `default.md` | `**/*` fallback — no other pattern matched | Same five families in language-agnostic form |

## Format

Terse imperative checklists, `####` section headings, each ending with an explicit "Do not
report in the following cases:" block. No STE100 prose pass (D-05) — these are machine-consumed
instructions the reviewing agent reads verbatim, not prose for a person to read.

## Adding a rule doc

Adding a language doc here means adding its glob pattern to `rule_glob.BUILTIN_PATH_RULE_MAP` in
the same commit — an unresolvable doc is a config no reviewer sees. Pattern order is match
order: the first pattern in the map that matches wins, so a more specific pattern must precede a
broader one.
