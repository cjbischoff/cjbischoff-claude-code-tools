# commands/

Slash-command entry points for the sec-overlay skill.

| File | Command | Purpose |
|------|---------|---------|
| `audit.md` | `/sec-overlay:audit <repo> [<repo> ...]` | Drive a single-repo audit, or audit several repos and correlate them into the invocation directory. |

The command is a thin routing document over `sec_overlay.run.drive` (single repo) and
`python -m sec_overlay.correlate` (multi-repo). All executable logic lives under
`helpers/sec_overlay/`; this folder holds no code.
