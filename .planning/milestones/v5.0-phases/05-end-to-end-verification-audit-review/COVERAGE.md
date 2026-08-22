# Phase 05 API Coverage

No external API integration: the sec-overlay core is stdlib-only, the Anthropic SDK
and any direct API dependency are rejected by ADR-2026-08-04 (recorded under Out of
Scope in REQUIREMENTS.md), and `helpers/pyproject.toml` keeps an empty runtime
dependency list per REL-03. This phase adds no source code at all — it runs the two
existing pipelines against a real target repository and records sanitized receipts.
Every command it issues is a local `subprocess` invocation of git or a locally
installed scanner; no third-party service surface is created, called, or configured.

The detector signal that triggered this file is a false positive: the matched text is
the row `| Anthropic SDK / direct API dependency | Rejected by ADR-2026-08-04;
stdlib-only core |` in REQUIREMENTS.md's Out of Scope table. The match is a statement
that the dependency does not exist, not an integration point.
