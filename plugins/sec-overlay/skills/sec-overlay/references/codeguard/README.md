# `references/codeguard/` — secure-coding checklists

Terse secure-coding checklists, one per domain, consumed by `codeguard.py` and the
patch/triage agents for correct remediation shape.

| File | Domain covered |
|------|-----------------|
| `codeguard-0-api-web-services.md` | API & web services: webhook signature verification, endpoint authn/authz, rate limiting, response reflection. |
| `codeguard-0-authorization-access-control.md` | Authorization & access control: object/function-level authz, ownership derivation, deny-by-default. |
| `codeguard-0-client-side-web-security.md` | Client-side web security: DOM sinks, `postMessage` origin checks, CORS, unsafe redirects. |
| `codeguard-0-cryptography.md` | Cryptography: authenticated encryption, approved hashes/KDFs, key management. |
| `codeguard-0-file-handling-and-uploads.md` | File handling & uploads: path canonicalization, upload validation, streaming, quotas. |
| `codeguard-0-input-validation-injection.md` | Input validation & injection defense: parameterized queries, argument-vector command execution, boundary validation. |
| `codeguard-0-safe-c-functions.md` | Safe C/C++ functions: bounded string functions, length checks, wire-length validation before fixed-buffer copies. |

When a file here changes, update this README in the same commit (enforced by the pre-commit hook).
