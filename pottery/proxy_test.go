package main

import (
	"errors"
	"net/http"
	"net/http/httptest"
	"testing"
)

func TestAllowFraming(t *testing.T) {
	resp := &http.Response{Header: http.Header{}}
	resp.Header.Set("X-Frame-Options", "SAMEORIGIN")
	resp.Header.Set("Content-Security-Policy", "default-src 'self'")

	if err := allowFraming("https://ceramics.software-dev.ncsa.illinois.edu")(resp); err != nil {
		t.Fatalf("allowFraming returned error: %v", err)
	}
	if got := resp.Header.Get("X-Frame-Options"); got != "" {
		t.Errorf("X-Frame-Options = %q, want empty", got)
	}
	want := "frame-ancestors https://ceramics.software-dev.ncsa.illinois.edu"
	if got := resp.Header.Get("Content-Security-Policy"); got != want {
		t.Errorf("Content-Security-Policy = %q, want %q", got, want)
	}
}

func TestParseHost(t *testing.T) {
	cases := []struct {
		host     string
		wantName string
		wantPort string
		wantOK   bool
	}{
		{"ceramic-01-clay.software-dev.ncsa.illinois.edu", "ceramic-01", shellPort, true},
		{"ceramic-01-glaze.software-dev.ncsa.illinois.edu", "ceramic-01", appPort, true},
		{"ceramic-01-bat.software-dev.ncsa.illinois.edu", "ceramic-01", batPort, true},
		{"ceramic-01-clay.software-dev.ncsa.illinois.edu:443", "ceramic-01", shellPort, true},
		{"ceramic-01-glaze:8000", "ceramic-01", appPort, true},
		{"ceramic-01.software-dev.ncsa.illinois.edu", "", "", false},
		{"ceramic-01", "", "", false},
	}
	for _, c := range cases {
		name, port, ok := parseHost(c.host)
		if name != c.wantName || port != c.wantPort || ok != c.wantOK {
			t.Errorf("parseHost(%q) = (%q, %q, %v), want (%q, %q, %v)",
				c.host, name, port, ok, c.wantName, c.wantPort, c.wantOK)
		}
	}
}

// failingRoundTripper always fails, standing in for a dial to a dead IP.
type failingRoundTripper struct{}

func (failingRoundTripper) RoundTrip(req *http.Request) (*http.Response, error) {
	return nil, errors.New("connection refused")
}

func TestEvictingTransportEvictsOnFailure(t *testing.T) {
	var evicted string
	transport := &evictingTransport{
		RoundTripper: failingRoundTripper{},
		name:         "cracked-vase",
		evict:        func(name string) { evicted = name },
	}

	req := httptest.NewRequest(http.MethodGet, "http://10.0.0.1:8080/", nil)
	if _, err := transport.RoundTrip(req); err == nil {
		t.Fatal("RoundTrip: want error from failingRoundTripper, got nil")
	}
	if evicted != "cracked-vase" {
		t.Errorf("evict called with %q, want %q", evicted, "cracked-vase")
	}
}

func TestEvictingTransportDoesNotEvictOnSuccess(t *testing.T) {
	backend := httptest.NewServer(http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
	}))
	defer backend.Close()

	evictCalled := false
	transport := &evictingTransport{
		RoundTripper: http.DefaultTransport,
		name:         "cracked-vase",
		evict:        func(name string) { evictCalled = true },
	}

	req := httptest.NewRequest(http.MethodGet, backend.URL, nil)
	resp, err := transport.RoundTrip(req)
	if err != nil {
		t.Fatalf("RoundTrip: %v", err)
	}
	resp.Body.Close()
	if evictCalled {
		t.Error("evict called on a successful round trip")
	}
}

