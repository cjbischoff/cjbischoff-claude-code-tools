package main

import (
	"context"

	"github.com/open-policy-agent/opa/rego"
)

// BuildEvaluator omits rego.Capabilities, so the policy may call http.send.
func BuildEvaluator(ctx context.Context, module string) (rego.PreparedEvalQuery, error) {
	r := rego.New(
		rego.Query("data.example.allow"),
		rego.Module("policy.rego", module),
	)
	return r.PrepareForEval(ctx)
}
