package main

import (
	"context"
	"net/http"
	"net/http/httputil"
	"strings"
)

// resolver looks up the backend IP for a ceramic name. In production this
// is s.resolveIP; tests can supply one that points at a local test server.
type resolver func(ctx context.Context, name string) (string, error)

// ceramicProxy reverse-proxies requests to the right ceramic pod, chosen
// by the Host header, on the port chosen by which surface it names.
type ceramicProxy struct {
	resolve resolver
	// portalOrigin is the portal's own origin (e.g.
	// "https://ceramics.software-dev.ncsa.illinois.edu"), used to let the
	// glaze surface be iframed by the portal despite whatever
	// frame-blocking headers the agent's app might send.
	portalOrigin string
}

// allowFraming strips any frame-blocking headers a response sets and
// replaces them with a CSP that permits exactly the portal's own origin.
// Without this, an agent-scaffolded app (e.g. one using Helmet defaults)
// could refuse to render inside the portal's iframe for reasons entirely
// outside the agent's or the ceramic's control.
func allowFraming(portalOrigin string) func(*http.Response) error {
	return func(resp *http.Response) error {
		resp.Header.Del("X-Frame-Options")
		resp.Header.Set("Content-Security-Policy", "frame-ancestors "+portalOrigin)
		return nil
	}
}

const (
	claySuffix  = "-clay"
	glazeSuffix = "-glaze"
	shellPort   = "7681"
	appPort     = "8080"
)

// parseHost splits a Host header like "ceramic-01-clay.software-dev...:443"
// into the ceramic name ("ceramic-01") and the backend port for the surface
// named by the suffix ("-clay" or "-glaze"). ok is false if the host
// doesn't name a recognized surface.
func parseHost(host string) (name string, port string, ok bool) {
	label := host
	if i := strings.IndexAny(label, ".:"); i != -1 {
		label = label[:i]
	}
	switch {
	case strings.HasSuffix(label, claySuffix):
		return strings.TrimSuffix(label, claySuffix), shellPort, true
	case strings.HasSuffix(label, glazeSuffix):
		return strings.TrimSuffix(label, glazeSuffix), appPort, true
	default:
		return "", "", false
	}
}

func (p *ceramicProxy) ServeHTTP(w http.ResponseWriter, r *http.Request) {
	name, port, ok := parseHost(r.Host)
	if !ok {
		http.Error(w, "unrecognized ceramic host: "+r.Host, http.StatusNotFound)
		return
	}

	ip, err := p.resolve(r.Context(), name)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = "http"
			req.URL.Host = ip + ":" + port
		},
	}
	if port == appPort {
		proxy.ModifyResponse = allowFraming(p.portalOrigin)
	}
	proxy.ServeHTTP(w, r)
}
