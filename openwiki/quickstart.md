---
type: quickstart
title: cjbischoff-claude-code-tools Wiki Quickstart
description: Entry point to the wiki for the cjbischoff-claude-code-tools Claude Code plugin marketplace, with a map of every section and a task-routing table from engineering intent to owning pages, source, tests, and validation.
tags: [quickstart, navigation, marketplace, sec-overlay]
---

# cjbischoff-claude-code-tools wiki

This repository is a **Claude Code plugin marketplace** — a distribution and governance system,
not an application server. It has no HTTP API, no database, and no production runtime. It ships
one plugin, [`sec-overlay`](plugins/sec-overlay/overview.md), an agentic security-audit harness,
from `plugins/sec-overlay/`. Read this page first; it links to everything else.

## Map

- **[marketplace/](marketplace/overview.md)** — the manifest contract, plugin directory layout,
  install path, `${CLAUDE_PLUGIN_ROOT}` resolution, `claude plugin validate .`, and the
  automatic plugin-version-bump rule.
  - [Overview](marketplace/overview.md) — `marketplace.json`, `plugin.json`, install/discovery.
  - [Validation and versioning](marketplace/validation-and-versioning.md) — the validate command
    and the semver bump rule, including which mechanism actually checks it.
- **[governance/](governance/hooks-and-commits.md)** — commit rules and every gate that
  enforces them.
  - [Hooks and commits](governance/hooks-and-commits.md) — branch naming, Conventional Commits,
    the prek doc-update-guard, the GitHub ruleset, and a legacy skill-local hook.
  - [Code review](governance/code-review.md) — CodeRabbit's comment-only role and warning-mode
    pre-merge checks.
- **[plugins/sec-overlay/](plugins/sec-overlay/overview.md)** — the one distributed plugin, in
  depth.
  - [Overview](plugins/sec-overlay/overview.md) — the four principles, three-folder
    architecture, and the four cross-cutting invariants.
  - [Pipeline](plugins/sec-overlay/pipeline.md) — the full phase order, the phase-adversary and
    deterministic arch/tm/artifact gates, tuning knobs, and multi-pass campaigns.
  - [Agents](plugins/sec-overlay/agents.md) — every LLM prompt, producer vs. adversary, and the
    investigate gate ladder.
  - [Helpers](plugins/sec-overlay/helpers.md) — the deterministic Python core, the tiered
    tool-receipt gate, the audit driver, and the module map.
  - [References](plugins/sec-overlay/references.md) — the rule book: prompt constants, the
    architecture/threat-model standards, schemas, CVSS v4.0/crypto policy.
  - [Running an audit](plugins/sec-overlay/running-an-audit.md) — the smoke scan, the driven
    `/sec-overlay:audit` command, the full manual agentic audit, preflight, and env-only test
    failures.
  - [Developing the skill](plugins/sec-overlay/developing-the-skill.md) — tests, linting, the
    bench harness.
  - [Cross-repo correlation](plugins/sec-overlay/cross-repo-correlation.md) — the optional
    multi-repo capability.
- **[operations/](operations/security-automation.md)** — repository-level security automation
  and how this repo runs its own tooling.
  - [Security automation](operations/security-automation.md) — dependency review, Dependabot,
    CodeQL default setup, secret scanning, SHA pinning, least-privilege tokens.
  - [Cursor CodeGuard rule](operations/cursor-codeguard-rules.md) — the one remaining
    always-applied `.cursor/rules/` rule.
  - [OpenWiki refresh](operations/openwiki-refresh.md) — how this wiki itself gets regenerated.

## Task-routing table

