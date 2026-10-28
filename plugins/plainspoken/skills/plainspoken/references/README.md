# references/

Rule files the `plainspoken` skill loads one mode at a time. `SKILL.md` holds the router, the shared safeguards, and the footer. Each file here holds the detail for one mode or medium.

| File | Holds | Loaded by |
|------|-------|-----------|
| `interview.md` | The hybrid interview: one unorganized take, at most 5 follow-up questions, composing from the writer's words, notes and voice-memo handling, the provenance note | `interview` |
| `rewrite.md` | Rewrite steps with the diagnosis order, what not to change, tells A-G, the structure and flow checklist, "sound like a person", tighten tests, edge rules, genre notes, final checks, the shorter option | `rewrite`; also `review` (pattern names) and `interview` (final checks) |
| `review.md` | Piece-level diagnosis and passage-level findings with severity and verdicts | `review` |
| `severity.md` | The P0/P1/P2 tier membership list, the rule that safeguard violations are not a tier, and the casual-text rule | `review`, `deep`, and the lens agents |
| `deep.md` | The deep-mode steps: four parallel lens agents, merge, numbered findings, the question before the rewrite, one rewrite pass | `deep` (command only) |
| `brief.md` | The four business formats, detection table, hard limits, never-change and rewrite-aggressively rules, tone by audience, CHANGES rules | `brief` |
| `medium.md` | One row per medium: what to optimize for, preserve, and avoid | Any mode, when the piece is academic, legal, medical, safety, reference, procedural, marketing, email, UI, speech, slides, fiction, or narrative |
| `longform.md` | The editing pass for authored long-form prose | Any mode, when the piece is an essay, article, newsletter, talk, speech, or narrative |
| `tells.md` | The merged lexicon of AI tells: word lists, phrase lists, dash substitutes. It is enforced in sync with `../scripts/lint.py` by a test, so change both together | `rewrite` and `review` (word lists), `lint` (reading hits) |

`interview.md`, `review.md`, `medium.md`, and `longform.md` adapt material from clarity (MIT, Addy Osmani). `rewrite.md`, `interview.md`, and `tells.md` adapt material from work-humanizer (MIT, Pawel Huryn). The pattern families, tiers, and tighten tests in `severity.md`, `deep.md`, `rewrite.md`, and `tells.md` come from anti-slop-editor by Christopher Bischoff, which draws on blader/humanizer (MIT) and Wikipedia "Signs of AI writing". No text is copied from it. See `../../../NOTICE.md`.
