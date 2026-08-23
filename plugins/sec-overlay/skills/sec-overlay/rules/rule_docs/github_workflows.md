> Favor precision over recall: only raise a finding when the evidence in the workflow YAML under
> review is confident, and stay silent when the triggering event or repository trust boundary is
> not visible in the diff. Adapted from open-code-review (Apache-2.0).

#### Undefined Behavior on Missing or Optional Inputs
- A workflow input or secret referenced without a default where the triggering event may not
  supply it, causing a step to run with an empty or unset value
- A `needs:` reference to a job ID that does not exist in the same workflow, or a circular job
  dependency
- A misspelled action input name (e.g. `fetch-detph`) that is silently ignored rather than erroring

Do not report in the following cases:
- The input has an org- or repo-level default (`vars.*` fallback, org secret)
- A condition already guards the consuming step (`if: inputs.x != ''`)

#### Concurrency Control and Non-Deterministic Runs
- A workflow triggered by `push`/`pull_request` with no `concurrency` group, letting overlapping
  runs race on the same ref or deployment target
- A matrix strategy with `fail-fast` left at its default `true`, canceling unrelated platform legs
  the moment one leg fails, when all legs are meant to report independently

Do not report in the following cases:
- The workflow's steps are read-only or idempotent with no shared external state
- `concurrency` is already declared at the workflow or job level

#### Script and Command Injection via Untrusted Context
- `${{ github.event.* }}` (PR title, body, branch/ref name, issue title) interpolated directly
  into a `run:` block instead of passed through an `env:` variable first
- `pull_request_target` combined with `actions/checkout` on the PR head ref, executing untrusted
  fork code with the target branch's write permissions and secret access
- A secret echoed to logs (`echo ${{ secrets.X }}`) instead of only ever flowing through `env:`

Do not report in the following cases:
- The expression is a fixed literal already controlled by the repo owner (`github.repository`,
  `github.ref` on a protected branch)
- The value already flows through an `env:` variable before any use inside `run:`

#### Excess Permissions and Unbounded Resource Consumption
- `permissions: write-all`, or no top-level `permissions` key at all, defaulting the token to
  broad access instead of least privilege
- A job with no `timeout-minutes`, able to run indefinitely and consume runner (especially
  self-hosted) resources
- A third-party action pinned to a mutable tag instead of a full commit SHA

Do not report in the following cases:
- The job's default token scope already matches least privilege for a read-only workflow
- A first-party `actions/*` action is pinned to a major version tag (`v4`)

#### Silenced Failures and Missing Error Signaling
- `continue-on-error: true` on a security-relevant step (lint, test, dependency scan) that should
  fail the job when it fails
- `|| true` or an equivalent suffix hiding a real command failure instead of an intentionally
  optional, documented step
- Deprecated `set-output`/`save-state`/`::set-output` usage that silently no-ops instead of erroring

Do not report in the following cases:
- `continue-on-error` is on a documented best-effort or notify-only step
- The failure is already surfaced through a separate required status check
