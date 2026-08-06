package main

import (
	"context"
	"fmt"

	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/apimachinery/pkg/apis/meta/v1/unstructured"
	"k8s.io/apimachinery/pkg/runtime/schema"
)

var ingressRouteGVR = schema.GroupVersionResource{
	Group:    "traefik.io",
	Version:  "v1alpha1",
	Resource: "ingressroutes",
}

const potteryIngressRouteName = "pottery"

// domainListWithout returns domains with any entry for the given host
// removed (a no-op if it's not present).
func domainListWithout(domains []interface{}, host string) []interface{} {
	out := make([]interface{}, 0, len(domains))
	for _, d := range domains {
		entry, ok := d.(map[string]interface{})
		if ok && entry["main"] == host {
			continue
		}
		out = append(out, d)
	}
	return out
}

// domainListWith returns domains with an entry for the given host added,
// unless one already exists.
func domainListWith(domains []interface{}, host string) []interface{} {
	for _, d := range domains {
		if entry, ok := d.(map[string]interface{}); ok && entry["main"] == host {
			return domains
		}
	}
	return append(domains, map[string]interface{}{"main": host})
}

// setIngressRouteDomains reads the pottery IngressRoute's spec.tls.domains,
// applies fn to the list, and writes it back. No retry-on-conflict: this
// object is touched at most a few times a month (ceramic create/delete),
// so a lost update from a concurrent edit is not worth guarding against.
func (s *server) setIngressRouteDomains(ctx context.Context, fn func([]interface{}) []interface{}) error {
	client := s.dynamicClient.Resource(ingressRouteGVR).Namespace(s.namespace)

	obj, err := client.Get(ctx, potteryIngressRouteName, metav1.GetOptions{})
	if err != nil {
		return fmt.Errorf("get IngressRoute: %w", err)
	}

	domains, _, err := unstructured.NestedSlice(obj.Object, "spec", "tls", "domains")
	if err != nil {
		return fmt.Errorf("read spec.tls.domains: %w", err)
	}

	if err := unstructured.SetNestedSlice(obj.Object, fn(domains), "spec", "tls", "domains"); err != nil {
		return fmt.Errorf("write spec.tls.domains: %w", err)
	}

	_, err = client.Update(ctx, obj, metav1.UpdateOptions{})
	if err != nil {
		return fmt.Errorf("update IngressRoute: %w", err)
	}
	return nil
}
