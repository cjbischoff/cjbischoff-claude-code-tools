# commands/

Slash-command entry points for the readme-keeper skill. Each command is a thin routing document: it names the mode and adds that mode's one hard constraint. All rules live in `skills/readme-keeper/`; this folder holds no code.

| File | Command | Purpose |
|------|---------|---------|
| `create.md` | `/readme-keeper:create [path] [--depth minimal\|standard\|full] [--research] [--style fancy]` | Create a README from the repo's real files. Refuses if the README exists. Shows a diff and stops before writing. |
| `update.md` | `/readme-keeper:update [path] [--style fancy]` | Refresh the marked regions of a README. Never edits text outside markers. Shows a diff and stops. |
| `check.md` | `/readme-keeper:check [path\|--all] [--links] [--prose] [--strict] [--install-ci]` | Run `scripts/check.py` and report. Read-only. With `--install-ci`, shows a diff that installs the CI check. |
| `review.md` | `/readme-keeper:review [path] [--score] [--research]` | Review a README with the reader rubric and rank findings P0, P1, P2. Never writes files. |
