# Seed corpus

One JSON file per source class. Positives = vulnerabilities the harness must find;
negatives = correctly-rejected leads it must not report (measures false-positive rate).
`lifecycle: locked` marks a regression-guarded positive that must stay detected. Every
entry is public: synthetic fixtures under `helpers/fixtures/`, dep-CVE lockfiles, or
public-app advisories pinned to a commit. Never add a confirmed vuln from private code.

| File | Source | Target | Notes |
|------|--------|--------|-------|
| `dogfood.json` | synthetic | `fixtures/vulnerable_repo`, `fixtures/absence_repo`, `fixtures/dep_sink_repo`, `fixtures/route_repo` | Two `locked` positives at `vulnerable_repo` (`secrets` app.py:9, `sqli` app.py:18) — both semgrep-detectable, the CI detection gate. The rest are `open`. |
| `absence.json` | synthetic | `fixtures/absence_repo` | Absence-rule positives (`open`) plus one negative. |
| `negatives.json` | synthetic | `fixtures/absence_repo` | Safe variants that must stay silent. |
| `dep_cves.json` | dep-cve | `fixtures/dep_cve_repo` | Pinned vulnerable package versions with a CVE per line of `requirements.txt`. |
| `public_apps.json` | public-app | Juice Shop @ pinned commit | Advisory-backed findings with verified file/line; graded only when cloned (skipped by `--only-local`). |

`local_path` scans a local checkout directly; `commit`/`repo_url` are empty for local
entries. `validate()` skips both target checks when `local_path` is set, so an empty
pair is valid there. `CorpusEntry` tolerates extra keys, so `package`/`cve` on dep-CVE
entries and `lifecycle` are optional per source.
