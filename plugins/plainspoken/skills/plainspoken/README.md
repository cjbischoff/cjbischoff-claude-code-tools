# skills/plainspoken/

The `plainspoken` skill. One skill with five modes: `interview`, `rewrite`, `review`, `brief`, and `lint`. `SKILL.md` routes a request to a mode, holds the 8 shared safeguards and the output footer, and loads only the reference that mode needs.

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
- The rewrite rules, tell lists, and mechanical sweep adapt [work-humanizer](https://github.com/phuryn/work-humanizer) by Pawel Huryn (MIT). The license text is in `NOTICE.md` at the plugin root.
