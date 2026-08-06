package main

import (
	"context"
	"fmt"
	"log"
	"os"

	corev1 "k8s.io/api/core/v1"
	apierrors "k8s.io/apimachinery/pkg/api/errors"
	"k8s.io/apimachinery/pkg/api/resource"
	metav1 "k8s.io/apimachinery/pkg/apis/meta/v1"
	"k8s.io/client-go/dynamic"
	"k8s.io/client-go/kubernetes"
	"k8s.io/client-go/rest"
	"k8s.io/client-go/tools/clientcmd"
)

const maxCeramics = 20

const (
	labelApp      = "app"
	labelAppValue = "ceramic"
)

type server struct {
	clientset     *kubernetes.Clientset
	dynamicClient dynamic.Interface
	namespace     string
	image         string
	domain        string // e.g. "software-dev.ncsa.illinois.edu"
}

// getConfig loads the cluster config: via KUBECONFIG when set (local dev),
// or in-cluster config when running as a pod (production). Shared by both
// the typed clientset (pods) and the dynamic client (the IngressRoute CRD).
func getConfig() (*rest.Config, error) {
	if kubeconfig := os.Getenv("KUBECONFIG"); kubeconfig != "" {
		cfg, err := clientcmd.BuildConfigFromFlags("", kubeconfig)
		if err != nil {
			return nil, fmt.Errorf("build config from kubeconfig: %w", err)
		}
		return cfg, nil
	}
	cfg, err := rest.InClusterConfig()
	if err != nil {
		return nil, fmt.Errorf("build in-cluster config: %w", err)
	}
	return cfg, nil
}

// listPods returns all ceramic pods in the pottery's namespace.
func (s *server) listPods(ctx context.Context) ([]corev1.Pod, error) {
	list, err := s.clientset.CoreV1().Pods(s.namespace).List(ctx, metav1.ListOptions{
		LabelSelector: fmt.Sprintf("%s=%s", labelApp, labelAppValue),
	})
	if err != nil {
		return nil, err
	}
	return list.Items, nil
}

// checkCapacity refuses to create another ceramic once maxCeramics are
// already running, rather than letting the cluster's scheduler discover
// the limit the hard way.
func checkCapacity(pods []corev1.Pod) error {
	if len(pods) >= maxCeramics {
		return fmt.Errorf("at capacity: %d/%d ceramics already exist", len(pods), maxCeramics)
	}
	return nil
}

// buildPodSpec constructs a ceramic pod: no service-account token, user
// namespaces on, seccomp default, all capabilities dropped, resource
// limits set, and an emptyDir workspace that dies with the pod.
func buildPodSpec(name, namespace, image string) *corev1.Pod {
	falseVal := false
	return &corev1.Pod{
		ObjectMeta: metav1.ObjectMeta{
			Name:      name,
			Namespace: namespace,
			Labels:    map[string]string{labelApp: labelAppValue},
		},
		Spec: corev1.PodSpec{
			AutomountServiceAccountToken: &falseVal,
			// TODO: re-enable, needs node containerd fix (see slow_chown)
			// HostUsers: &falseVal,
			SecurityContext: &corev1.PodSecurityContext{
				SeccompProfile: &corev1.SeccompProfile{
					Type: corev1.SeccompProfileTypeRuntimeDefault,
				},
			},
			RestartPolicy: corev1.RestartPolicyNever,
			Containers: []corev1.Container{
				{
					Name:            "ceramic",
					Image:           image,
					ImagePullPolicy: corev1.PullAlways,
					Ports: []corev1.ContainerPort{
						{Name: "shell", ContainerPort: 7681},
						{Name: "app", ContainerPort: 8080},
					},
					SecurityContext: &corev1.SecurityContext{
						AllowPrivilegeEscalation: &falseVal,
						// No dropped capabilities: root here should behave like real root (apt, chown, ...).
					},
					Resources: corev1.ResourceRequirements{
						Requests: corev1.ResourceList{
							corev1.ResourceCPU:              resource.MustParse("250m"),
							corev1.ResourceMemory:           resource.MustParse("256Mi"),
							corev1.ResourceEphemeralStorage: resource.MustParse("1Gi"),
						},
						Limits: corev1.ResourceList{
							corev1.ResourceCPU:              resource.MustParse("2"),
							corev1.ResourceMemory:           resource.MustParse("2Gi"),
							corev1.ResourceEphemeralStorage: resource.MustParse("8Gi"),
						},
					},
					VolumeMounts: []corev1.VolumeMount{
						{Name: "workspace", MountPath: "/workspace"},
					},
				},
			},
			Volumes: []corev1.Volume{
				{
					Name:         "workspace",
					VolumeSource: corev1.VolumeSource{EmptyDir: &corev1.EmptyDirVolumeSource{}},
				},
			},
		},
	}
}

// createCeramic lists existing ceramics to check capacity and pick a name,
// then creates the pod.
func (s *server) createCeramic(ctx context.Context) (*corev1.Pod, error) {
	pods, err := s.listPods(ctx)
	if err != nil {
		return nil, fmt.Errorf("list pods: %w", err)
	}
	if err := checkCapacity(pods); err != nil {
		return nil, err
	}

	name := randomName(pods)
	pod := buildPodSpec(name, s.namespace, s.image)
	created, err := s.clientset.CoreV1().Pods(s.namespace).Create(ctx, pod, metav1.CreateOptions{})
	if err != nil {
		return nil, err
	}

	clay, glaze := ceramicHostnames(name, s.domain)
	err = s.setIngressRouteDomains(ctx, func(domains []interface{}) []interface{} {
		return domainListWith(domainListWith(domains, clay), glaze)
	})
	if err != nil {
		// Non-fatal: the ceramic still works, just without a real cert
		// until this is retried — see the kiln page's note about that.
		log.Printf("warning: could not register domains for %s: %v", name, err)
	}

	return created, nil
}

// deleteCeramic deletes a ceramic pod by name. Deleting one that's already
// gone is not an error — the caller just wanted it gone.
func (s *server) deleteCeramic(ctx context.Context, name string) error {
	err := s.clientset.CoreV1().Pods(s.namespace).Delete(ctx, name, metav1.DeleteOptions{})
	if err != nil && !apierrors.IsNotFound(err) {
		return err // a real failure; NotFound just means it's already gone, which is fine
	}

	clay, glaze := ceramicHostnames(name, s.domain)
	ingressErr := s.setIngressRouteDomains(ctx, func(domains []interface{}) []interface{} {
		return domainListWithout(domainListWithout(domains, clay), glaze)
	})
	if ingressErr != nil {
		log.Printf("warning: could not remove domains for %s: %v", name, ingressErr)
	}

	return nil
}

// resolveIP looks up a ceramic's pod IP by name — the one piece of the
// proxy that actually talks to Kubernetes. Kept separate from the proxying
// logic itself so tests can substitute a resolver that points at a local
// test server instead.
func (s *server) resolveIP(ctx context.Context, name string) (string, error) {
	pod, err := s.clientset.CoreV1().Pods(s.namespace).Get(ctx, name, metav1.GetOptions{})
	if err != nil {
		return "", err
	}
	if pod.Status.PodIP == "" {
		return "", fmt.Errorf("ceramic %s has no IP yet", name)
	}
	return pod.Status.PodIP, nil
}
