# Phase 19: Correlation & Cross-Member Obligations — Context

**Gathered:** 2026-09-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Fix the two high-cost harness defects (D-7, D-8) that prevent the correlation
layer from representing cross-repo taint flows and cross-member obligations.

- **EDGE-01 (D-7):** Add `data-channel` edge kind to correlation with
  manifest-declared channels carrying producer/consumer members and sites.
- **OBLIGATION-01 (D-8):** Add `caller-out-of-scope` to reachability blocker
  taxonomy as first-class non-fatal blocker; cross-member obligations persist
  as open obligations instead of being rejected.

</domain>

<decisions>
## Implementation Decisions

### Data-Channel Edge — Manifest-Declared Channels (D-7)

- **D-01:** The correlation manifest (`correlate/manifest.py`) gains a
  `channels` field: a list of declared data channels. Each channel has `id`,
  `description`, `producer` (member slug), `consumer` (member slug),
  `producer_site` (file:line where data enters), `consumer_site` (file:line
  where data leaves), and `medium` (database, queue, file, shared-schema).
  — **Reversibility:** reversible — additive manifest field, no existing
  correlation output changes.
- **D-02:** The correlation layer (`correlate/edges.py`) gains a
  `data_channel_edges` derivation: for each declared channel, check if the
  producer member has findings at `producer_site` AND the consumer member has
  findings at `consumer_site`. If both exist, emit a `data-channel` edge with
  `evidence_chain: [producer_site, consumer_site]`.
- **D-03:** The correlation verdict for a `data-channel` edge is typed
  `cross-member` (not `coverage-gap`), with `evidence_chain` populated with
  both the producer and consumer `file:line` sites. A verdict with
  `evidence_chain: []` on every row is a null result presented as a result
  — `data-channel` edges must always carry populated evidence chains.
- **D-04:** The existing 3 hardcoded ROLES (`rbac-source`, `service-enforcer`,
  `infra`) remain unchanged. The `channels` field is additive — existing
  manifests without channels continue to work with only the role-based edges.

### Caller-Out-of-Scope Blocker (D-8)

- **D-05:** Add `"caller-out-of-scope"` to `reachability.BLOCKERS` in
  `sec_overlay/reachability.py`. This blocker is non-fatal: a finding with
  this blocker cannot be `confirmed` (the reachability proof requires a
  sibling member's code) but cannot be `rejected` either (the finding is
  real, just not fully provable from one member alone).
- **D-06:** A finding whose blocker is `caller-out-of-scope` persists as an
  **open obligation** rather than being rejected. The obligation record
  carries: finding id, out-of-scope symbol (member slug + site), and status
  `open`.
- **D-07:** The member-scoped validator (`validate` agent) must NOT reject a
  finding whose blocker is `caller-out-of-scope`. The rejection gate in
  `findings_gate.py` must exempt this blocker.
- **D-08:** Correlation (`correlate/verdicts.py`) must attempt to discharge
  open obligations: scan sibling members' findings and channels; if a sibling
  finding or channel matches the out-of-scope symbol, the obligation is
  discharged and a combined finding is created.

</decisions>

<canonical_refs>
## Canonical References

- `.planning/reports/2026-09-02-sec-overlay-missed-rce-coverage-defect-report.md` — D-7, D-8 details
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/correlate/manifest.py` — Current ROLES, Member
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/correlate/edges.py` — Current edge derivations
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/correlate/ingest.py` — Current ingest (findings only)
- `plugins/sec-overlay/skills/sec-overlay/helpers/sec_overlay/reachability.py` — BLOCKERS taxonomy
</canonical_refs>

<code_context>
## Existing Code Insights

### Correlation
- `correlate/manifest.py` — `Member` dataclass with slug, repo_root, scan_scope, role
- `ROLES = ("rbac-source", "service-enforcer", "infra")` — hardcoded
- `correlate/edges.py` — `control_enforces_edges` (privilege-token intersection),
  `same_class_recurrence` (fingerprint grouping)
- `correlate/ingest.py` — reads findings.json only, no channel/obligation data
- `verdicts.json` structure: `{edges, members, verdicts, artifacts}` — verdicts
  carry `direction`, `edge`, `evidence_chain`, `confidence`

### Reachability
- `reachability.py` has `BLOCKERS` frozenset — need to add `caller-out-of-scope`
- Findings gate exempts certain blocker types from rejection

</code_context>

<deferred>
## Deferred Ideas

- Automatic channel discovery (inferring channels from shared schemas, queue
  topic conventions, or DB migration analysis) — future work.

</deferred>

---

*Phase: 19-Correlation & Cross-Member Obligations*
*Context gathered: 2026-09-06*
