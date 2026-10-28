# commands/

Slash-command entry points for the plainspoken skill. Each command is a thin routing document: it names the mode and adds that mode's one hard constraint. All rules live in `skills/plainspoken/`; this folder holds no code.

| File | Command | Purpose |
|------|---------|---------|
| `interview.md` | `/plainspoken:interview <topic>` | Co-write a piece from the writer's own words. No drafting until the writer answers. |
| `rewrite.md` | `/plainspoken:rewrite <file or text>` | Rewrite a draft. Diagnoses substance before surface and matches a supplied writing sample. |
| `review.md` | `/plainspoken:review <file or text>` | Critique a draft. Does not rewrite and does not create or modify any file. |
| `brief.md` | `/plainspoken:brief <file or text>` | Tighten a draft into BLUF email, 3-sentence executive summary, action items, or tight message. Keeps every number, name, date, and decision verbatim. |
| `lint.md` | `/plainspoken:lint <file>` | Run `scripts/lint.py` and report the diagnostics. Does not change prose. |
