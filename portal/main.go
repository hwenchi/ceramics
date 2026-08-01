package main

import (
	"log"
	"net/http"
	"os"
)

func main() {
	clientset, err := getClientset()
	if err != nil {
		log.Fatalf("k8s client: %v", err)
	}

	v, err := clientset.Discovery().ServerVersion()
	if err != nil {
		log.Fatalf("server version: %v", err)
	}
	log.Printf("connected to cluster, server version %s", v.String())

	namespace := os.Getenv("CERAMIC_NAMESPACE")
	if namespace == "" {
		namespace = "ceramics"
	}
	image := os.Getenv("CERAMIC_IMAGE")
	if image == "" {
		image = "ghcr.io/hwenchi/ceramics/ceramic:main"
	}
	s := &server{clientset: clientset, namespace: namespace, image: image}

	portalOrigin := os.Getenv("PORTAL_ORIGIN")
	if portalOrigin == "" {
		portalOrigin = "https://ceramics.software-dev.ncsa.illinois.edu"
	}
	domain := os.Getenv("CERAMIC_DOMAIN")
	if domain == "" {
		domain = "software-dev.ncsa.illinois.edu"
	}

	apiMux := http.NewServeMux()
	apiMux.HandleFunc("GET /", handleHome)
	apiMux.HandleFunc("GET /api/ceramics", s.handleList)
	apiMux.HandleFunc("POST /api/ceramics", s.handleCreate)
	apiMux.HandleFunc("DELETE /api/ceramics/{name}", s.handleDelete)
	apiMux.Handle("GET /kiln/{name}", &kilnHandler{domain: domain})

	proxy := &ceramicProxy{resolve: s.resolveIP, portalOrigin: portalOrigin}

	// Requests to a ceramic's own hostname (ceramic-01-clay, ceramic-01-glaze)
	// go to the proxy; everything else (the portal's own hostname) hits the API.
	root := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, _, ok := parseHost(r.Host); ok {
			proxy.ServeHTTP(w, r)
			return
		}
		apiMux.ServeHTTP(w, r)
	})

	addr := ":8000"
	log.Printf("portal listening on %s (namespace=%s image=%s)", addr, namespace, image)
	log.Fatal(http.ListenAndServe(addr, root))
}
