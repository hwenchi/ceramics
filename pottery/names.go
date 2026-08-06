package main

import (
	"fmt"
	"math/rand"

	corev1 "k8s.io/api/core/v1"
)

var nameAdjectives = []string{
	"cracked", "chipped", "glazed", "unglazed", "fired", "hardened",
	"brittle", "sturdy", "hollow", "smooth", "rough", "warped",
	"polished", "matte", "glossy", "earthen", "speckled", "textured",
	"slender", "squat",
}

var nameNouns = []string{
	"vase", "bowl", "mug", "urn", "jar", "plate", "pot", "teapot",
	"pitcher", "tile", "jug", "dish", "planter", "ramekin", "ewer",
	"chalice", "tureen", "crock", "canister", "amphora",
}

func pickName(taken map[string]bool) string {
	const maxAttempts = 10000
	for i := 0; i < maxAttempts; i++ {
		candidate := fmt.Sprintf("%s-%s",
			nameAdjectives[rand.Intn(len(nameAdjectives))],
			nameNouns[rand.Intn(len(nameNouns))])
		if !taken[candidate] {
			return candidate
		}
	}
	panic(fmt.Sprintf("pickName: no unique name found in %d attempts", maxAttempts))
}

// randomName picks a name not already used by any of the given pods.
func randomName(pods []corev1.Pod) string {
	taken := make(map[string]bool, len(pods))
	for _, p := range pods {
		taken[p.Name] = true
	}
	return pickName(taken)
}
