> Favor precision over recall: only raise a finding when the evidence in the diff and
> surrounding file is confident, and stay silent when context is unclear.
> Adapted from open-code-review (Apache-2.0).

#### Null and Undefined Dereference
- A value from `$r`/`$rawfile` lookup, network response, or optional chaining reaching a
  destructure or property access without a preceding null/undefined check
- `@Prop`/`@Link`/`@State` fields typed to allow `undefined` used in the `build` method
  without a guard before access

Do not report in the following cases:
- The value is a required, non-optional constructor/props parameter with a default
- An earlier `if`/`??`/optional-chain in the same function already rules out the absent case

#### Async and Worker Race Conditions
- Shared component state (`@State`/`AppStorage`) mutated from more than one async
  callback, timer, or worker message handler without ordering or cancellation guard
- A timer or listener started in `aboutToAppear` that can still fire after
  `aboutToDisappear` releases the component's state

Do not report in the following cases:
- The async work is awaited sequentially with no concurrent callback in flight
- The listener/timer is already released in `aboutToDisappear` in the visible code

#### Injection (SQL, Command, and DOM)
- User input concatenated directly into a SQL string, shell command, or `eval`-like
  call instead of using parameter binding or an allow-listed API
- Untrusted data written into WebView/DOM APIs (`innerHTML`-equivalent, raw URL
  navigation) without escaping or an HTTPS/certificate check on the request

Do not report in the following cases:
- The value is a literal constant or already validated/escaped immediately before use
- The API used is a typed component prop that the framework serializes safely

#### Resource Leaks
- Timers, listeners, or subscriptions created in `aboutToAppear` with no matching
  release in `aboutToDisappear`
- Image or file resources loaded without a caching/release strategy on a hot path,
  causing unbounded resource growth

Do not report in the following cases:
- The resource is released by a framework-managed lifecycle visible in context
- A one-shot listener that the framework itself removes after firing once

#### Swallowed Errors
- An async function or promise chain with no `try`/`catch` (or `.catch`), letting a
  rejection disappear silently in a user-facing flow
- A `catch` block that logs nothing and substitutes a default without surfacing the
  original failure to the caller or user

Do not report in the following cases:
- The catch re-throws, logs at an appropriate level, or shows a user-facing error
- The error is a documented, unreachable internal invariant, not external input
