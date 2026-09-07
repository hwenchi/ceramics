package main

import (
	"embed"
	"html/template"
	"net/http"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
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
	BatURL   string
}

// handleKiln serves the split-pane view of one ceramic at /kiln/{name} — but
// only once it's actually reachable. A ceramic that doesn't exist, is still
// starting up, or is being deleted sends the visitor back to the studio
// instead of a page full of panels with nothing to connect to; the studio's
// own polling already tells them what's going on.
func (s *server) handleKiln(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	pod, err := s.clientset.CoreV1().Pods(s.namespace).Get(r.Context(), name, metav1.GetOptions{})
	if err != nil || pod.DeletionTimestamp != nil || !podReady(*pod) {
		http.Redirect(w, r, "/", http.StatusFound)
		return
	}

	clay, glaze, bat := ceramicHostnames(name, s.domain)
	page := kilnPage{
		Name:     name,
		ClayURL:  "https://" + clay,
		GlazeURL: "https://" + glaze,
		BatURL:   "https://" + bat,
	}
	w.Header().Set("Content-Type", "text/html; charset=utf-8")
	if err := kilnTemplate.Execute(w, page); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
	}
}
