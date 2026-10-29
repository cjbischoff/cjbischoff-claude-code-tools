# Badges and decorative images

Rules for the `badges` region, and the catalog for `--style fancy`. Adapted from the badge reference of `rushikeshsakharleofficial/readme-forge` (MIT, Rushikesh Sakharle) and the badge-ecosystem reference of `povvo/claudikins-github-readme-for-perfectionists` (MIT, Ethan Lee). URL forms below use slots. Fill each slot from a repo file. Never guess a slot.

## Rules

1. **A badge states a fact.** It is allowed only when the repo shows the fact (the gate column below). No gate, no badge.
2. **One style.** Pick one shields.io `style` value (`flat`, `flat-square`, `for-the-badge`, `plastic`) and use it on every badge. Default `flat`. Keep the style of badges already in the README.
3. **Few badges.** Prefer 3 to 5. More than 7 is clutter.
4. **No vanity badges.** "Made with {language}" informs no decision. Skip it. Skip a stars or downloads badge when the number is small.
5. **No stale or placeholder badges.** A badge whose source is missing, or whose URL has an unfilled slot, is a P1 finding. `check.py` reports the file-backed cases.
6. **Alt text on every image.** It says what the badge shows.
7. **Order by what the reader checks first:** status (CI, coverage), then package (version), then license, then community.
8. **Private package:** no registry badge when the manifest marks the package private. Say how to install from the repo instead.

## Fact-gated catalog

| Badge | URL form | Gate: the repo must show |
|---|---|---|
| CI status | `https://img.shields.io/github/actions/workflow/status/{OWNER}/{REPO}/{workflow-file}` | A workflow file at `.github/workflows/{workflow-file}` and a GitHub remote |
| npm version | `https://img.shields.io/npm/v/{package}` | A `package.json` with a `name` and no `"private": true` |
| PyPI version | `https://img.shields.io/pypi/v/{package}` | A `pyproject.toml` with `project.name`, intended for public release |
| Crates.io version | `https://img.shields.io/crates/v/{crate}` | A `Cargo.toml` with a `package.name` and no `publish = false` |
| Coverage | the coverage service badge URL for the repo | A coverage config and a CI step that uploads results |
| License | `https://img.shields.io/github/license/{OWNER}/{REPO}` | A `LICENSE` file. The badge reads the file, so it cannot disagree with it |
| Release | `https://img.shields.io/github/v/release/{OWNER}/{REPO}` | A GitHub remote and at least one release the user confirms |
| Chat or community | the service's badge URL | A link to the community in the repo (a file, a manifest field) |

`{OWNER}/{REPO}` comes from the git remote URL. With no GitHub remote, skip every GitHub-hosted badge.

Plugin or marketplace repos: a static shields.io `badge/{label}-{message}-{color}` badge may show a fact read from `plugin.json`, such as the plugin name or version. Fill the message from the file. Do not type a version by hand.

## Layout

Put badges in one row directly under the title, inside the `badges` region:

```markdown
<!-- readme-keeper:start badges -->
[![{alt}]({badge-url})]({link-target}) [![{alt}]({badge-url})]({link-target})
<!-- readme-keeper:end badges -->
```

The link target is the page the badge describes (the workflow run page, the registry page, the `LICENSE` file).

## Decorative images (`--style fancy` only)

Off by default. Decorative images call third-party hosts when a reader views the README. Tell the user that before adding any. Each image goes inside the `badges` region. Each has a fact gate. A failed gate means skip the image and say why.

| Image | URL form | Gate |
|---|---|---|
| Typing-SVG banner | `https://readme-typing-svg.demolab.com/?lines={url-encoded-lines}` plus optional `font`, `color`, `width`, `height` | The text lines come from the README's own opening or the manifest description. Never invent a tagline. Four lines at most |
| Capsule-render divider | `https://capsule-render.vercel.app/api?type=waving&section=header&height={n}&color={hex}` | None beyond the user opting in. Keep the height small, and set alt text |
| Star-history chart | `https://api.star-history.com/svg?repos={OWNER}/{REPO}&type=Date` | A public GitHub remote. Confirm with the user that the repo is public. A repo with few stars shows a weak chart: warn the user |
| Contributors grid | `https://contrib.rocks/image?repo={OWNER}/{REPO}` | A public GitHub remote, as above, and more than one contributor in `git log` |

Image rules:

- Use the badge hosts above only. Do not add other hosts.
- Colors come from the user's choice or the project's existing colors. If neither exists, use one neutral color for all images.
- Keep the page readable with images blocked: the title and opening must work without them.
- Light and dark themes: avoid an image that disappears on one theme. Use a `<picture>` element only when the project already ships both logo files.
- A banner or logo file from the repo is better than a hosted one. Use a hosted image only when no repo file exists.
