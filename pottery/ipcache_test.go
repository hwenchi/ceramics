package main

import (
	"context"
	"errors"
	"testing"
)

func TestCachingResolverCachesAfterFirstResolve(t *testing.T) {
	calls := 0
	c := newCachingResolver(func(ctx context.Context, name string) (string, error) {
		calls++
		return "10.0.0.1", nil
	})

	for i := 0; i < 3; i++ {
		ip, err := c.resolveIP(context.Background(), "cracked-vase")
		if err != nil {
			t.Fatalf("resolveIP: %v", err)
		}
		if ip != "10.0.0.1" {
			t.Errorf("resolveIP = %q, want %q", ip, "10.0.0.1")
		}
	}
	if calls != 1 {
		t.Errorf("underlying resolveFunc called %d times, want 1", calls)
	}
}

func TestCachingResolverDoesNotCacheErrors(t *testing.T) {
	calls := 0
	c := newCachingResolver(func(ctx context.Context, name string) (string, error) {
		calls++
		return "", errors.New("not scheduled yet")
	})

	for i := 0; i < 2; i++ {
		if _, err := c.resolveIP(context.Background(), "cracked-vase"); err == nil {
			t.Fatalf("resolveIP: want error, got nil")
		}
	}
	if calls != 2 {
		t.Errorf("underlying resolveFunc called %d times, want 2 (errors should not be cached)", calls)
	}
}

func TestCachingResolverEvictForcesRefetch(t *testing.T) {
	calls := 0
	ips := []string{"10.0.0.1", "10.0.0.2"}
	c := newCachingResolver(func(ctx context.Context, name string) (string, error) {
		ip := ips[calls]
		calls++
		return ip, nil
	})

	ip, _ := c.resolveIP(context.Background(), "cracked-vase")
	if ip != "10.0.0.1" {
		t.Fatalf("resolveIP = %q, want %q", ip, "10.0.0.1")
	}

	c.evict("cracked-vase")

	ip, _ = c.resolveIP(context.Background(), "cracked-vase")
	if ip != "10.0.0.2" {
		t.Fatalf("resolveIP after evict = %q, want %q", ip, "10.0.0.2")
	}
	if calls != 2 {
		t.Errorf("underlying resolveFunc called %d times, want 2", calls)
	}
}

func TestCachingResolverEvictOfUncachedNameIsNoop(t *testing.T) {
	c := newCachingResolver(func(ctx context.Context, name string) (string, error) {
		return "10.0.0.1", nil
	})
	c.evict("never-resolved") // must not panic
}

func TestCachingResolverKeepsNamesSeparate(t *testing.T) {
	c := newCachingResolver(func(ctx context.Context, name string) (string, error) {
		return "ip-for-" + name, nil
	})

	a, _ := c.resolveIP(context.Background(), "a")
	b, _ := c.resolveIP(context.Background(), "b")
	if a != "ip-for-a" || b != "ip-for-b" {
		t.Errorf("resolveIP(a)=%q resolveIP(b)=%q, want ip-for-a / ip-for-b", a, b)
	}
}
