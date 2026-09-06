# Detection coverage

_Generated from the live `clsmap` inventory (`sec_overlay.detection_coverage`). An honest, falsifiable statement of what this harness catches and does not — not a claim to detect everything._

## Rule sources

| source | what it covers |
|--------|----------------|
| semgrep | broad pattern SAST, all languages; vendored security rulesets |
| dependency-internal sink | No backend reads a dependency's own source, so a sink inside OPA/CEL/Starlark/goja/Lua is invisible to pattern and dataflow rules. `references/dependency-sinks.json` closes the routing half: a manifest match routes the attack class. It does not prove the sink; the class prompt's proof tuple does. |
| codeql | semantic dataflow/taint (`security-extended`), compiled + go, python, javascript, java, csharp, cpp, ruby, swift
| osv-scanner (sca) | dependency CVEs from lockfiles/manifests |
| secrets (in-house) | distinctive-prefix credentials; broad via optional gitleaks |
| agent + ripgrep | SAST-blind languages (Liquid/templates) + business-logic/hunt-list |

## Vulnerability classes

| class | confidence | primary source |
|-------|-----------|----------------|
| authn | High | semgrep/codeql |
| authz | High | semgrep/codeql |
| business-logic | High | semgrep/codeql |
| clear-text-logging | High | semgrep/codeql |
| cmdi | High | semgrep/codeql |
| crypto | High | semgrep/codeql |
| cswsh | High | semgrep/codeql |
| deserialization | High | semgrep/codeql |
| excessive-agency | High | semgrep/codeql |
| injection | High | semgrep/codeql |
| jwt | High | semgrep/codeql |
| log-injection | High | semgrep/codeql |
| open-redirect | High | semgrep/codeql |
| path-traversal | High | semgrep/codeql |
| prototype-pollution | High | semgrep/codeql |
| request-smuggling | High | semgrep/codeql |
| resource | High | semgrep/codeql |
| secrets | High | secrets |
| sqli | High | semgrep/codeql |
| ssrf | High | semgrep/codeql |
| ssti | High | semgrep/codeql |
| xss | High | semgrep/codeql |
| xxe | High | semgrep/codeql |

## Language coverage matrix

| capability | php | python | javascript/ts | go | java | liquid/templates |
|------------|-----|--------|---------------|----|----|------------------|
| semgrep patterns | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| codeql dataflow | — | ✅ | ✅ | ✅ | ✅ | — |
| sca (deps) | ✅ | ✅ | ✅ | ✅ | ✅ | — |
| secrets | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| agent + ripgrep (templates/logic) | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

## Known limitations

- **CodeQL has no PHP support** — PHP dataflow relies on semgrep patterns only.
- **Semgrep OSS taint is single-function** — no cross-function/cross-file taint (that needs Semgrep Pro); the agentic investigate phase covers cross-function paths.
- **Liquid/Handlebars/ERB templates are SAST-blind** — no CodeQL/semgrep taint; covered by agent template reads grounded with `ripgrep:` receipts.
- **SCA/secrets need their tools** — `osv-scanner` for deps (else skipped-and-logged), optional `gitleaks` for broad secrets (in-house scanner covers distinctive tokens only).
- **Business-logic / auth-model classes are agent-found**, not rule-detected — recall depends on the threat-model hunt list, not SAST.
