# Directory Structure

**Analysis Date:** 2026-09-05

## Root Directory Layout

```
cjbischoff-claude-code-tools/
├── .claude-plugin/          # Marketplace manifest (plugin registry entry point)
│   └── marketplace.json     # Lists all plugins available for install
├── .github/                 # CI/CD configuration
│   ├── workflows/           # GitHub Actions: tests, dependency review, OpenWiki update
│   ├── dependabot.yml       # Weekly dependency updates
│   └── codeql/              # CodeQL config with path exclusions
├── .planning/               # GSD planning artifacts (PROJECT.md, ROADMAP.md, STATE.md, etc.)
├── plugins/                 # One directory per distributable plugin
│   └── sec-overlay/         # The only plugin — agentic security-audit harness
├── scripts/                 # Repo-level tooling
│   ├── hooks/               # Git hook scripts (prek: commit-msg, pre-commit)
│   └── openwiki-history-digest.sh
├── docs/                    # Design specs, implementation plans, decisions
│   ├── decisions/           # Architecture Decision Records (ADR)
│   ├── templates/plugin/    # New-plugin skeleton ({{PLACEHOLDER}} markers)
│   └── superpowers/         # Implementation plans and design specs (historical, delivered)
├── openwiki/                # Generated AI wiki (do not hand-edit except INSTRUCTIONS.md)
├── .coderabbit.yaml         # CodeRabbit review config (15KB)
├── .pre-commit-config.yaml  # prek hook config
├── .env.example             # Local OpenWiki env template
├── .openwikiignore          # OpenWiki read boundary
├── .gitignore               # Caches, venvs, secrets, vendored semgrep-rules
├── .cursor/rules/           # Cursor IDE rules (codeguard secrets checker)
├── AGENTS.md                # OpenWiki pointer for coding agents
├── CLAUDE.md                # Governor: branch rules, commit format, changelog routing, governance
├── README.md                # Marketplace README (user-facing)
├── CHANGELOG.md             # Repo-level changelog (83KB)
└── SECURITY.md              # How to report vulnerabilities
```

## Plugin Directory: `plugins/sec-overlay/`

```
plugins/sec-overlay/
├── .claude-plugin/
│   └── plugin.json          # Plugin manifest: name, description, version
├── commands/
│   ├── audit.md             # /sec-overlay:audit slash command
│   └── README.md            # Command directory docs
├── skills/
│   └── sec-overlay/         # The skill that implements the audit harness
│       ├── SKILL.md         # Skill playbook (736 lines — authoritative reference)
│       ├── CLAUDE.md        # Maintainer manual: prerequisites, rules, workspace artifacts
│       ├── agents/          # LLM subagent prompts (20+ agents)
│       │   ├── recon.md, architecture.md, threat-model.md
│       │   ├── investigate.md, critic.md, validate.md, patch.md
│       │   ├── redteam.md, redteam-adversary.md
│       │   ├── context-ingest.md, context-adversary.md
│       │   ├── phase-adversary.md, recall-adversary.md
│       │   ├── review-file.md, review-filter.md
│       │   └── ...
│       ├── references/      # Structured reference data
│       │   ├── prompt-constants.md    # 12 verbatim blocks (DIAGRAM_STYLE, FIELD_OWNERSHIP, etc.)
│       │   ├── architecture-standards.md
│       │   ├── threat-model-standards.md
│       │   ├── attack-classes.md
│       │   ├── dependency-sinks.json
│       │   ├── finding.schema.json
│       │   ├── finding-template.md
│       │   ├── coverage-ledger.schema.json
│       │   ├── scan-profile.schema.json
│       │   ├── route-frameworks.json
│       │   └── mermaid-caps.md
│       ├── rules/           # Rule documentation by language (40+ files)
│       │   ├── rule_docs/   # Per-language rule docs (terraform.md, python.md, go.md, etc.)
│       │   ├── README.md
│       │   ├── absence/     # First-party absence-detection rules
│       │   └── smoke.yaml   # Minimal demo ruleset
│       └── helpers/         # Python deterministic core
│           ├── pyproject.toml      # Python 3.12+, stdlib-only, no runtime deps
│           ├── uv.lock              # Lockfile (pytest, ruff, ty only)
│           ├── sec_overlay/        # Python package (~100 modules)
│           ├── tests/              # ~150 test files
│           ├── fixtures/           # Test fixtures (vulnerable repos, golden data)
│           ├── bench/              # Benchmarking harness
│           └── rules/              # Semgrep rules (vendored clone, gitignored)
├── README.md                # User-facing plugin docs (install, prerequisites, quick start)
├── CLAUDE.md                # Maintainer manual (development commands, folder-README rule)
├── CHANGELOG.md             # Plugin changelog (145KB — extensive history)
├── action.yml               # GitHub Action definition (optional)
└── SKILL.md                 # (at skill level, not plugin root)
```

