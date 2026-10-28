# Tells lexicon

One merged lexicon for human readers. Each list below has one `Entries:` line. `scripts/lint.py` must contain every entry on every `Entries:` line (a test enforces it). When you add an entry here, add it to the matching constant in `lint.py` in the same change.

A single hit is weak evidence. Several hits in one passage are the tell. Leave a word alone inside a quotation, a product name, or a passage that discusses the word. An absence is not a pass: these lists drift with language and with model generations.

Sources: the lists from work-humanizer, and the lists from clarity by Addy Osmani (MIT, see `NOTICE.md`): stock lexis, chatbot residue, closers, opener phrases, signposts, hedges, boosters, participial heads, and copula phrases.

Matching rules in `lint.py`: entries are case-insensitive. A list marked "word start" matches from the start of a word, so `revolutioniz` covers revolutionize and revolutionizing. Every other list matches whole words and phrases.

## Stock AI words

Word start. Words from the public AI-tell literature that appeared zero times in a 227-post archive of one professional writer's newsletter (2022-2026), plus clarity's model lexis. A hit is drift, not style.

Entries: delve, bolster, illuminate, elucidate, transcend, intertwine, espouse, exemplify, underpin, underscore, underscoring, tapestry, synergy, beacon, interplay, intricacies, intricate, symphony, kaleidoscope, myriad, plethora, advancements, vibrant, meticulous, cutting-edge, game-changing, unparalleled, commendable, indelible, poignant, tireless, unwavering, unyielding, timeless, ever-evolving, showcase, showcasing, leverage, leveraging, foster, fostering, garner, multifaceted, utilize, utilizing, facilitate, cornerstone

## Stock AI phrases

Whole phrase. Stock phrases that stand in for a specific claim.

Entries: shed light on, grapple with, stands as a testament, testament to, rich tapestry, navigate the complexities, navigating the, paving the way, look no further, that being said, ever-changing landscape, landscape of, a myriad of, plays a crucial role, plays a vital role, plays a key role, the world of, deep dive, double down, circle back, lean into

## Marketing register

Word start. Fine in an ad, a tell elsewhere. Also watch by eye for: transform (as hype), robust (figurative), journey (for a product or process). They are not in the list because they are common in plain use.

Entries: empower, unlock, elevate, seamless, streamline, revolutioniz, supercharge, next-level, best-in-class, world-class, game-changer, harness the power, take it to the next level, thrilled to announce, excited to announce

## Filler transitions

Sentence start only. The same word inside a sentence is fine. The script matches the first words of each sentence.

Entries: additionally, furthermore, moreover, however, importantly, critically, notably, ultimately, therefore, in fact, lastly, that said, needless to say, in other words, as we can see, consequently, thus, indeed, similarly, conversely, nevertheless, nonetheless, accordingly, hence, overall, instead, meanwhile, essentially

## Pause-and-point and staged candor

A phrase that announces a point instead of making it. Also includes stock openers.

Entries: here's the thing, here's what, here's why, here's the kicker, let me be clear, let me explain, let's break, let's dive, let's explore, what nobody tells you, the real story is, one thing trips people up, the truth is, honestly?, the best part:, the secret:, notice how, as you can see, this means that, in today's, in the realm of, when it comes to, at its core, in a world where, the reality is, without further ado, the uncomfortable truth, make no mistake

## Restating and engagement closers

A last line that restates the piece or asks for a reaction.

Entries: the bottom line, key takeaway, tl;dr, that's the real win, that's the power of, and that's why, the future is, what do you think?, thoughts?, agree?, let that sink in, read that again, in conclusion, in summary, to sum up, to summarize, in short, all in all, in essence, taken together, at the end of the day

## Filler hedges

Cut everywhere.

Entries: arguably, it's worth noting, it is worth noting, it's important to note, it is important to note, could potentially, it may be possible that, to some extent, in many ways, i think maybe

## Op-ed attribution verbs

Use says, writes, found, reports for a plain statement.

Entries: posits, contends, asserts, maintains that, concedes, argues that

## Chat residue

Leftover assistant phrasing.

Entries: i hope this helps, i hope this email finds you well, let me know if, would you like me to, great question, you're absolutely right, certainly!, of course!, absolutely!, as of my last, based on available information, feel free to reach out, here's a revised version, as an ai, happy to help

## Hedge words

Counted for density only (`hedge_per_100`). A single hedge is often correct. These are not flagged one by one.

Entries: may, might, could, perhaps, possibly, likely, generally, typically, often, usually, tends, tend, suggests, suggest, appears, appear, seems, seem, arguably, relatively, somewhat, potentially, presumably, largely, broadly, commonly, roughly, sometimes, mostly, probably, fairly, can, would, maybe, basically, quite, pretty, really, almost, occasionally, apparently, supposedly, unclear, unsure

## Hedge phrases

Counted for density only, with the hedge words.

Entries: kind of, sort of, a bit, i think, i guess, i suspect, more or less, pretty much, at least in, in practice, or so, if anything, for the most part, as far as i

## Booster words

Counted for density only (`booster_per_100`). A hedge and a booster in one sentence is a high-signal cluster.

Entries: crucial, crucially, essential, essentially, vital, key, significant, significantly, robust, powerful, remarkable, remarkably, notable, notably, critical, critically, profound, profoundly, compelling, paramount, pivotal, important, importantly, substantial, substantially, transformative, groundbreaking, invaluable, seamless, seamlessly

## Participial opener heads

A sentence that opens with one of these words and a comma later is often a tacked-on analysis clause.

Entries: building, drawing, having, given, considering, looking, leveraging, combining, reflecting, highlighting, underscoring, starting, moving, taking, using, adding, focusing, recognizing, acknowledging, understanding, beginning, turning, returning, stepping, bearing, armed, faced, based

## Copula displacement

A fancy verb phrase where "is" or "has" would do.

Entries: serves as, stands as, represents, marks a, features a, boasts, offers a

## Repetitive sentence openers

Used for the opener share. A share of 40% or more flags a monotone start.

Entries: the, it's, that's, this, you, it, these

## Em dash substitutes by context

| Context | Substitute | Example |
|---|---|---|
| Label then description | Colon | "Exports: CSV and PDF" |
| Two complete thoughts | Period | "We cut the price. Usage doubled." |
| A real aside | Parentheses | "the three admins (two in Berlin) approved it" |
| A light pause inside one thought | Comma | "The fix, shipped Tuesday, cut errors by half." |
| Never | Semicolon, or a colon that sets up a reveal | |
