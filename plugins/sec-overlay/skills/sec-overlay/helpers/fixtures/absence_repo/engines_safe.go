package main

import (
	"github.com/google/cel-go/cel"
	lua "github.com/yuin/gopher-lua"
)

// BuildSafeCelEnv declares the one variable the expression may name, so no
// other host name resolves.
func BuildSafeCelEnv() (*cel.Env, error) {
	return cel.NewEnv(cel.Variable("input", cel.StringType))
}

// BuildSafeLuaState skips the standard library, so os and io stay unreachable.
// gopher-lua takes Options by value, which is what the absence rule negates.
func BuildSafeLuaState() *lua.LState {
	return lua.NewState(lua.Options{SkipOpenLibs: true})
}
