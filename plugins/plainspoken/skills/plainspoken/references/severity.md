# Severity tiers

The single list of tier membership. `review.md`, `deep.md`, and the lens agents point here. No other file repeats these lists. Pattern names match the section names in `rewrite.md` and the lists in `tells.md`.

## P0: credibility

A reader who sees one of these stops trusting the piece.

- Chat residue and sycophancy
- Knowledge-cutoff disclaimers
- Acknowledgment loops
- Reasoning-chain residue
- Vague authority
- Importance claimed for a routine event

## P1: obvious machine texture

- Stock AI word clusters
- Pause-and-point and "Let's" openers
- Contrast with a claim nobody made
- Synonym cycling
- Formulaic openings
- Em dashes above 1 per 1,000 words, when the writer's sample does not use them
- Bold sprinkled on phrases
- Rhetorical-question openers
- Triads by reflex
- Analogy scaffolding
- False breadth
- False ranges
- Social-post openers
- Notability lists
- "Challenges and future prospects" boilerplate
- Orphaned list signals
- Conclusion before setup

## P2: polish

- Restating closers and generic conclusions
- Uniform rhythm
- Copula displacement
- Filler transitions
- Stacked hedges
- Labels that say nothing
- Title case against house style
- Point-of-view drift
- Emoji decoration
- Curly quotes
- Predicate hyphens
- An unexpanded acronym
- Wordy constructions
- Redundant pairs
- Defense phrases
- Summary paragraphs
- Section mismatch

## Safeguards are not a tier

A safeguard violation is not a severity. A finding whose fix would break a safeguard in `SKILL.md` is dropped, not ranked. Examples: a fix that adds a fact, removes a qualifier that carries the writer's certainty, or overrides the writer's sample.

## Casual text

For Slack, DMs, and quick internal notes, report P0 findings only. Say that P1 and P2 findings were skipped for the register. The `rewrite` genre notes for Slack do not change.
