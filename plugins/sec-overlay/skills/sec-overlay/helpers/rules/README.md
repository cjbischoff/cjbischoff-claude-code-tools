# Vendored SAST rules

## Semgrep
Vendored (not fetched at scan time) so scans need no network. Layout:
`rules/semgrep/<language>/**.yaml`. Vendor or refresh with:

    git clone --depth 1 https://github.com/semgrep/semgrep-rules \
      skills/sec-overlay/helpers/rules/semgrep

Recon selects the `<language>` subdirs that match the target. `rules/smoke.yaml`
is the offline smoke-test ruleset used by the deterministic test fixture only.

## CodeQL
Uses the standard query suites from the CodeQL bundle (default:
`security-extended`) — no custom rules authored. Ensure packs are present:

    codeql pack download codeql/go-queries codeql/python-queries

## Absence rules

`rules/absence/` holds tracked, first-party semgrep rules. Never move a first-party rule under
`rules/semgrep/` — that directory is a gitignored clone `preflight.py` recreates, so anything
placed there is deleted and never committed.

An absence rule flags a dangerous construction that lacks its safe option. A plain `pattern`
rule cannot express this: it fires on every call site, safe ones included. The idiom pairs
`patterns` (the dangerous construction) with `pattern-not` (the safe option, required absent):

    patterns:
      - pattern: rego.New(...)
      - pattern-not: rego.New(..., rego.Capabilities(...), ...)

Every rule in the pack must set `metadata.cls` to an attack-class key from `clsmap.py`. The
prefilter routes a semgrep hit by that field; a rule with no `cls` routes nowhere.

If a `pattern-not` fails to suppress the safe fixture, narrow the pattern until the safe site
stays silent. Never weaken the assertion instead — a rule that fires on fixed code trains the
reviewer to ignore the pack.
