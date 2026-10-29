# Tells lexicon

A small subset of the plainspoken prose-tell lists, for `check.py --prose`. Adapted from plainspoken, which carries lists from clarity (MIT, Addy Osmani) and work-humanizer (MIT, Pawel Huryn). See `NOTICE.md`.

Each list below has one `Entries:` line. `scripts/check.py` must contain every entry on every `Entries:` line (a test enforces it). When you add an entry here, add it to the matching constant in `check.py` in the same change.

A single hit is weak evidence. Leave a word alone inside a quotation, a product name, or a passage that discusses the word. `check.py --prose` reports each hit as P2.

Matching rules in `check.py`: entries are case-insensitive. A list marked "word start" matches from the start of a word, so `revolutioniz` covers revolutionize and revolutionizing. A list marked "sentence start" matches only the first words of a sentence.

## Stock AI words

Word start. Words that stand in for a specific claim.

Entries: delve, bolster, tapestry, synergy, beacon, interplay, intricacies, intricate, vibrant, meticulous, cutting-edge, game-changing, unparalleled, ever-evolving, showcase, showcasing, leverage, leveraging, foster, fostering, multifaceted, utilize, utilizing, facilitate, cornerstone, realm, paradigm, holistic, impactful, paramount, groundbreaking, transformative

## Marketing register

Word start. Fine in an ad, a tell in a README.

Entries: empower, unlock, elevate, seamless, streamline, revolutioniz, supercharge, next-level, best-in-class, world-class, game-changer, harness the power

## Filler transitions

Sentence start only. The same word inside a sentence is fine.

Entries: additionally, furthermore, moreover, importantly, notably, ultimately, consequently, in fact, needless to say, in other words, essentially, indeed

## Em dash

No `Entries:` line. `check.py --prose` reports each em dash character (U+2014). Use a colon, a period, parentheses, or a comma instead.