## Python Core: `helpers/sec_overlay/` (~100 files)

Key modules:

| File | Purpose |
|------|---------|
| `cli.py` | CLI entry point (`scan|audit|review` verbs) |
| `run.py` | Full audit pipeline driver |
| `workspace.py` | Filesystem workspace manager (sidecar pattern) |
| `state.py` / `campaign.py` | Campaign state management (pass counter, stages) |
| `graph.py` | KB graph builder (structural index + call-edge heuristic) |
| `prefilter.py` | SAST backend dispatch (semgrep, CodeQL, SCA, secrets, crypto) |
| `preflight.py` | Tool installation/vendoring before scanning |
| `investigate.py` / `sast.py` | Finding normalization |
| `dedupe.py` | Finding deduplication |
| `cluster.py` | Systemic finding clustering |
| `scoring.py` / `calibrate.py` | Risk scoring |
| `verify.py` | Patch verification (re-scan) |
| `findings_gate.py` | Output quality gate |
| `report.py` | SARIF + Markdown report generation |
| `dedupe.py` / `cluster.py` | Finding normalization pipeline |
| `review_agent.py` / `review_findings.py` | Review pipeline core |
| `reflection.py` | Retract-only reflection filter |
| `route_census.py` / `route_control.py` | Route/capability inventory |
| `phase_gate.py` | Deterministic pre-check for analysis phases |
| `diagram_gate.py` / `ste_lint.py` | Architecture/threat-model diagram quality gates |
| `cost.py` | Token usage recording |
| `correlate/` | Cross-repo correlation (read-only, rethreshold engine) |
| `sca.py` | Software Composition Analysis (OSV, secrets, crypto) |
| `secrets.py` | Secrets detection |
| `crypto_policy.py` | Approved algorithm enforcement |
| `models.py` / `evidence.py` | Frozen contract: finding datamodel (byte-mirrored by Go port) |
| `envelope.py` | Receipt envelope for tool output |
| `fingerprint.py` | Finding fingerprinting (identity function, never changed) |
| `finding_schema.py` | JSON schema validation for findings |
| `fix_and_gates.py` | Fix assessment + gate orchestration |
| `postflight.py` | Post-run cleanup/verification |
| `pr_poster.py` | PR comment poster (for CI findings) |
| `profile.py` | Scan profile loading/validation |
| `prompts.py` / `prompt_tokens.py` | Prompt template utilities |
| `prove.py` | Evidence trace construction |
| `redactor.py` | Output redaction |
| `redteam.py` | Red team plan renderer |
| `render_util.py` | Report rendering utilities |
| `test_*.py` (tests/) | ~150 test files covering every core module |

## Key File Conventions

- **Folder README rule:** Every directory in the Directory Guide (README.md) has its own `README.md`. A commit changing a tracked file inside `scripts/` or `docs/` must update that folder's README.md
- **Changelog routing:** Plugin-only commits → plugin CHANGELOG.md; root-only commits → root CHANGELOG.md; mixed → both
- **Plugin internal naming:** Plugin root doc trio = README.md + CHANGELOG.md + CLAUDE.md
- **branch naming:** `<type>/<short-kebab-description>` (e.g. `feat/poc-reproducer-retry`)
- **Commit format:** `<type>(<optional-scope>): <imperative summary, under 50 chars>`
