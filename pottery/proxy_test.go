package main

import (
	"net/http"
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
