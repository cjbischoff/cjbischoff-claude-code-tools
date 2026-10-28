---
description: Run plainspoken's mechanical prose diagnostics on a file
argument-hint: [file path]
---
Use the `plainspoken` skill in lint mode on: $ARGUMENTS

Run `python3 "${CLAUDE_PLUGIN_ROOT}/skills/plainspoken/scripts/lint.py" <file>` and report its output. Treat every hit as a prompt to read the passage in context, not a verdict. Do not change the prose.
