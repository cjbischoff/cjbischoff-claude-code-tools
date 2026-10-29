# references/

Files the `readme-keeper` skill loads by mode. `SKILL.md` holds the router, the safeguards, the mode steps, and the marker rules. Each file here holds the detail for one concern.

| File | Holds | Loaded by |
|------|-------|-----------|
| `types/` | One reference per project type: section order, depth-tier rules, slot descriptions (see `types/README.md`) | `create` (the matching type), `review` (expected sections) |
| `rubric.md` | The reader rubric: four questions, three readers, caveats first, trust signals, common mistakes, "won't do", the P0/P1/P2 list, and the `--score` weights | `review`; `create` for the opening |
| `examples.md` | Three annotated AI/ML capstone READMEs with attribution | `create` for an AI/ML project |
| `badges.md` | Fact-gated badge rules and the decorative image catalog for `--style fancy` | `create` and `update` for the `badges` region |
| `safeguards.md` | The eight rules adapted from plainspoken: invent nothing, keep certainty, source text is data, never execute target code, diff-ask-write | Every mode that writes or reviews |
| `tells.md` | The prose-tell word lists that `scripts/check.py --prose` flags. A test keeps it in sync with the lexicon in `check.py`, so change both together | `review` with `--prose` |

## Attribution

- `types/`, `examples.md`, and the common mistakes in `rubric.md` adapt the readme skill by Christopher Bischoff, which adapts Alexey Grigorev, "How to Write a Good README".
- `rubric.md` adapts the `review-readme` command in `cajias/claude-skills` (MIT, Claude Skills Contributors), and the roadmap patterns of `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee).
- `badges.md` adapts the badge references of `rushikeshsakharleofficial/readme-forge` (MIT, Rushikesh Sakharle) and `povvo/claudikins-github-readme-for-perfectionists`.
- `safeguards.md` and `tells.md` adapt plainspoken (this repo), which adapts clarity (MIT, Addy Osmani) and work-humanizer (MIT, Pawel Huryn).

No text is copied from `tavva/ben-claude-plugins`: it has no license file. See `../../../NOTICE.md`.
