# docs/

Design specs and planning documents for this marketplace.

**Naming convention:** specs live under `docs/superpowers/specs/` as
`YYYY-MM-DD-<topic>-design.md`.

**Writers:** Claude Code sessions in this workspace, on a branch, with user review
before merge.

## Contents

| Path | Purpose |
|------|---------|
| `superpowers/specs/2026-08-11-port-sec-overlay-design.md` | Design for porting the sec-harness skill into the sec-overlay plugin |
| `superpowers/plans/2026-08-11-port-sec-overlay.md` | Task-by-task implementation plan for the sec-overlay port |
| `superpowers/specs/2026-08-11-sec-overlay-doc-overhaul-design.md` | Design for the sec-overlay documentation overhaul (Go-prose removal, README/CLAUDE.md rewrite, per-folder READMEs, folder-README hook) |
| `superpowers/plans/2026-08-11-sec-overlay-doc-overhaul.md` | Six-commit implementation plan for the sec-overlay documentation overhaul |
| `superpowers/specs/2026-08-12-sec-overlay-review-improvements-design.md` | Design for four sec-overlay improvements from the lumedeodorant review: token accounting/self-score, systemic finding clustering, external-boundary disposition, SARIF completeness |
| `superpowers/plans/2026-08-12-sec-overlay-review-improvements.md` | Task-by-task TDD implementation plan for the four sec-overlay improvements (build order I3, I1, I2, I4) |
| `superpowers/specs/2026-08-14-marketplace-doc-structure-design.md` | Design for the marketplace documentation split: root CLAUDE.md for governance and scaffolding, per-plugin CLAUDE.md/README/CHANGELOG, plugin template, hook routing |
| `superpowers/plans/2026-08-14-marketplace-doc-structure.md` | Four-commit implementation plan for the marketplace documentation split (sec-overlay split, root rewrite, template, hook routing + test) |
