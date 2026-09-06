# Phase 16 Code Review — Dependency-Sink Catalog & CWE Mapping

**Depth:** standard
**Files reviewed:** clsmap.py, dependency_sinks.py, dependency-sinks.json, prefilter.py, attack-classes.md, route_census.py

---

## Summary

| Severity | Count |
|----------|-------|
| Critical | 0 |
| Warning | 0 |
| Info | 2 |

---

## Info

### I-01: `_FLOOR` dict recreated on every `build_coverage_ledger` call

**File:** `coverage_ledger.py:94-100`
**Severity:** Info
**Description:** The `_FLOOR` dictionary is defined as a local variable inside `build_coverage_ledger`, so it is reconstructed on every call. Since this function is called once per run, performance is not a concern. Consider promoting to module level for consistency with other constants in the codebase (e.g., `_REPORTED`, `_SETTLED_NO_ISSUE`).

### I-02: `validate_dependency_catalog_receipt` is unreachable from the findings gate

**File:** `evidence.py:70-80`
**Severity:** Info
**Description:** The `validate_dependency_catalog_receipt` function is added to evidence.py but not yet wired into any gate or validation path. It's a pure library function with tests. Consider adding it to the findings gate's receipt validation path so that an invalid `dependency-catalog:` receipt is caught at the gate, not silently ignored.
