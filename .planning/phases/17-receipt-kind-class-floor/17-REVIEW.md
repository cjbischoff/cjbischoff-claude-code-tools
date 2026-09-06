# Phase 17 Code Review — Receipt Kind & Class Floor

**Depth:** standard
**Files reviewed:** evidence.py, coverage_ledger.py

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Warning | 0 |
| Info | 1 |

---

## Info

### I-01: `validate_dependency_catalog_receipt` uses `catalog_ids` param, not the live catalog

**File:** `evidence.py:70-80`
**Severity:** Info
**Description:** The function requires `catalog_ids` to be passed explicitly rather than calling `catalog_ids()` from `dependency_sinks.py` directly. This makes it testable (no import of the live catalog) but means callers must remember to pass the correct id set. Consider adding a convenience wrapper that calls `catalog_ids()` as default when no argument is provided.
