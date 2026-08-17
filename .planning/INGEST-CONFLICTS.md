## Conflict Detection Report

Mode: new (no existing .planning/ context to check against). Precedence applied:
ADR > SPEC > PRD > DOC, with recency resolving same-tier overlap between historical,
completed design docs (per ingest instruction). 0 locked decisions, 0 PRDs,
0 UNKNOWN classifications in the set.

### BLOCKERS (0)

None. No LOCKED-vs-LOCKED contradiction (no doc is locked). No UNKNOWN/low-confidence
classification. No multi-document cross-reference cycle (DFS over the cross_refs graph
found none; one degenerate self-reference, see INFO).

### WARNINGS (1)

[WARNING] Referenced spec missing from ingest set (kb-redesign design)
  Found: docs/superpowers/specs/2026-08-11-sec-overlay-kb-redesign-design.md
    ("Approved for implementation") lists truncated cross_refs
    "docs/superpowers/plans/2026-08-11-…" and "docs/superpowers/specs/2026-08-09-…";
    no 2026-08-09 spec exists in the classification set.
  Impact: The upstream spec this design builds on was not classified, so constraints
    inherited from it may be incomplete in constraints.md; the precedence chain for the
    KB doc/diagram redesign cannot be fully verified.
  → If docs/superpowers/specs/ contains a 2026-08-09 spec, add it via --manifest and
    re-run ingest; otherwise approve proceeding with the design doc as the authority.

### INFO (7)

[INFO] Auto-resolved: CVSS v4.0 supersedes CVSS 3.1 (SPEC > DOC + explicit ruling)
  Note: docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md
    (ruling R2) and the -source.md standard pin CVSS v4.0 harness-wide, "no mixing".
    plugins/.../docs/plans/2026-08-02-clusterF-T7-calibrate-crash.md (DOC) targets the
    old cvss31_base engine; docs/superpowers/plans/2026-08-16-sec-overlay-cvss4-migration.md
    implements the replacement. SPEC wins over DOC; CVSS v4.0 is authoritative.

[INFO] Auto-resolved by recency: architecture/threat-model artifact layout
  Note: docs/superpowers/specs/2026-08-16-architecture-threat-model-standards-design.md
    (ruling R3) replaces the artifact layout outright — <workspace>/architecture/ and
    <workspace>/threat-model/ replace kb/architecture.md, kb/entities/*.md,
    kb/THREAT_MODEL.md, "no shims; all consumers re-pointed". This supersedes the
    artifact definitions in plugins/.../docs/plans/2026-08-02-artifact-substrate-design.md
    (same SPEC tier, earlier, self-declared pre-implementation with open questions).
    The substrate's kb/graph.json evidence layer is NOT superseded — only the
    architecture/threat-model artifact layout.

[INFO] Auto-resolved by recency: report rendering contract
  Note: docs/superpowers/specs/2026-08-15-sec-overlay-defect-remediation-design.md
    (report split + per-finding detail files) postdates
    plugins/.../docs/superpowers/specs/2026-08-08-report-readability-design.md
    (triage table, NDT-view, dep-view) on the same report.md scope. Same SPEC tier;
    both are completed historical designs; the 08-15 structure is authoritative where
    the two contradict. The 08-08 epistemic rules (headline counts must not hide NDT
    leads) are consistent with, and carried forward by, the later spec.

[INFO] Explicit supersession: Spec B over the cross-repo correlation seed design
  Note: plugins/.../docs/plans/2026-08-08-cross-repo-correlation-spec.md declares in
    its own header "Supersedes/expands: docs/plans/2026-08-07-cross-repo-correlation-design.md".
    Not a contradiction — a declared lineage. Spec B is authoritative for correlation.

[INFO] Auto-resolved by recency: invocation authority
  Note: docs/superpowers/specs/2026-08-16-sec-overlay-invocation-design.md ("Approved
    2026-08-16") defines the /sec-overlay:audit command and run.py driver, layering
    over docs/superpowers/plans/2026-08-15-sec-overlay-audit-driver.md (Plan A
    phases.py/driver.py sequencer). Complementary, not contradictory; the 08-16 design
    is the latest authority on how a run is invoked and driven.

[INFO] Degenerate self-reference in one classification's cross_refs
  Note: the classification for docs/superpowers/plans/2026-08-16-sec-overlay-invocation.md
    lists its own path in cross_refs (a self-loop). Cycle detection (DFS, depth cap 50)
    found no cycle between distinct documents; a self-loop cannot cause a synthesis
    loop, so synthesis proceeded on the full set.

[INFO] Evidence documents referenced but outside the ingest set
  Note: several specs cite evidence inputs that were not classified (by design — they
    are review artifacts, not planning docs):
    review_agentgateway/brainstorming/review_sec-overlay-issues_20260814_1507.md
    (defect-remediation), review_sec-overlay-harness_20260814_1258.md and
    spec_sec-overlay-invocation_20260815_0949.md (invocation design),
    ~/Documents/Reports/2026-08-08-aem-report-artifact-critique.md (report
    readability). Provenance is noted per entry in constraints.md; no extraction gap —
    each spec restates the constraints it derives from them.
