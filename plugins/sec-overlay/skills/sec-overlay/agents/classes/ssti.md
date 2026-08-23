# CWE-class extension — ssti

Thin extension imported by investigate/patch on top of the shared preamble. Adds ONLY
the class-specific bits; the gate ladder + tool-receipt rules come from the base prompt.

## Canonical fix shape
Render through a non-template or sandboxed path and pass caller data only as template
CONTEXT, never as template SOURCE. Name the concrete option: a `jinja2.Environment` with
`autoescape` on and no `from_string`/`Template()` call on caller text, or a logic-less
engine (Mustache-style) with no code-execution syntax. A deny-list of template syntax
tokens is not the fix shape; the rendering path is.

## Discrimination requirement
State whether the caller-supplied text becomes template SOURCE (compiled and rendered) or
template CONTEXT (a value substituted into a fixed, first-party template). Only the first
is `ssti`. A caller value inserted into a fixed template's context is not a finding here —
check it under `injection`/XSS for output-escaping instead.

## Class boundary
**IS:** untrusted text compiled and rendered as template source by a template engine
(`Template(request_data)`, `env.from_string(user_text)`, or a `render`/`render_string` call
whose template argument itself is attacker-controlled).
**IS NOT:**
- A sandbox escape in a general expression, policy, or rule engine (Rego, CEL, Starlark,
  Lua, a JS VM) with no template-compilation step → `cls: expr-eval-rce`.
- Raw `eval()`/`exec()` on attacker text with no template engine involved → `cls: injection`.
- Attacker data rendered as CONTEXT into a fixed, first-party template with unescaped
  output reaching HTML → `cls: injection` (XSS), not ssti — the template source here is
  fixed, only the output-escaping is broken.

## Proof tuple (required evidence)

A confirmable SSTI needs all three, each with a `file:line`:
1. **Template engine constructed and fed caller text as source** — cite the construction
   line and the line where attacker-controlled text becomes the template argument, not a
   context value. A `dependency-catalog:<id>` receipt names a dependency-internal render
   call when the sink has no first-party line; it locates the sink and never confirms alone.
2. **No sandbox/non-template rendering path on every path to that compile-and-render call**
   — cite the absence: the construction call with `autoescape` off or with `from_string`/
   `Template()` still reachable from caller text.
3. **Attacker control of the compiled text** — cite the route, handler, or queue consumer
   that carries the text, and the assignment that reaches element 1.

**Instance preservation:** do NOT collapse sibling instances that share a CWE but hit distinct concrete sinks/routes into one finding. Expand every concrete instance as its own candidate; dedupe merges only exact `(file,line,cls)` collisions.
