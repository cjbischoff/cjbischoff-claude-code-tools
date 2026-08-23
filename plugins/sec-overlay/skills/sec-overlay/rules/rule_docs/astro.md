> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null and Missing Frontmatter Values
- Frontmatter data reaching client HTML, an inline script, or a hydrated island without
  a check for `undefined`/`null` when the source (fetch, `Astro.locals`, query param)
  can legitimately be absent
- A prop passed into a `client:*` island typed as optional but destructured without a
  default or guard

Do not report in the following cases:
- The value is a required, statically known frontmatter constant
- An earlier conditional in the same `.astro` file already rules out the absent case

#### Concurrency Across Islands
- Rarely applicable: `.astro` frontmatter runs once per render with no shared mutable
  state across requests unless explicitly stored server-side

Do not report in the following cases:
- Ordinary per-request frontmatter execution with no shared server-side mutable state
- Client-side island state that is local to that island's own hydration instance

#### Injection (Unescaped Output and Template Safety)
- `set:html` rendering a value that is not clearly trusted or sanitized — treat as a
  high-risk escape hatch
- Untrusted data interpolated into an attribute, URL, or raw markup without
  context-appropriate escaping, or a `<script define:vars>` payload containing
  unescaped user input

Do not report in the following cases:
- The templating layer's autoescaping is active and the output is not explicitly
  marked safe/raw (no `set:html`, no `is:raw`)
- The value is a literal constant or already sanitized immediately before use

#### Resource and Payload Management
- Hydrated component props or `define:vars` payloads carrying secrets, large objects,
  or unreduced server-fetched data across the client boundary
- `server:defer` islands with no fallback slot when the deferred fetch is unbounded or
  slow, risking a stuck loading state

Do not report in the following cases:
- The payload is already reduced to the minimal serializable interaction data
- The server island has an adapter-provided fallback or timeout in visible context

#### Swallowed Errors
- A server-fetched data call in frontmatter with no error handling, letting a failed
  fetch render an empty or broken island silently
- A `client:only` island with no fallback content, producing a blank UI on failure with
  no indication to the user

Do not report in the following cases:
- The fetch error is caught and surfaced via a rendered error state
- The failure mode is a documented, unreachable internal invariant
