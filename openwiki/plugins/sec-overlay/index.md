# Files

- [sec-overlay LLM Agent Prompts](agents.md) - The producer-vs-adversary model behind every sec-overlay agent prompt, the investigate gate ladder, the classes/ extension prompts, and the template tokens the orchestrator substitutes.
- [Cross-Repo Correlation](cross-repo-correlation.md) - How sec-overlay joins N already-completed per-repo scans into cross-repo edges and verdicts, deterministically and read-only, when one product spans multiple repositories.
- [Developing the sec-overlay Skill](developing-the-skill.md) - Test and lint commands, the stdlib-only dependency rule, the structural guard tests, the dev-only bench harness, and the folder-README-tracks-code rule as it applies inside the sec-overlay skill.
- [sec-overlay Deterministic Python Core (helpers/)](helpers.md) - The stdlib-only Python modules that run SAST tools, enforce the tool-receipt gate, and assemble the SARIF and Markdown reports for the sec-overlay harness.
- [sec-overlay Plugin Overview](overview.md) - What the sec-overlay plugin is, its four governing principles, its three-folder architecture (agents, helpers, references), and the invariants that make its findings trustworthy.
- [sec-overlay Audit Pipeline](pipeline.md) - The full phase order of a sec-overlay audit pass, the phase-adversary gate mechanism, the tuning knobs, and the multi-pass campaign model.
- [sec-overlay Reference Knowledge Base (references/)](references.md) - The prompt-constants blocks injected into every agent, the attack-class registry, the machine-checked schemas and crypto policy, and the hunting/codeguard guides that make sec-overlay's rules consistent across ~30 agent prompts.
- [Running a sec-overlay Audit](running-an-audit.md) - The deterministic smoke-scan command versus a full agentic audit, preflight tool checks, environment prerequisites and the two known env-only test failures, and how the harness upholds its never-execute-the-target invariant.
