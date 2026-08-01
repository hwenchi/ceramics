package main

import (
	"encoding/json"
	"net/http"

	corev1 "k8s.io/api/core/v1"
)

// Ceramic is the JSON shape returned by the API — no Kubernetes vocabulary
// (pod, namespace, etc.) leaks past this point.
type Ceramic struct {
	Name      string `json:"name"`
	Phase     string `json:"phase"`
	CreatedAt string `json:"createdAt"`
}

func toCeramic(p corev1.Pod) Ceramic {
	return Ceramic{
		Name:      p.Name,
		Phase:     string(p.Status.Phase),
		CreatedAt: p.CreationTimestamp.UTC().Format("2006-01-02T15:04:05Z"),
	}
}

func (s *server) handleList(w http.ResponseWriter, r *http.Request) {
	pods, err := s.listPods(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	ceramics := make([]Ceramic, 0, len(pods))
	for _, p := range pods {
		ceramics = append(ceramics, toCeramic(p))
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(ceramics)
}

func (s *server) handleCreate(w http.ResponseWriter, r *http.Request) {
	pod, err := s.createCeramic(r.Context())
	if err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(toCeramic(*pod))
}

func (s *server) handleDelete(w http.ResponseWriter, r *http.Request) {
	name := r.PathValue("name")
	if err := s.deleteCeramic(r.Context(), name); err != nil {
		http.Error(w, err.Error(), http.StatusInternalServerError)
		return
	}
	w.WriteHeader(http.StatusNoContent)
}
