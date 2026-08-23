package main

import (
	"github.com/google/cel-go/cel"
	lua "github.com/yuin/gopher-lua"
)

// BuildUnsafeCelEnv declares nothing, so every inherited host function is
// reachable from caller-supplied expression text.
func BuildUnsafeCelEnv() (*cel.Env, error) {
	return cel.NewEnv()
}

// BuildUnsafeLuaState keeps the default standard library, so os and io stay
// reachable from caller-supplied Lua.
func BuildUnsafeLuaState() *lua.LState {
	return lua.NewState()
}
