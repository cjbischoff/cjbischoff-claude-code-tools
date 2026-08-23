package main

import (
	"context"

	"github.com/open-policy-agent/opa/ast"
	"github.com/open-policy-agent/opa/rego"
)

// BuildSafeEvaluator removes http.send from the builtin set before evaluating.
func BuildSafeEvaluator(ctx context.Context, module string) (rego.PreparedEvalQuery, error) {
	caps := ast.CapabilitiesForThisVersion()
	kept := caps.Builtins[:0]
	for _, b := range caps.Builtins {
		if b.Name != "http.send" {
			kept = append(kept, b)
		}
	}
	caps.Builtins = kept
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
		rego.Capabilities(caps),
	)
	return r.PrepareForEval(ctx)
}
