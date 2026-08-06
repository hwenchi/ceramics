package main

import (
	"embed"
	"html/template"
	"net/http"
)

//go:embed templates/kiln.html templates/home.html
var templateFS embed.FS

var kilnTemplate = template.Must(template.ParseFS(templateFS, "templates/kiln.html"))

var homeHTML = func() []byte {
	b, err := templateFS.ReadFile("templates/home.html")
	if err != nil {
		panic(err) // embedded at build time; a missing file is a build-time bug, not a runtime one
	}
	return b
}()

func handleHome(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	w.Write(homeHTML)
}

type kilnPage struct {
	Name     string
	ClayURL  string
	GlazeURL string
}

// kilnHandler serves the split-pane view of one ceramic at /kiln/{name}.
type kilnHandler struct {
	domain string // e.g. "software-dev.ncsa.illinois.edu"
}

func (k *kilnHandler) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	clay, glaze := ceramicHostnames(name, k.domain)
	page := kilnPage{
		Name:     name,
		ClayURL:  "https://" + clay,
		GlazeURL: "https://" + glaze,
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := kilnTemplate.Execute(w, page); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
