package main

import (
	"encoding/json"
	"net/http"
	"sort"

	corev1 "k8s.io/api/core/v1"
)

// Ceramic is the JSON shape returned by the API — no Kubernetes vocabulary
// (pod, namespace, etc.) leaks past this point.
type Ceramic struct {
	Name      string `json:"name"`
	Phase     string `json:"phase"`
	CreatedAt string `json:"createdAt"`
	KilnURL   string `json:"kilnURL"`
	ClayURL   string `json:"clayURL"`
	GlazeURL  string `json:"glazeURL"`
	BatURL    string `json:"batURL"`
}

func (s *server) toCeramic(p corev1.Pod) Ceramic {
	clay, glaze, bat := ceramicHostnames(p.Name, s.domain)
	return Ceramic{
		Name:      p.Name,
		Phase:     string(p.Status.Phase),
		CreatedAt: p.CreationTimestamp.UTC().Format("2006-01-02T15:04:05Z"),
		KilnURL:   "/kiln/" + p.Name,
		ClayURL:   "https://" + clay,
		GlazeURL:  "https://" + glaze,
		BatURL:    "https://" + bat,
	}
}

func (s *server) handleList(w http.ResponseWriter, r *http.Request) {
	pods, err := s.listPods(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	sort.Slice(pods, func(i, j int) bool {
		return pods[i].CreationTimestamp.After(pods[j].CreationTimestamp.Time)
	})
	ceramics := make([]Ceramic, 0, len(pods))
	for _, p := range pods {
		ceramics = append(ceramics, s.toCeramic(p))
	}
	w.Header().Set("Content-Type", "application/json")
	w.Header().Set("Cache-Control", "no-store")
	json.NewEncoder(w).Encode(ceramics)
}

func (s *server) handleCreate(w http.ResponseWriter, r *http.Request) {
	pod, err := s.createCeramic(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(s.toCeramic(*pod))
}

func (s *server) handleDelete(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	if err := s.deleteCeramic(r.Context(), name); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
