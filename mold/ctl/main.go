// ctl holds the real Docker socket and exposes exactly three hardcoded
// operations, name-allow-listed. No generic Docker API surface exists.
package main

import (
	"encoding/json"
	"io"
	"log"
	"net/http"
	"sort"

	"github.com/moby/moby/client"
)

type statusEntry struct {
	Name      string `json:"name"`
	State     string `json:"state"`
	StartedAt string `json:"startedAt"`
}

// Restart: dev containers only.
var restartAllowed = map[string]bool{
	"fastapi-dev": true,
	"angular-dev": true,
}

// Logs/status are read-only, so all fixed containers are fine here.
var readAllowed = map[string]bool{
	"ceramic":     true,
	"postgres":    true,
	"keycloak":    true,
	"fastapi-dev": true,
	"angular-dev": true,
	"caddy":       true,
}

func main() {
	cli, err := client.NewClientWithOpts(client.FromEnv, client.WithAPIVersionNegotiation())
	if err != nil {
		log.Fatal(err)
	}

	mux := http.NewServeMux()

	mux.HandleFunc("POST /restart/{name}", func(w http.ResponseWriter, r *http.Request) {
		name := r.PathValue("name")
		if !restartAllowed[name] {
			http.Error(w, "not allowed", http.StatusForbidden)
			return
		}
		if _, err := cli.ContainerRestart(r.Context(), name, client.ContainerRestartOptions{}); err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
	})

	mux.HandleFunc("GET /logs/{name}", func(w http.ResponseWriter, r *http.Request) {
		name := r.PathValue("name")
		if !readAllowed[name] {
			http.Error(w, "not allowed", http.StatusForbidden)
			return
		}
		out, err := cli.ContainerLogs(r.Context(), name, client.ContainerLogsOptions{
			ShowStdout: true,
			ShowStderr: true,
			Tail:       "200",
		})
		if err != nil {
			http.Error(w, err.Error(), http.StatusInternalServerError)
			return
		}
		defer out.Close()
		if _, err := io.Copy(w, out); err != nil {
			log.Printf("logs %s: %v", name, err)
		}
	})

	mux.HandleFunc("GET /status", func(w http.ResponseWriter, r *http.Request) {
		names := make([]string, 0, len(readAllowed))
		for name := range readAllowed {
			names = append(names, name)
		}
		sort.Strings(names)

		entries := make([]statusEntry, 0, len(names))
		for _, name := range names {
			info, err := cli.ContainerInspect(r.Context(), name, client.ContainerInspectOptions{})
			if err != nil || info.Container.State == nil {
				entries = append(entries, statusEntry{Name: name, State: "unknown"})
				continue
			}
			entries = append(entries, statusEntry{
				Name:      name,
				State:     string(info.Container.State.Status),
				StartedAt: info.Container.State.StartedAt,
			})
		}
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(entries)
	})

	log.Fatal(http.ListenAndServe(":8090", mux))
}
