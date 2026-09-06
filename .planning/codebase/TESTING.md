# Testing

**Analysis Date:** 2026-09-05

## Test Framework

- **Runner:** pytest >=8
- **Config:** `pyproject.toml` (`testpaths = ["tests"]`)
- **Type checker:** `ty` (separate from tests, checks non-fixture paths)
- **Linter:** ruff >=0.6 (line-length 100, `target-version = "py312"`)
- **TDD convention:** New or changed executable logic ships with a test in the same change; failing-test-first expected

## Test Location & Organization

```
plugins/sec-overlay/skills/sec-overlay/helpers/
├── tests/               # ~150 test files
│   ├── test_workspace.py
│   ├── test_run.py
│   ├── test_cli_e2e.py
│   ├── test_review_*.py        # ~10 test files (review_live, review_profiles, review_coverage, etc.)
│   ├── test_prefilter*.py
│   ├── test_dedupe.py
│   ├── test_finding_schema.py
│   ├── test_correlate_*.py     # ~6 test files (CLI, edges, ingest, manifest, mermaid, rethreshold, xrepo_sarif)
│   ├── test_verify*.py         # verify, verify_causes, verify_configs
│   ├── test_sast.py / test_sca.py / test_secrets.py
│   ├── test_fp_feedback.py / test_fix_and_gates.py
│   ├── test_crypto_policy.py / test_cvss.py / test_cvss4_data.py
│   ├── test_frozen_contract.py
│   ├── test_phase*.py          # phase_gate, phases test
│   ├── test_diagram_gate.py / test_ste_lint*.py
│   ├── test_graph.py / test_kb.py
│   ├── test_redteam*.py        # ~4 files
│   ├── test_report*.py         # report, report_optional_sections, report_split
│   ├── test_render_util.py
│   ├── test_repo_memory.py
│   ├── test_reflection.py
│   ├── test_* (one per core module)
│   └── README.md               # Possibly test-specific readme
├── fixtures/            # Test fixtures
│   ├── vulnerable_repo/        # Target codebase with known vulns
│   ├── absence_repo/           # For absence-detection testing
│   ├── dep_cve_repo/           # For dependency CVE testing
│   ├── dep_sink_repo/          # For dependency sink testing
│   ├── route_repo/             # For route census testing
│   ├── golden_sqli_patch.diff
│   ├── golden_raw_finding.json
│   └── golden_scan_profile.json
├── bench/               # Benchmarking harness
│   ├── driver.py / judge.py / run.py / tally.py
│   ├── corpus_seed/            # Benchmark corpus
│   ├── corpus.py / adapter.py / aacr_adapter.py
│   └── README.md
└── rules/               # Semgrep rule fixtures
    ├── absence/                # First-party absence rule pack
    ├── smoke.yaml              # Minimal demo ruleset
    └── README.md
```

## Test Patterns

### Unit Tests
One test file per core module following `test_<module>.py` naming. For example:
- `test_workspace.py` — tests `sec_overlay/workspace.py`
- `test_dedupe.py` — tests `sec_overlay/dedupe.py`
- `test_cluster.py` — tests `sec_overlay/cluster.py`
- `test_finding_schema.py` — tests `sec_overlay/finding_schema.py`

### Integration Tests
- `test_cli_e2e.py` — End-to-end CLI tests
- `test_verify_causes.py` — Verify causes integration
- `test_review_live.py` — Live review pipeline tests
- `test_correlate_*.py` — Cross-repo correlation integration
- `test_wiring.py` — Module wiring integration

### Test Fixtures
- **Real target repos:** `fixtures/vulnerable_repo/`, `fixtures/absence_repo/`, `fixtures/dep_cve_repo/`, `fixtures/dep_sink_repo/`, `fixtures/route_repo/` — small but real codebases with known patterns
- **Golden files:** `golden_sqli_patch.diff`, `golden_raw_finding.json`, `golden_scan_profile.json` — known-good expected outputs for comparison

### CI Test Suite
- **`.github/workflows/sec-overlay-tests.yml`** — Runs pytest + offline detection-regression gate on pull requests
- Ruff linter runs as a separate check (not in pytest)
- `ty` type checker runs separately

## Test Governance

- **No test fixtures in ruff/ty scanning** — `fixtures` and `rules` directories excluded in `pyproject.toml`
- **Per-file ignores:** `tests/**` allows `E702` (multiple statements per line) in ruff
- **Test assertions verified in v5.1:** WR-01 tests prove the adversary guard runs before any git call; `--workspace` forwarding asserted in CLI test (TEST-01, PR #32)
- **Benchmark suite** at `bench/` — separate from unit/integration tests; independent run

## Coverage & Quality Enforcement

- CodeQL runs on the repo with path exclusions for test fixtures and caches (`.github/codeql/codeql-config.yml`)
- Dependency review on all PRs (`.github/workflows/dependency-review.yml`)
- CodeRabbit reviews every PR with governance pre-merge checks
- Pre-commit hooks validate doc-update guards and commit messages
