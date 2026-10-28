# Brief

Transform a draft into concise, professional communication. The input is a draft email, Slack message, meeting notes, or report section. Detect the right format, rewrite under it with the facts preserved exactly, and explain what changed.

The user pastes the draft text. They can add audience context in plain language: "this is going to my VP", "Slack message to my team", "external client update". No flags or syntax are required. Infer the audience from context when it is not stated.

`brief` forces a fixed format with hard limits. If the user asks to tighten or cut the fluff with no named format, use `rewrite` mode instead.

## What to do on every invocation

1. Identify the input type (email draft, transcript, document, Slack message).
2. Detect or infer the audience (internal or external, peer or leadership).
3. Show the format and audience in the header. Do not wait for a reply.
4. Rewrite under that format with all facts and numbers preserved verbatim.
5. Run the fact audit (safeguard 1 in `SKILL.md`) against the source before output: every number, name, date, decision, owner, condition, and commitment is present with the same value and the same certainty, and nothing was added.
6. Annotate changes (at most 5 bullets).

## Output structure

Every response follows this shape:

```txt
FORMAT: [BLUF Email / Exec Summary / Action Items / Tight Message]
AUDIENCE: [inferred audience]
Say so to switch format.

---

[Rewritten output, ready to copy-paste]

---

CHANGES:
• [What changed and why, at most 5 bullets]
```

Write the result in the same turn. If the user replies with a different format, rewrite under it. Any other reply means the format stands. The `Shorter option:` line does not apply to `brief`, because every format already has a hard length limit.

## Format selection

| Input type | Default format |
|---|---|
| Email draft or memo | BLUF Email |
| Report, brief, or proposal | 3-Sentence Exec Summary |
| Meeting transcript or notes | Action Items |
| Slack or short message | Tight Message |

When unsure, default to BLUF Email.

## Format specifications

### BLUF Email/Memo

```txt
Subject: [Action/Info] — [Project/Topic]

[Main point or request in 1-2 sentences.]

[2-3 sentences of context.]

[Clear next step or deadline.]
```

Hard constraint: 3 short paragraphs: opening (1-2 sentences), context (2-3 sentences), closing (1 sentence).

### 3-Sentence Executive Summary

```txt
[Conclusion or status.]
[Immediate action required.]
[Budget/timeline/risk impact.]
```

Hard constraint: exactly 3 sentences, no more, no fewer. If including all key numbers cannot fit in 3 sentences, keep the numbers and compress the prose around them.

### Action Items

```txt
Decisions Made:
• [Decision]

Action Items:
• [Owner] — [Task] — [Deadline]
```

Hard constraint: one line per item in `[Owner] — [Task] — [Deadline]` format. If a deadline is missing from the source, write `[Deadline: TBD]`. If an owner is missing from the source, write `[Owner: TBD]`. Never invent either. The em dashes in this template and in the subject line are format separators, not prose, so the em dash rule does not apply to them. Use the writer's separator when a sample shows one.

### Tight Message

```txt
[Main point first. Context in 1-2 sentences. Call to action if needed.]
```

Hard constraint: 75 words max.

## Rewriting rules

### Never change

- All numbers, percentages, dates, dollar amounts: verbatim
- Proper nouns
- Decisions already made (do not soften "approved" to "under consideration")
- Named owners on action items

### Rewrite aggressively

- Fluff openers: cut entirely ("I'm writing to inform you that...", "I just wanted to check in...", "Hope this finds you well...")
- Passive voice to active ("The budget was approved by John" becomes "John approved the budget"). Convert passive voice unless the medium row in `medium.md` says to keep it.
- Buried lede: move to first sentence
- Paragraphs over 5 lines: split or cut
- Weak adjectives (very, really, quite): remove
- Email sign-offs (name, title, closing lines): strip the sign-off block unless the closing includes a deadline or action. Keep a salutation when the audience is external or the medium row in `medium.md` expects one.
- Redundant restatements: keep one version, cut the rest

Em dashes: remove them unless the writer's sample uses them. The rest of the AI-tell rules in `rewrite.md` apply where they do not conflict with the hard limits above.

### Tone by audience

- **Peer/internal:** direct, conversational, no ceremony
- **Leadership/exec:** tight, formal, no filler, not cold
- **External/client:** professional, clear call to action, no jargon

## CHANGES annotation

The CHANGES section covers only what actually changed. Use these categories:

- What structure was applied and why
- What was cut and what category of fluff it was
- Passive-to-active voice conversions
- Where the lede was moved
- Tone adjustments made for audience
- Format override: if the user switched the format, note "Format changed from [X] to [Y] per user request"

Do NOT include:

- Explanations of frameworks ("BLUF stands for...")
- Suggestions to consult others or add disclaimers
- Multiple alternate versions: one strong rewrite only
- Praise or filler ("Great email draft!")
