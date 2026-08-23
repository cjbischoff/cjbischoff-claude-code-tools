package main

import "net/http"

func register(mux *http.ServeMux) {
	mux.HandleFunc("/admin/reload", reload)
}

func reload(w http.ResponseWriter, r *http.Request) {}
