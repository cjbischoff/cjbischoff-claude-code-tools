# references/

Rule files the `plainspoken` skill loads one mode at a time. `SKILL.md` holds the router, the shared safeguards, and the footer. Each file here holds the detail for one mode or medium.

| File | Holds | Loaded by |
|------|-------|-----------|
| `tells.md` | The merged lexicon of AI tells: word lists, phrase lists, dash substitutes. It is enforced in sync with `../scripts/lint.py` by a test, so change both together | `rewrite` and `review` (word lists), `lint` (reading hits) |
