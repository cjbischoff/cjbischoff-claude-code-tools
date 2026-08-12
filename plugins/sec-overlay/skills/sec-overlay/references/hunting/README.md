# `references/hunting/` — exploit-reasoning companions

Deep exploit-reasoning companions loaded conditionally by attack surface; `methodology.md`
and `anti-patterns.md` load always.

| File | Covers |
|------|--------|
| `ai-agent.md` | AI agent & LLM surfaces: chatbots, RAG pipelines, tool-calling loops, MCP servers/clients (LangChain/MCP/RAG); the `untrusted text → model → capability or sink` flow. |
| `anti-patterns.md` | Ten auditor failure modes that produce false positives, missed findings, or wasted review cycles; always loaded, checked before findings leave investigate/critic/validate. |
| `business-logic.md` | Workflow- and role-level exploitability that holds even when every individual check passes — near-universal applicability. |
| `client-side.md` | Client-side & browser (SPA): DOM rendering of attacker-influenceable content, `postMessage`, WebSockets, credentialed cross-origin responses. |
| `graphql-injection.md` | GraphQL injection — loaded only when the target actually uses a GraphQL layer (graphql/apollo-server/graphene/gqlgen/etc.). |
| `memory-native.md` | Memory safety & native code — out of scope unless the target has C/C++/Objective-C, Rust `unsafe`, or a cgo/JNI boundary. |
| `methodology.md` | Twelve domain-agnostic attacker-mindset heuristics; always loaded, the operational core of signal-over-noise. |
| `web-protocol-auth.md` | Web protocol & auth: reverse proxies/gateways, custom HTTP parsers, JWT/OAuth/OIDC/SAML — forging, replaying, or desyncing identity. |

When a file here changes, update this README in the same commit (enforced by the pre-commit hook).
