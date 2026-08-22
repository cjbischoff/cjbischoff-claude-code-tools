---
schema_version: 1
open_count: 2
waived_count: 0
fixed_count: 0
total_count: 2
last_updated: 2026-08-22T14:17:07.528Z
---

# Broken Windows Ledger

> Cross-phase defect register. With `workflow.windows_enforce` enabled, `/gsd-ship` blocks while `open_count > 0`.
> Waive with `gsd-tools windows waive <id> "<reason>"` (reason required).
> Mark fixed with `gsd-tools windows fixed <id>`.

| id | phase | kind | file | line | description | status | reason | recorded_at | resolved_at |
|----|-------|------|------|------|-------------|--------|--------|-------------|-------------|
| 1 | 06 | deviation | plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py | 778 | Pre-existing ruff I001 import-order finding (import subprocess after from sec_overlay import cli), not caused by 06-06 changes, deferred out of scope | open |  | 2026-08-22T14:17:07.372Z |  |
| 2 | 06 | deviation | .planning/phases/06-remediation-and-governed-release/06-SECURITY.md | 77 | CodeRabbit PR #29: duplicated open threat status contradicts threats_open: 0; register total (37 rows) mismatches reported 35 total threats (lines 96-99). Pre-existing from 92bc991, out of 06-06 file scope, not fixed | open |  | 2026-08-22T14:17:07.528Z |  |

````json
[
  {
    "id": 1,
    "kind": "deviation",
    "phase": "06",
    "file": "plugins/sec-overlay/skills/sec-overlay/helpers/tests/test_cli.py",
    "line": 778,
    "description": "Pre-existing ruff I001 import-order finding (import subprocess after from sec_overlay import cli), not caused by 06-06 changes, deferred out of scope",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-22T14:17:07.372Z",
    "resolved_at": null
  },
  {
    "id": 2,
    "kind": "deviation",
    "phase": "06",
    "file": ".planning/phases/06-remediation-and-governed-release/06-SECURITY.md",
    "line": 77,
    "description": "CodeRabbit PR #29: duplicated open threat status contradicts threats_open: 0; register total (37 rows) mismatches reported 35 total threats (lines 96-99). Pre-existing from 92bc991, out of 06-06 file scope, not fixed",
    "status": "open",
    "reason": "",
    "recorded_at": "2026-08-22T14:17:07.528Z",
    "resolved_at": null
  }
]
````
