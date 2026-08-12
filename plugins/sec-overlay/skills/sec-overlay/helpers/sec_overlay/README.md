# `sec_overlay/` — the Python core package

The deterministic pipeline package: SAST orchestration, the tool-receipt gate, finding identity,
scoring, reporting, campaign state, and per-repo memory. Stdlib-only (no runtime dependencies).

**The authoritative, grouped module map lives in [`../README.md`](../README.md#sec_overlay--module-map-grouped-by-job)** — that
table lists every module by job and is kept current with the code. This file is the in-package
entry point; read the parent map for the full inventory.

- Package layout: ~72 modules at the top level, plus the `correlate/` subpackage (cross-repo
  correlation — see the parent map's `sec_overlay/correlate/` section).
- Two in-code invariants enforced here: the tool-receipt gate (`evidence.py` + `findings_gate.py`)
  and never-silent backends (`prefilter.py`). See [`../README.md`](../README.md#the-two-invariants-in-code).
- CLI-callable modules (`python -m sec_overlay.<module>`) are listed in the parent map.

When a module here changes, update the module map in [`../README.md`](../README.md) **and** this
pointer if the package layout changed — in the same commit (enforced by the pre-commit hook).

`cost.py` gained `aggregate_by_model` (per-model token totals, alongside the existing
`aggregate_by_phase`), feeding `report.py`'s "Run economics" section — see the module map entry.

`models.py`'s `Finding` gained `cluster_id` (systemic-cluster id) and `affected_sites` (member
sites on a cluster primary) — additive, nullable fields that round-trip through `to_dict`/
`from_dict`.

`selfscore.py` (new) computes the per-run self-score from workspace findings and persists it to
`CampaignState.budget["self_score"]` — see the module map entry.

`cluster.py` (new) groups ≥3 same-class, same-sink `raw` findings into one systemic cluster,
run after dedupe and before the critic/gate ladder — see the module map entry.

`report.py` gained `collapse_clusters`, which reduces each systemic cluster to one representative
finding (highest-risk member, or the elected primary if present) before the confirmed and
needs-runtime buckets are counted and rendered; `render_ndt` renders an affected-sites table when
the finding carries `affected_sites`.

`scope.py` (new) checks `is_external_package(pkg, ws)` against `kb/scan-scope.json`'s
`ingested_packages` list, so a sink that resolves into an un-ingested dependency can be flagged as
outside the scanned source — returns `False` (not external) when no manifest exists, so the check
never invents a boundary — see the module map entry.

`calibrate.py` gained `_EXTERNAL_CAP` (3) and `_is_external_boundary`: a finding whose
`reachability.blocker == "external-boundary"` has its `risk_score` capped at 3 (below the medium
floor of 4) and `completeness_tier` set to `"external-unverifiable"`, so it can never present as a
confirmed medium regardless of claimed severity.

`report.to_markdown` partitions the needs-runtime bucket further: findings with
`completeness_tier == "external-unverifiable"` render in their own "Leads — pending
external-dependency verification" section (via `render_ndt`), separate from the source-provable
needs-runtime section, so a capped external-boundary lead is never conflated with an in-repo
needs-runtime finding.
