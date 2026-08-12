# `references/asvs/` — OWASP ASVS seed data

Curated ASVS 5.0 requirement seed consumed by the deterministic citation layer.

| File | Form & function |
|------|-----------------|
| `asvs_5.0.0.json` | A curated 12-item subset of OWASP ASVS 5.0.0 requirements (id, chapter, level, CWE, keywords, description). Loaded by `helpers/sec_overlay/asvs.py` and attached to findings by `citations.py` / `rule_matcher.py` as advisory ASVS ids — never as tool receipts. |

When a file here changes, update this README in the same commit (enforced by the pre-commit hook).
