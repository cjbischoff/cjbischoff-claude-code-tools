# Architecture

**Analysis Date:** 2026-09-05

## System Overview

This is a Claude Code **plugin marketplace** containing exactly one plugin: **sec-overlay**, an agentic security-audit harness. The repo enforces its own governance (prek hooks, Conventional Commits, folder README rules) to keep the marketplace distributable.

The system has two architectural layers:

1. **Marketplace layer** (repo root) — Plugin discovery, governance, CI/CD, docs, wiki
2. **Plugin layer** (`plugins/sec-overlay/`) — The distributed security-audit tool with Python deterministic core + LLM subagent orchestration

## Architectural Patterns

### Layered Pipeline (sec-overlay core)

The audit pipeline is a strict sequential pipeline with deterministic and LLM phases interleaved:

```
Preflight → Begin Pass → Context Ingest → T1 Substrate → Recon → Architecture → Threat Model
  → Prefilter → Investigate → Dedupe → Cluster → Critic → Adversarial Validate
  → Calibrate → Patch → Verify → Gate → Red Team → Report
```

Each phase writes artifacts to disk and passes a workspace handle. Deterministic phases are pure Python; LLM phases spawn Claude Code subagents with structured prompts.

### Gate-Adversary Pattern

Every analysis phase that produces findings or context consumed by a later phase has an **adversary gate**:

```
Phase output → Deterministic pre-check (phase_gate.run_phase_checks)
                 refused citations → REJECT (no agent), log reason
                 resolved → Independent adversary (opus, different family, fresh context)
               Only battle-tested claims flow forward
```

This applies to: recon, architecture, threat-model, context-ingest.

### Deterministic Core (stdlib-only)

**Constraints enforced by ADR-2026-08-04:**
- Zero runtime dependencies in `pyproject.toml`
- No Anthropic SDK or any direct API dependency
- `models.py` and `evidence.py` frozen (byte-mirrored by parallel Go port)
- Tool-receipt confirmation bar never bypassed
- Correlation: read-only over member repos; sidecars byte-identical

### Command-Plugin Pattern (Plugin)

The plugin installs one slash command (`/sec-overlay:audit`) and one verb (`review`). Both are thin CLI wrappers around:

```
uv run python -m sec_overlay.cli <verb> --target <path> --workspace <path> --config <rules>
```

The `review` verb has a three-phase lifecycle:
1. **Prepare** — Write review plan + prompts for each changed file
2. **Dispatch** — Spawn review-file subagents in waves (up to `--concurrency`, default 8)
3. **Consume** — Run gate chain: position gate → profile filter → reflection filter → receipt gate

## Data Flow

### Audit Data Flow

```
Target Codebase
    |
    v
[Preflight] → Installs/vendors missing tooling
    |
    v
[Begin Pass] → Pins SHA, increments pass counter
    |
    v
[C1 Context-ingest] → kb/context.json (sonnet → opus adversary)
    |
    v
[T1 Substrate] → kb/graph.json (no LLM: structural_index + call-edge heuristic + osv/secrets/crypto facts)
    |
    v
[Recon] → kb/scan-profile.json (sonnet → opus phase adversary + opus recall adversary)
    |
    v
[Architecture] → architecture/ tree: C4 diagrams, arc42.md (sonnet → deterministic diagram_gate + ste_lint)
    |
    v
[Threat Model] → threat-model/ tree: dfd.mmd, attack-sequences/, STRIDE findings (sonnet → deterministic gate)
    |
    v
[Prefilter] → {candidates, backends_run, skipped, failed, excluded} (deterministic SAST)
    |
    v
[Investigate] → raw/rejected/A-#### findings (sonnet, parallel per attack class)
    |
    v
[Dedupe] → deduplicated findings (deterministic)
    |
    v
[Cluster] → systemic clusters (deterministic, groups >=3 same-class same-sink)
    |
    v
[Critic] → production viability assessment (sonnet)
    |
    v
[Adversarial Validate] → confirmed/rejected (opus, different family)
    |
    v
[Calibrate] → risk_score (deterministic)
    |
    v
[Patch] → patch_diff (opus)
    |
    v
[Verify] → fixed/verified-static (deterministic)
    |
    v
[Gate] → findings_gate (deterministic)
    |
    v
[Red Team] → runtime_disposition, runtime_test (sonnet + opus adversary)
    |
    v
[Report] → report.sarif + report.md + coverage-ledger.json (deterministic)
```

### Review Data Flow

```
Diff (base..head)
    |
    v
[Prepare] → review_plan.json + review_prompts/*.md
    |
    v
[Dispatch] → review-file subagents (waves of 3-4) → recorded agent returns
    |
    v
[Prepare Reflection] → reflection_plan.json + reflection_prompts/*.md
    |
    v
[Dispatch Reflection] → review-filter subagents (waves of 3-4) → recorded verdicts
    |
    v
[Consume] → Position gate → apply_profile → reflection filter → receipt gate → report.md + SARIF
```

## Entry Points

| Entry Point | Type | Purpose |
|-------------|------|---------|
| `plugins/sec-overlay/commands/audit.md` | Slash command | `/sec-overlay:audit` |
| `plugins/sec-overlay/skills/sec-overlay/SKILL.md` | Skill playbook | Agentic audit instructions (the skill that executes the pipeline) |
| `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/cli.py` | Python CLI | `uv run python -m sec_overlay.cli scan|audit|review` |
| `plugins/sec-overlay/skills/sec-overlay/agents/` | Agent prompts | 20+ agent definition files for LLM subagents |
| `.claude-plugin/marketplace.json` | Marketplace manifest | Plugin discovery endpoint |
| `scripts/hooks/` | Git hooks | `prek` hook scripts for governance |

## Key Abstractions

### Workspace (`sec_overlay/workspace.py`)
Filesystem-based workspace manager. All audit artifacts resolve under a per-repo sidecar (`<target>/.sec-overlay/<slug>/`). Never writes to the target's tracked tree.

### State (`sec_overlay/state.py`)
Campaign state: pinned SHA, pass counter, stage tracking, serialized as `state.json`.

### Scan Profile (`kb/scan-profile.json`)
Output of recon phase. Defines attack surface, agents to spawn, role inference. Validated by `load_profile`.

### Coverage Ledger (`kb/coverage-ledger.json`)
Maps attack surface × finding status. Built by report phase. Blocks `completeness == complete` when classes lack confirmed/NDT findings.

### Route Census (`sec_overlay/route_census.py`)
Deterministic inventory of codebase routes/functions. Runs before recon so an unnamed route appears as a gap.

### Finding Schema (`references/finding.schema.json`)
JSON schema for normalized findings. Carries `fingerprint()`, status, disposition, risk score, and `open_questions`.

## Integration Points

- **SAST backend integration** — semgrep (rulesets), CodeQL (query packs), SCA (first-party), secrets (first-party), crypto (first-party)
- **CI/CD integration** — GitHub Actions workflow files, Dependabot config
- **Plugin install** — Claude Code plugin runtime (installs skills, agents, commands from `plugins/sec-overlay/`)
- **OpenWiki** — AI wiki generator; reads codebase, writes `openwiki/` with its own gitignore

## Non-Patterns (deliberately avoided)

- No microservices or server architecture
- No web framework
- No external database
- No message queue or event bus
- No caching layer
- No authentication/authorization system
- No frontend/UI