| I want to... | Read | Source entrypoints / symbols | Focused tests | Minimal validation |
|---|---|---|---|---|
| Install this marketplace and the plugin | [Marketplace overview](marketplace/overview.md) | `.claude-plugin/marketplace.json`, `plugins/sec-overlay/.claude-plugin/plugin.json` | — | `claude plugin validate .` |
| Add a second plugin | [Marketplace overview](marketplace/overview.md), [Validation and versioning](marketplace/validation-and-versioning.md) | copy `docs/templates/plugin/` to `plugins/<name>/`, fill in `{{PLACEHOLDER}}`s, add a `marketplace.json` entry | — | `claude plugin validate .` |
| Bump a plugin's version correctly | [Validation and versioning](marketplace/validation-and-versioning.md) | `plugins/sec-overlay/.claude-plugin/plugin.json`'s `version` field | — | CodeRabbit's `plugin-version-bump` warning on the PR |
| Make any tracked-file change without breaking a hook | [Hooks and commits](governance/hooks-and-commits.md) | `scripts/hooks/pre-commit-check.sh`, `scripts/hooks/commit-msg-check.sh` | `scripts/hooks/test-pre-commit-check.sh`, `scripts/hooks/test-commit-msg-check.sh` | `bash scripts/hooks/test-pre-commit-check.sh && bash scripts/hooks/test-commit-msg-check.sh` |
| Understand what CodeRabbit will flag | [Code review](governance/code-review.md) | `.coderabbit.yaml` | — | open the PR, wait for the walkthrough comment (`gh pr view <n> --comments`) |
| Run a fast smoke scan of a target | [Running an audit](plugins/sec-overlay/running-an-audit.md) | `sec_overlay.cli.run_scan`, `rules/smoke.yaml` | `helpers/tests/test_cli.py`, `test_cli_e2e.py` | `uv run python -m sec_overlay.cli scan --target <T> --config rules/smoke.yaml --sha <sha>` from `helpers/` |
| Run (most of) an audit with the driver | [Running an audit](plugins/sec-overlay/running-an-audit.md#the-driven-audit-sec-overlayaudit) | `commands/audit.md`, `helpers/sec_overlay/run.py` (`drive`/`advance`), `phases.py` (`PHASE_TABLE`), `driver.py` | `helpers/tests/test_run.py`, `test_driver.py`, `test_phases.py`, `test_command_audit.py` | `uv run python -c "from sec_overlay.run import drive; print(drive('<repo>', config='rules/smoke.yaml'))"` from `helpers/` |
| Run the phases the driver doesn't cover yet (full manual audit) | [Pipeline](plugins/sec-overlay/pipeline.md), [Running an audit](plugins/sec-overlay/running-an-audit.md) | `SKILL.md`, skill `CLAUDE.md` §2 | `helpers/tests/test_preflight.py`, `test_wiring.py` | `uv run python -m sec_overlay.preflight` first, then follow `SKILL.md` phase order |
| Change the tool-receipt gate | [Helpers](plugins/sec-overlay/helpers.md#the-tool-receipt-gate) | `helpers/sec_overlay/evidence.py` (`TIER1_RECEIPTS`/`TIER2_RECEIPTS`), `findings_gate.py` | `helpers/tests/test_evidence.py`, `test_finding_schema.py`, `test_contracts.py` | `uv run pytest tests/test_evidence.py tests/test_finding_schema.py tests/test_contracts.py -q` |
| Edit an agent prompt | [Agents](plugins/sec-overlay/agents.md#editing-rules) | `agents/*.md`, `agents/README.md` | `helpers/tests/test_wiring.py`, `test_docs_invariants.py` | `uv run pytest tests/test_wiring.py tests/test_docs_invariants.py -q`; update `agents/README.md` in the same commit |
| Add a new attack class | [Agents — classes/](plugins/sec-overlay/agents.md#classes--cwe-class-extension-prompts), [References](plugins/sec-overlay/references.md) | `references/attack-classes.md`, `agents/classes/<key>.md`, `helpers/sec_overlay/clsmap.py` | `helpers/tests/test_wiring.py`, `test_clsmap.py` | `uv run pytest tests/test_wiring.py tests/test_clsmap.py -q` |
| Loosen or tighten crypto policy | [References](plugins/sec-overlay/references.md#machine-checked-policy-and-schemas) | `references/approved-crypto-algorithms.yaml`, `helpers/sec_overlay/crypto_policy.py` | `helpers/tests/test_crypto_policy.py` | `uv run pytest tests/test_crypto_policy.py -q` — requires sign-off per the editing rules |
| Change CVSS scoring | [Helpers](plugins/sec-overlay/helpers.md#module-map-grouped-by-job) | `helpers/sec_overlay/cvss.py` (`cvss40_base`), `cvss4_data.py` | `helpers/tests/test_cvss.py`, `test_cvss4_data.py` | `uv run pytest tests/test_cvss.py tests/test_cvss4_data.py -q` |
| Change an architecture/threat-model diagram cap or prose rule | [References](plugins/sec-overlay/references.md) | `references/mermaid-caps.md`, `helpers/sec_overlay/diagram_gate.py`, `ste_lint.py` | `helpers/tests/test_diagram_gate.py`, `test_ste_lint.py`, `test_references_caps.py` | `uv run pytest tests/test_diagram_gate.py tests/test_ste_lint.py tests/test_references_caps.py -q` |
| Correlate findings across multiple repos | [Cross-repo correlation](plugins/sec-overlay/cross-repo-correlation.md) | `helpers/sec_overlay/correlate/cli.py`, `sec_overlay.run.infer_role`/`synthesize_manifest` | `helpers/tests/test_correlate_*.py`, `test_run.py` | `python -m sec_overlay.correlate --manifest <m.json> --out <dir>` |
| Run the full sec-overlay test suite | [Developing the skill](plugins/sec-overlay/developing-the-skill.md) | `helpers/pyproject.toml` | all 91 files under `helpers/tests/` | `uv run pytest -q` from `helpers/` (two env-only failures expected on a clean checkout) |
| Add or change the Cursor secure-coding rule | [Cursor CodeGuard rule](operations/cursor-codeguard-rules.md) | `.cursor/rules/codeguard-1-hardcoded-credentials.mdc` | — | CodeRabbit's `codeguard-reference-audit` finishing-touch on the PR |
| Change a GitHub Actions workflow | [Security automation](operations/security-automation.md) | `.github/workflows/*.yml` | — | `.github/workflows/**` CodeRabbit path instruction (SHA pin + least-privilege `permissions`) |
| Refresh the wiki itself | [OpenWiki refresh](operations/openwiki-refresh.md) | `openwiki/INSTRUCTIONS.md`, `.openwikiignore` | — | `openwiki code --update --print`, or dispatch the `OpenWiki Update` workflow |

## The sec-overlay pipeline in one sentence

Cheap mechanical tools (semgrep, CodeQL, ast-grep, secrets scanning) find *candidates*; sonnet
LLM agents investigate whether each candidate is real through a gate ladder; opus adversaries
on a different model family try to refute every survivor; and a finding can only reach
`confirmed` with a recorded Tier-1 mechanical tool receipt — LLM reasoning alone never confirms.
See
[pipeline](plugins/sec-overlay/pipeline.md) for the full phase order and
[agents](plugins/sec-overlay/agents.md) for the producer-vs-adversary mechanics behind it.

## Backlog — deliberate deferrals

These areas are intentionally out of scope or documented only at the depth needed to orient a
reader, with the reason and source anchor:

- **`docs/superpowers/` and `plugins/sec-overlay/skills/sec-overlay/docs/plans/` +
  `docs/superpowers/`** — historical design specs and implementation plans (e.g.
  `docs/superpowers/specs/2026-08-11-port-sec-overlay-design.md`,
  `plugins/sec-overlay/skills/sec-overlay/docs/plans/2026-08-07-cross-repo-correlation-design.md`).
  Cited in this wiki for *why* a capability exists (see
  [cross-repo correlation](plugins/sec-overlay/cross-repo-correlation.md)), never treated as
  authoritative over current code — per the brief's source-precedence rule, a dated plan never
  overrides current code.
- **`plugins/sec-overlay/skills/sec-overlay/docs/dogfooding/` and `.../docs/gsd/`** — excluded
  by `.openwikiignore`; not walked or documented.
- **`**/fixtures/**` and `**/fixtures_struct/**`** — intentionally vulnerable detector-test
  fixtures (e.g. `helpers/fixtures/`), excluded from OpenWiki, from CodeRabbit review, and from
  CodeQL's default-setup scan (all three for the same reason: seeded findings would bury real
  ones). They exist to exercise the harness's own detectors in `helpers/tests/`; see
  [`SECURITY.md`](/SECURITY.md)'s "Test fixtures" note — this wiki documents their existence and
  purpose only, never their contents.
- **`helpers/bench/corpus_seed/`** — gitignored, local-only labelled-corpus data for the
  dev-only [bench harness](plugins/sec-overlay/developing-the-skill.md#the-bench-harness-dev-only-not-part-of-an-audit);
  not part of any audit run and not present in this repository's tracked source.
- **The top-level `/skills/` directory** (`skills/mermaid-diagrams/`, `skills/write-connector/`)
  — this is **OpenWiki's own** tooling-authoring skill library, unrelated to the distributed
  `sec-overlay` plugin's `plugins/sec-overlay/skills/sec-overlay/`. It is untracked in the root
  README's Directory Guide and not referenced by `marketplace.json` or any `plugin.json`. Out of
  scope for this marketplace/governance/sec-overlay wiki.
- **GitHub ruleset configuration** — referenced throughout (see
  [hooks and commits](governance/hooks-and-commits.md#the-github-ruleset-on-main)) but is a
  server-side GitHub setting, not a file in this repository; described qualitatively from the
  root README/CLAUDE.md's own statements about it.
- **`.planning/`** — a GSD (Get Stuff Done) planning bootstrap (`PROJECT.md`, `REQUIREMENTS.md`,
  `ROADMAP.md`, `STATE.md`, synthesized intel, an ingest-conflict report, and an onboarding
  summary) added in this range. The brief's out-of-scope list names "GSD planning notes" as
  excluded from documentation; it is an agent-planning artifact about *how* work on this repo
  gets sequenced, not a product surface, and is not cited elsewhere in this wiki.
