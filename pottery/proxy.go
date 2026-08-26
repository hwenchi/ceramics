package main

import (
	"net/http"
	"net/http/httputil"
	"strings"
)

// ceramicProxy reverse-proxies requests to the right ceramic pod, chosen
// by the Host header, on the port chosen by which surface it names.
type ceramicProxy struct {
	resolver *cachingResolver
	// potteryOrigin is the pottery's own origin (e.g.
	// "https://ceramics.software-dev.ncsa.illinois.edu"), used to let the
	// glaze surface be iframed by the pottery despite whatever
	// frame-blocking headers the agent's app might send.
	potteryOrigin string
}

// evictingTransport wraps a transport and evicts a ceramic's cached IP
// whenever a round trip to it fails outright (connection refused, timeout,
// ...) — as opposed to the backend returning an HTTP error, which is a
// normal response, not a dead IP. This is the only point in the request
// lifecycle where a stale cache entry is observable: the real TCP dial
// happens here.
type evictingTransport struct {
	http.RoundTripper
	name  string
	evict func(name string)
}

func (t *evictingTransport) RoundTrip(req *http.Request) (*http.Response, error) {
	resp, err := t.RoundTripper.RoundTrip(req)
	if err != nil {
		t.evict(t.name)
	}
	return resp, err
}

// notYetGlazed serves a friendly placeholder instead of a raw connection
// error when nothing is listening on the glaze port yet — the normal state
// for a ceramic before anything's been built.
func notYetGlazed(w http.ResponseWriter, r *http.Request, err error) {
	w.Header().Set("Content-Type", "text/plain; charset=utf-8")
	w.WriteHeader(http.StatusServiceUnavailable)
	w.Write([]byte("nothing here yet — ask claude to build something"))
}

// allowFraming strips any frame-blocking headers a response sets and
// replaces them with a CSP that permits exactly the pottery's own origin.
// Without this, an agent-scaffolded app (e.g. one using Helmet defaults)
// could refuse to render inside the pottery's iframe for reasons entirely
// outside the agent's or the ceramic's control.
func allowFraming(potteryOrigin string) func(*http.Response) error {
	return func(resp *http.Response) error {
		resp.Header.Del("X-Frame-Options")
		resp.Header.Set("Content-Security-Policy", "frame-ancestors "+potteryOrigin)
		return nil
	}
}

const (
	claySuffix  = "-clay"
	glazeSuffix = "-glaze"
	batSuffix   = "-bat"
	shellPort   = "7681"
	appPort     = "8080"
	batPort     = "8082"
)

// ceramicHostnames builds a ceramic's surface hostnames from its name and
// the cluster's domain (e.g. "software-dev.ncsa.illinois.edu").
func ceramicHostnames(name, domain string) (clay, glaze, bat string) {
	return name + claySuffix + "." + domain, name + glazeSuffix + "." + domain, name + batSuffix + "." + domain
}

// parseHost splits a Host header like "cracked-vase-clay.software-dev...:443"
// into the ceramic name ("cracked-vase") and the backend port for the
// surface named by the suffix ("-clay", "-glaze", or "-bat"). ok is false
// if the host doesn't name a recognized surface.
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
	case strings.HasSuffix(label, batSuffix):
		return strings.TrimSuffix(label, batSuffix), batPort, true
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

	ip, err := p.resolver.resolveIP(r.Context(), name)
	if err != nil {
		http.Error(w, err.Error(), http.StatusBadGateway)
		return
	}

	proxy := &httputil.ReverseProxy{
		Director: func(req *http.Request) {
			req.URL.Scheme = "http"
			req.URL.Host = ip + ":" + port
		},
		Transport: &evictingTransport{RoundTripper: http.DefaultTransport, name: name, evict: p.resolver.evict},
	}
	if port == appPort {
		proxy.ModifyResponse = allowFraming(p.potteryOrigin)
		proxy.ErrorHandler = notYetGlazed
	}
	proxy.ServeHTTP(w, r)
}
