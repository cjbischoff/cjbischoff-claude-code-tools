> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null and Missing-Value Handling
- Interpolations or directive arguments on possibly-absent values without `!` (default)
  or `??` (existence), which raise `InvalidReferenceException` at render time
- A bare `!` masking genuinely-required data with a silent empty string instead of an
  explicit default or `<#if value??>` guard

Do not report in the following cases:
- An earlier `<#if value??>` in the same template already guards the access
- The value is a template-scope constant or loop variable guaranteed present

#### Concurrency Across Renders
- Rarely applicable: template rendering is per-request with no shared mutable state
  unless the data model itself holds a shared mutable object

Do not report in the following cases:
- Ordinary per-request template rendering with no shared mutable data-model object
- `<#assign>`/`<#local>` scoped to a single render pass

#### Injection (Output Escaping and SSTI)
- Interpolations reaching HTML without escaping when auto-escaping is not active
  (`<#ftl output_format="HTML">` absent and file is not `.ftlh`/`.ftlx`) and no
  `?html`/`?url`/`?js_string` matches the sink
- `?no_esc`, `<#noautoesc>`, `?new()`, `?api`, or `?eval` applied to user-controlled or
  untrusted input — server-side template injection / RCE risk

Do not report in the following cases:
- Auto-escaping is active for the file's output format and no override disables it
- The interpolated value is a literal constant or sanitized immediately before use

#### Resource Management
- `<#include>`/`.get_optional_template(userValue)` resolving a template name derived
  from unbounded or unvalidated request input, allowing arbitrary template disclosure
- Missing-template failures left unhandled where the include is meant to be optional

Do not report in the following cases:
- The included template name is a fixed, template-source-controlled literal
- `.get_optional_template(...).exists` already guards the optional include

#### Swallowed Errors
- A macro/function whose failure path is silently absorbed by `!` defaults, hiding a
  render-time failure instead of surfacing it to the caller
- `<#attempt>`/`<#recover>` blocks that recover without logging or re-raising a
  meaningful error

Do not report in the following cases:
- The recovery path logs or substitutes a documented, intentional fallback
- The masked failure is on genuinely optional data, not required input
