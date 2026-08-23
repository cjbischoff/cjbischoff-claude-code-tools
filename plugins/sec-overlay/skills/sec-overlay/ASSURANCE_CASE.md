# Assurance case: sec-overlay

This document states why the sec-overlay harness is safe to run against a target codebase.
It names the actors, the trust boundaries, the threats, and the countermeasures.
Each countermeasure cites a concrete file and line.
The design follows the Saltzer and Schroeder principles of least privilege and fail-safe defaults.

## Actors

- The maintainer runs the harness and reads the artifacts.
- The main agent orchestrates phases and dispatches subagents.
- A subagent runs one phase prompt and writes structured output.
- An adversary subagent tries to refute a prior artifact.
- The target codebase supplies untrusted source text and untrusted repo docs.

## Trust boundaries

- Repo text into prompts. Source code and repo docs are untrusted input. The harness wraps and neutralizes them first.
- Secrets into prompts. Source text can carry credentials. The harness redacts and verifies text before a model sees it.
- Subagent writes. A subagent writes only into the workspace sidecar. It never writes into the reviewed source tree.
- Target integrity. The harness reads the target. It never executes the target and never modifies the target source.

## Threats

- Prompt injection. Repo text tries to hijack an agent through fake instructions or forged markers. This maps to CWE-77.
- Secret leakage. A credential in source text reaches a model or an artifact. This maps to CWE-312.
- Source tampering. A patch phase modifies the real target instead of a copy.
- False confirmation. A model asserts a finding is real with no mechanical proof.
- Citation hallucination. An agent cites a file and line that does not exist.

## Countermeasures

- Envelope wrapping. `wrap_untrusted` fences untrusted repo text with a nonce marker at `helpers/sec_overlay/envelope.py:15`.
- Marker neutralization. `neutralize_markers` breaks smuggled envelope delimiters at `helpers/sec_overlay/envelope.py:40`.
- Secret abort. `verify_no_secrets` raises on any detected secret at `helpers/sec_overlay/redactor.py:79`.
- Redaction in depth. `safe_for_prompt` masks residual secrets at `helpers/sec_overlay/redactor.py:93`.
- Background guard. `load_background` verifies before it masks at `helpers/sec_overlay/background.py:61`, so a detected secret aborts.
- Copy discipline. `verify` applies a patch to a throwaway copy at `helpers/sec_overlay/verify.py:267`, so the source stays intact.
- Tool-receipt gate. A finding needs a mechanical receipt for confirmation at `helpers/sec_overlay/findings_gate.py:49`.
- Receipt whitelist. `is_tool_receipt` accepts only mechanical sources at `helpers/sec_overlay/evidence.py:36`.
- Citation resolution. `resolve_ref` rejects a reference that does not resolve at `helpers/sec_overlay/phase_gate.py:105`.

## Automated checks

- `pytest` runs the unit and contract suite for the modules above.
- `ruff` lints the helper code at line length 100.
- `ty` checks static types.
- `test_docs_invariants.py` walks the citations in this document and fails on a broken reference.
- The prek pre-commit hook enforces the governance and documentation rules.

## Contrast with open-code-review

The open-code-review benchmark sends code diffs to the model without redaction.
That choice matches its D7 threat note.
A secret in a diff can reach the model and the transcript.
The sec-overlay harness redacts and verifies text before a prompt.
It also requires a mechanical tool receipt before it confirms a finding.
This trades some recall for a lower false-positive rate and lower secret exposure.
