# Class extension: expr-eval-rce

Sandboxed expression, policy, or rule-engine escape. The evaluator is often a
dependency, so the sink is a builtin the engine exposes to evaluated text, not a
first-party call.

## Canonical fix shape

Narrow the engine's capability set at construction. Name the option in the fix:
`rego.Capabilities` with the unwanted builtin removed, a `cel.NewEnv` limited to a
reviewed declaration list, `lua.NewState` with `SkipOpenLibs`, a `goja.Runtime`
with no host object `Set`. A deny-list of expression substrings is not the fix
shape; the capability set is.

## Discrimination requirement

State which of these three the finding is, and cite the line:

1. The engine evaluates text the caller supplies at runtime.
2. The engine evaluates text that is a compile-time constant in this repo.
3. The engine is constructed but never evaluates caller text.

Only case 1 is a finding. Case 2 is `informational` unless the constant is loaded
from a writable path. Case 3 is `rejected`.

## Class boundary

IS this class: an evaluator that runs caller-supplied expression, policy, or
script text, where a builtin or host function reaches a capability the caller
should not have.

IS NOT this class:
- `eval()` or `exec()` on attacker text with no sandbox — that is `injection`.
- A template engine rendering untrusted markup — that is `ssti`.
- An object graph rebuilt from bytes — that is `deserialization`.
- An engine builtin that performs an outbound request — that is `ssrf`. Route by
  the sink the builtin reaches. OPA's `http.send` is `ssrf`.

## Proof tuple (required evidence)

All three elements, each with a `file:line` citation:

1. **Evaluator constructed and fed caller text.** Cite the construction line and
   the line where the expression, policy, or script text enters it. A
   `dependency-catalog:<id>` receipt names the dependency-internal sink when the
   sink has no first-party line; it locates the sink and never confirms alone.
2. **No capability restriction on every path to that evaluation.** Cite the
   absence: the construction call with no restricting option, or the option call
   with the dangerous builtin still present. An absence rule receipt
   (`semgrep:sec-overlay.absence.*`) satisfies this element.
3. **Attacker control of the evaluated text.** Cite the route, handler, or queue
   consumer that carries the text, and the assignment that reaches element 1.

An element with no citation makes the finding `raw`, never `confirmed`.

## Instance preservation

One finding per evaluator construction site. Two handlers building their own
evaluator are two findings even when the fix is the same option, because each
site can be fixed or missed independently.
