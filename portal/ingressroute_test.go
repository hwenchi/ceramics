package main

import (
	"reflect"
	"testing"
)

func TestDomainListWith(t *testing.T) {
	empty := []interface{}{}
	got := domainListWith(empty, "ceramic-01-clay.software-dev.ncsa.illinois.edu")
	want := []interface{}{map[string]interface{}{"main": "ceramic-01-clay.software-dev.ncsa.illinois.edu"}}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("domainListWith(empty, ...) = %v, want %v", got, want)
	}

	// adding the same host again is a no-op, not a duplicate
	got2 := domainListWith(got, "ceramic-01-clay.software-dev.ncsa.illinois.edu")
	if !reflect.DeepEqual(got2, want) {
		t.Errorf("domainListWith should not duplicate an existing host, got %v", got2)
	}
}

func TestDomainListWithout(t *testing.T) {
	domains := []interface{}{
		map[string]interface{}{"main": "ceramic-01-clay.software-dev.ncsa.illinois.edu"},
		map[string]interface{}{"main": "ceramic-01-glaze.software-dev.ncsa.illinois.edu"},
	}
	got := domainListWithout(domains, "ceramic-01-clay.software-dev.ncsa.illinois.edu")
	want := []interface{}{map[string]interface{}{"main": "ceramic-01-glaze.software-dev.ncsa.illinois.edu"}}
	if !reflect.DeepEqual(got, want) {
		t.Errorf("domainListWithout = %v, want %v", got, want)
	}

	// removing a host that isn't present is a no-op
	got2 := domainListWithout(want, "not-there.software-dev.ncsa.illinois.edu")
	if !reflect.DeepEqual(got2, want) {
		t.Errorf("domainListWithout of absent host should be a no-op, got %v", got2)
	}
}
