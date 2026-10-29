# references/

Files the `readme-keeper` skill loads by mode. `SKILL.md` holds the router, the safeguards, the mode steps, and the marker rules. Each file here holds the detail for one concern.

| File | Holds | Loaded by |
|------|-------|-----------|
| `types/` | One reference per project type: section order, depth-tier rules, slot descriptions (see `types/README.md`) | `create` (the matching type), `review` (expected sections) |
| `rubric.md` | The reader rubric: four questions, three readers, caveats first, trust signals, common mistakes, "won't do", the P0/P1/P2 list, and the `--score` weights | `review`; `create` for the opening |
| `tells.md` | The prose-tell word lists that `scripts/check.py --prose` flags. A test keeps it in sync with the lexicon in `check.py`, so change both together | `review` with `--prose` |

## Attribution

- `tells.md` adapts plainspoken (this repo), which adapts clarity (MIT, Addy Osmani) and work-humanizer (MIT, Pawel Huryn).
