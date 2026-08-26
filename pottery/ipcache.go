package main

import (
	"context"
	"sync"
)

// resolveFunc looks up a ceramic's IP from the source of truth (in
// production, s.resolveIP hitting the Kubernetes API).
type resolveFunc func(ctx context.Context, name string) (string, error)

// cachingResolver wraps a resolveFunc with an in-memory cache keyed by
// ceramic name. Ceramic pods never restart (RestartPolicyNever), so a
// resolved IP stays valid for the pod's whole life — caching turns what
// would otherwise be a Kubernetes API call on every proxied HTTP request
// into one call per ceramic.
type cachingResolver struct {
	resolve resolveFunc

	mu    sync.RWMutex
	cache map[string]string
}

func newCachingResolver(resolve resolveFunc) *cachingResolver {
	return &cachingResolver{resolve: resolve, cache: make(map[string]string)}
}

func (c *cachingResolver) resolveIP(ctx context.Context, name string) (string, error) {
	c.mu.RLock()
	ip, ok := c.cache[name]
	c.mu.RUnlock()
	if ok {
		return ip, nil
	}

	ip, err := c.resolve(ctx, name)
	if err != nil {
		return "", err
	}

	c.mu.Lock()
	c.cache[name] = ip
	c.mu.Unlock()
	return ip, nil
}

// evict forces the next resolveIP call for name to re-fetch. Called on
// ceramic delete, and when a proxied connection to a cached IP fails.
func (c *cachingResolver) evict(name string) {
	c.mu.Lock()
	delete(c.cache, name)
	c.mu.Unlock()
}
