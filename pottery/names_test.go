package main

import (
	"fmt"
	"regexp"
	"testing"
)

var nameFormatRe = regexp.MustCompile(`^[a-z]+-[a-z]+$`)

func TestPickNameFormat(t *testing.T) {
	name := pickName(map[string]bool{})
	if !nameFormatRe.MatchString(name) {
		t.Errorf("pickName() = %q, want format adjective-noun", name)
	}
}

func TestPickNameAvoidsTaken(t *testing.T) {
	taken := map[string]bool{"cracked-vase": true}
	for i := 0; i < 100; i++ {
		if name := pickName(taken); taken[name] {
			t.Fatalf("pickName() returned a taken name: %q", name)
		}
	}
}

func TestPickNameFindsTheOnlyGap(t *testing.T) {
	taken := map[string]bool{}
	for _, a := range nameAdjectives {
		for _, n := range nameNouns {
			taken[fmt.Sprintf("%s-%s", a, n)] = true
		}
	}
	gap := fmt.Sprintf("%s-%s", nameAdjectives[0], nameNouns[0])
	delete(taken, gap)

	if got := pickName(taken); got != gap {
		t.Errorf("pickName() = %q, want the only untaken name %q", got, gap)
	}
}
