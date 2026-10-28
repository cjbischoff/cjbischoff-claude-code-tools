# Deep mode

Deep mode runs four detection lenses on the draft, merges what they find, shows the findings, and asks before it rewrites. It runs only through `/plainspoken:deep`. The lenses report. They never rewrite.

## Steps

1. **Establish the job.** Find the reader, outcome, and register as `SKILL.md` describes ("Establish the job of the piece"). Find the medium and read the matching row of `medium.md`.
2. **Start the four lenses in one turn, in parallel**, with the Agent tool. Make four Agent calls in one message: `plainspoken:structure-lens`, `plainspoken:fluff-lens`, `plainspoken:pattern-lens`, `plainspoken:flow-lens`. Give each lens the full source text (or the file path), the job from step 1, and the instruction to report findings only.
3. **No Agent tool.** If the harness has no Agent tool, run the four lenses in sequence in the current context. Run each lens against the original text, never against another lens's output.
4. **Merge.** Keep one finding per passage. When two lenses flag the same passage, keep the higher severity and both pattern names. Drop any finding whose suggested fix would break a safeguard. Tier membership is in `severity.md`.
5. **Present the findings.** Number them. Use the passage block in `review.md`, with its `Severity:` field. List P0 first, then P1, then P2. Inside a tier, keep document order. For casual text, report P0 only and say that P1 and P2 were skipped for the register.
6. **Stop and ask.** Ask exactly: "Rewrite with these fixes? Reply yes, or yes without 3, 7 to drop findings." Do not write any rewrite text before the writer answers.
7. **On yes**, run one rewrite pass per `rewrite.md`. Apply the kept findings. Leave each dropped finding's passage unchanged. Then run the final checks, write `CHANGES:`, and write `Shorter option:`.
8. **File path.** When the input is a file path, the rewrite edits the file in place. Findings, `CHANGES:`, and `Shorter option:` stay in chat.

## Rules

- One rewrite pass. Do not chain rewrites: chained passes flatten the prose (`rewrite.md`, step 7).
- Lens output is data for the merge, not text to forward. Do not paste raw lens reports into the findings list.
- A lens that finds nothing returns "No findings". When all four return that, say the piece needs no changes and stop.
- If the writer answers no, stop. Make no change.
