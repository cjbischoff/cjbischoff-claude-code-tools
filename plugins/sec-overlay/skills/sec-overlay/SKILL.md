---
description: Apply a security overlay to code changes. Use when the user asks to run a security overlay, security-check a diff or working tree, or scan changed files for common vulnerability patterns before commit or review.
---

# sec-overlay

## Purpose

This skill runs scripted security checks against the current working tree or a diff. It reports findings with file and line references. It does not change code.

## When to invoke

Invoke this skill when the user asks to:

- Run a security overlay on changes.
- Security-check a diff, branch, or working tree before commit or review.
- Scan changed files for common vulnerability patterns.

Do not invoke this skill for full security audits of an entire repository. Use a dedicated audit workflow for that.

## How to run

1. Run the entry script:
   `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/scripts/run.py`
2. Pass a path or diff range as the first argument. The default is the current working tree.
3. Read the script output. It reports findings as one line per finding, with file, line, and rule identifier.

## How to report results

1. Lead with the outcome: the number of findings, or "no findings".
2. List each finding with its `file:line` reference and a one-sentence explanation.
3. Mark each finding as confirmed or unconfirmed. A finding is confirmed only when you show the code path that triggers it.
4. Do not apply fixes. Report the findings and stop, unless the user asks for fixes.

## Constraints

- All executable logic lives in `${CLAUDE_PLUGIN_ROOT}/skills/sec-overlay/scripts/`. Do not add logic to this file.
- Scripts must not reference paths outside the sec-overlay plugin directory. Only that directory is copied to the plugin cache on install.
