package main

import (
	"log"
	"net/http"
	"os"

	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
)

func main() {
	cfg, err := getConfig()
	if err != nil {
		log.Fatalf("k8s config: %v", err)
	}
	clientset, err := kubernetes.NewForConfig(cfg)
	if err != nil {
		log.Fatalf("k8s clientset: %v", err)
	}
	dynamicClient, err := dynamic.NewForConfig(cfg)
	if err != nil {
		log.Fatalf("k8s dynamic client: %v", err)
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
	domain := os.Getenv("CERAMIC_DOMAIN")
	if domain == "" {
		domain = "software-dev.ncsa.illinois.edu"
	}
	s := &server{
		clientset:     clientset,
		dynamicClient: dynamicClient,
		namespace:     namespace,
		image:         image,
		domain:        domain,
	}

	potteryOrigin := os.Getenv("POTTERY_ORIGIN")
	if potteryOrigin == "" {
		potteryOrigin = "https://ceramics.software-dev.ncsa.illinois.edu"
	}

	apiMux := http.NewServeMux()
	apiMux.Handle("GET /static/", http.StripPrefix("/static/", staticHandler()))
	apiMux.HandleFunc("GET /", handleHome)
	apiMux.HandleFunc("GET /api/ceramics", s.handleList)
	apiMux.HandleFunc("POST /api/ceramics", s.handleCreate)
	apiMux.HandleFunc("DELETE /api/ceramics/{name}", s.handleDelete)
	apiMux.Handle("GET /kiln/{name}", &kilnHandler{domain: domain})

	proxy := &ceramicProxy{resolve: s.resolveIP, potteryOrigin: potteryOrigin}

	// Requests to a ceramic's own hostname (cracked-vase-clay, cracked-vase-glaze)
	// go to the proxy; everything else (the pottery's own hostname) hits the API.
	root := http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		if _, _, ok := parseHost(r.Host); ok {
			proxy.ServeHTTP(w, r)
			return
		}
		apiMux.ServeHTTP(w, r)
	})

	addr := ":8000"
	log.Printf("pottery listening on %s (namespace=%s image=%s)", addr, namespace, image)
	log.Fatal(http.ListenAndServe(addr, root))
}
