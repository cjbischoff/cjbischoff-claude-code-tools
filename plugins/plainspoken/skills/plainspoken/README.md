# skills/plainspoken/

The `plainspoken` skill. One skill with six modes: `interview`, `rewrite`, `review`, `brief`, `lint`, and `deep`. `deep` runs only through `/plainspoken:deep`: four read-only lens agents (in `../../agents/`) report findings in parallel, then one rewrite follows the writer's answer. `references/severity.md` holds the single P0/P1/P2 list that `review`, `deep`, and the agents share. `SKILL.md` routes a request to a mode, holds the 8 shared safeguards and the output footer, and loads only the reference that mode needs.

## Layout

```text
skills/plainspoken/
├── README.md         this file
├── SKILL.md          router, safeguards, footer; under 200 lines
├── references/       rule files per mode and medium, plus the tells lexicon (see references/README.md)
└── scripts/
    └── lint.py       mechanical prose diagnostics, stdlib only
```

## Attribution

- Interview, review, medium, and long-form rules, the mode router, and the lint metrics adapt [clarity](https://github.com/addyosmani/clarity) by Addy Osmani (MIT). The license text is in `NOTICE.md` at the plugin root.
- The business formats in `references/brief.md` come from `brief-sharp` by Christopher Bischoff.
- The severity tiers, pattern families, tighten tests, and deep mode draw on anti-slop-editor by Christopher Bischoff, which draws on blader/humanizer (MIT) and Wikipedia "Signs of AI writing". No text is copied. See `NOTICE.md` at the plugin root.
- The rewrite rules, tell lists, and mechanical sweep adapt [work-humanizer](https://github.com/phuryn/work-humanizer) by Pawel Huryn (MIT). The license text is in `NOTICE.md` at the plugin root.
