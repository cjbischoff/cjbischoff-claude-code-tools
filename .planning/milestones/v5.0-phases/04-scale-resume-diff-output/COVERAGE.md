# Phase 04 API Coverage

No external API integration: the sec-overlay core is stdlib-only, the Anthropic SDK
and any direct API dependency are rejected by ADR-2026-08-04 (recorded under Out of
Scope in REQUIREMENTS.md), and `helpers/pyproject.toml` keeps an empty runtime
dependency list per REL-03. This phase adds concurrency bounds, resume identity
validation, and diff-anchored output — all of which run against the local git
repository through `subprocess`, with no third-party service surface.
