# Part B — Kubernetes Deployment

## 1. Namespace

Deploy into a dedicated namespace with Pod Security Standards.

[namespace.yaml](namespace.yaml)

- Namespace `pyn3k8` is created with the **restricted** Pod Security Standard enforced:
  ```yaml
  pod-security.kubernetes.io/enforce: restricted
  pod-security.kubernetes.io/audit: restricted
  pod-security.kubernetes.io/warn: restricted
  ```
- This means Kubernetes will **reject** any pod that doesn't meet restricted level security (non root, no privilege escalation, drop capabilities, etc.).

---

## 2. Deployments (3 Services)

Deploy UI, API, and Worker as separate Deployments.

[ui-deployment.yaml](ui-deployment.yaml), [api-deployment.yaml](api-deployment.yaml), [worker-deployment.yaml](worker-deployment.yaml)

| Service | Image | Port | Replicas |
|---------|-------|------|----------|
| UI | `pyn3k8-ui:latest` | 5000 | 1 |
| API | `pyn3k8-api:latest` | 8080 | 2 |
| Worker | `pyn3k8-worker:latest` | 9090 | 2 |

All three use `RollingUpdate` strategy with `maxSurge: 1` and `maxUnavailable: 0` for zero downtime deploys.

---

## 3. Security Context (Non-Root, Hardened)

Containers must run as non root, drop capabilities, prevent privilege escalation, use read only filesystem.

Every deployment has both pod level and container level security:

**Pod level** (in all 3 deployments):
```yaml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  runAsGroup: 1000
  fsGroup: 1000
  seccompProfile:
    type: RuntimeDefault
```

**Container level** (in all 3 deployments):
```yaml
securityContext:
  allowPrivilegeEscalation: false
  readOnlyRootFilesystem: true
  capabilities:
    drop:
      - ALL
```

**Read only rootfs workaround:** An `emptyDir` volume is mounted at `/tmp` so the app can write temp files without making the root filesystem writable.


---

## 4. Resource Requests and Limits

Set CPU and memory requests/limits on all containers.

All 3 deployments have:
```yaml
resources:
  requests:
    cpu: 50m
    memory: 64Mi
  limits:
    cpu: 200m
    memory: 128Mi
```

This ensures the scheduler places pods correctly and prevents any single pod from consuming excessive resources.

---

## 5. Health Probes

Liveness, readiness, and startup probes on all services.

All 3 deployments have three probes:

| Probe | Path | Purpose |
|-------|------|---------|
| **Liveness** | `/healthz` | Restarts the pod if the app crashes |
| **Readiness** | `/readyz` | Removes from Service if not ready to serve traffic |
| **Startup** | `/healthz` | Gives the app time to start before liveness kicks in |

Example (same pattern on all services, different ports):
```yaml
livenessProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 10
readinessProbe:
  httpGet:
    path: /readyz
    port: 8080
  initialDelaySeconds: 3
  periodSeconds: 5
startupProbe:
  httpGet:
    path: /healthz
    port: 8080
  initialDelaySeconds: 2
  periodSeconds: 3
  failureThreshold: 10
```

---

## 6. Services (ClusterIP)

Expose each deployment via a Kubernetes Service.

[ui-service.yaml](ui-service.yaml), [api-service.yaml](api-service.yaml), [worker-service.yaml](worker-service.yaml)

| Service | Type | Port |
|---------|------|------|
| `ui-service` | ClusterIP | 5000 |
| `api-service` | ClusterIP | 8080 |
| `worker-service` | ClusterIP | 9090 |

All are `ClusterIP` — only reachable inside the cluster. External access goes through Ingress.

Services use DNS names for inter service communication (e.g. `http://api-service:8080`), configured via the ConfigMap.

---

## 7. ConfigMap and Secrets

Use ConfigMaps for config and Secrets for sensitive data. No hardcoded secrets in images.

[configmap.yaml](configmap.yaml), [secret.yaml](secret.yaml)

**ConfigMap** (`app-config`):
```yaml
data:
  LOG_LEVEL: "INFO"
  WORKER_URL: "http://worker-service:9090"
  API_URL: "http://api-service:8080"
```

**Secret** (`app-secrets`):
```yaml
data:
  SECRET_KEY: ZGV2LXNlY3JldC1rZXk=   # base64-encoded
```

Both are injected into pods via `envFrom`:
```yaml
envFrom:
  - configMapRef:
      name: app-config
  - secretRef:
      name: app-secrets
```

No secrets are baked into Docker images.

---

## 8. Ingress

Expose the UI externally via Ingress.

[ingress.yaml](ingress.yaml)

```yaml
spec:
  ingressClassName: nginx
  rules:
    - host: pyn3k8.local
      http:
        paths:
          - path: /
            pathType: Prefix
            backend:
              service:
                name: ui-service
                port:
                  number: 5000
```

- Uses the **nginx** ingress controller (enabled via `minikube addons enable ingress`).
- Host `pyn3k8.local` routes to the UI service.
- Only the UI is exposed externally — API and Worker are internal only.

---

## 9. NetworkPolicies

Restrict network traffic between pods (default deny + explicit allows).

[network-policies.yaml](network-policies.yaml) — 5 policies:

| Policy | What it does |
|--------|-------------|
| `default-deny-all` | Blocks **all** ingress and egress in the namespace by default |
| `allow-dns` | Allows all pods to reach DNS (kube-system, port 53) |
| `ui-policy` | UI can receive from ingress-nginx, can send to API only |
| `api-policy` | API can receive from UI and ingress-nginx, can send to Worker only |
| `worker-policy` | Worker can receive from API only |

**Traffic flow:**
```
Internet → Ingress → UI → API → Worker
```

No pod can talk to anything it shouldn't. This is the principle of least privilege applied to networking.

> **Note:** Requires a CNI that supports NetworkPolicies (e.g. Calico). Start Minikube with `--cni=calico`.

---

## 10. HPA (Horizontal Pod Autoscaler)

Auto scale the API based on CPU usage.

[api-hpa.yaml](api-hpa.yaml)

```yaml
spec:
  scaleTargetRef:
    apiVersion: apps/v1
    kind: Deployment
    name: api
  minReplicas: 2
  maxReplicas: 5
  metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
```

- API scales between **2 and 5 replicas**.
- Scales up when average CPU exceeds **70%**.
- Requires metrics-server (`minikube addons enable metrics-server`).

---

## 11. PodDisruptionBudgets (Bonus)

Ensure minimum availability during voluntary disruptions (node drains, upgrades).

[pdb.yaml](pdb.yaml)

```yaml
# One PDB per service, all with:
spec:
  minAvailable: 1
  selector:
    matchLabels:
      app: <service-name>
```

Three PDBs created: `ui-pdb`, `api-pdb`, `worker-pdb`. Each guarantees at least 1 pod stays running during cluster maintenance.

---

## 12. Structured JSON Logging

Application logs should be in structured JSON format.

All three Flask services output JSON formatted logs using Python's `logging` module. 


---
