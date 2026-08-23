package main

import (
	"context"

	"github.com/open-policy-agent/opa/rego"
)

// EvalPolicy builds an evaluator from caller-supplied policy text. No
// rego.Capabilities call, so the policy may call the http.send builtin.
func EvalPolicy(ctx context.Context, module string, input map[string]any) (rego.ResultSet, error) {
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
	)
	q, err := r.PrepareForEval(ctx)
	if err != nil {
		return nil, err
	}
	return q.Eval(ctx, rego.EvalInput(input))
}
