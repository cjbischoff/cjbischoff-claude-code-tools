# `agents/classes/` — attack-class prompt extensions

Attack-class prompt extensions; `investigate.md` loads the `classes/<key>.md` matching
each candidate's class. `test_wiring.py` guards the wiring.

| File | Attack class |
|------|--------------|
| `authn.md` | Authentication — canonical fix shape for authentication weaknesses. |
| `authz.md` | Authorization — canonical fix shape for missing/incorrect access-control checks. |
| `business-logic.md` | Business logic — canonical fix shape for workflow-level exploitation. |
| `config.md` | Configuration — includes a non-Python test contract (no TDD requirement). |
| `context-bleed.md` | Context bleed — canonical fix shape for cross-tenant/cross-session data leakage. |
| `crypto.md` | Cryptography — canonical fix shape for weak/misused crypto primitives. |
| `excessive-agency.md` | Excessive agency — canonical fix shape for overly permissive agent/tool capability. |
| `injection.md` | Injection — canonical fix shape for SQL/command/template/etc. injection. |
| `prompt-injection.md` | Prompt injection — canonical fix shape for untrusted-text-into-model attacks. |
| `resource.md` | Resource exhaustion — canonical fix shape for DoS/unbounded-resource issues. |
| `ssrf.md` | SSRF — canonical fix shape for server-side request forgery. |

When a file here changes, update this README in the same commit (enforced by the pre-commit hook).
