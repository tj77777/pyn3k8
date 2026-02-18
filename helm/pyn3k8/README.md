# pyn3k8 Helm Chart

Helm chart for deploying the pyn3k8 microservices application (UI, API, Worker) on Kubernetes.

## Chart Info

| Field | Value |
|-------|-------|
| Chart Name | pyn3k8 |
| Chart Version | 0.1.0 |
| App Version | 1.0.0 |
| Type | application |

## Prerequisites

- Kubernetes cluster (Minikube recommended for local development)
- Helm v3 installed
- Container images built and available to the cluster
- Minikube addons (for local development):
  - `ingress` (nginx ingress controller)
  - `metrics-server` (for HPA)
  - `calico` CNI (for NetworkPolicy support)

## Build Images (Minikube)

Before installing the chart, build all service images inside Minikube's Docker environment:

```bash
eval $(minikube docker-env)
docker build -t pyn3k8-ui:latest services/ui/
docker build -t pyn3k8-api:latest services/api/
docker build -t pyn3k8-worker:latest services/worker/
```

## Installation Instructions

### 1. Lint the chart first

```bash
helm lint helm/pyn3k8/
```

### 2. Install with default (dev) values

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace
```

### 3. Install with production values

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace -f helm/pyn3k8/values-prod.yaml
```

### 4. Install with custom overrides

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace \
  --set api.replicaCount=3 \
  --set ingress.host=myapp.local
```

### 5. Dry-run to preview rendered manifests

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace --dry-run --debug
```

### 6. Verify the deployment

```bash
kubectl get pods,svc,ingress,netpol,hpa,pdb -n pyn3k8
```

## Upgrade Instructions

### Upgrade with new values

```bash
helm upgrade pyn3k8 helm/pyn3k8/ -n pyn3k8
```

### Upgrade to production values

```bash
helm upgrade pyn3k8 helm/pyn3k8/ -n pyn3k8 -f helm/pyn3k8/values-prod.yaml
```

### Upgrade with specific image tags

```bash
helm upgrade pyn3k8 helm/pyn3k8/ -n pyn3k8 \
  --set ui.image.tag=v1.2.0 \
  --set api.image.tag=v1.2.0 \
  --set worker.image.tag=v1.2.0
```

### Check release history after upgrade

```bash
helm history pyn3k8 -n pyn3k8
```

## Rollback Procedure

### 1. List available revisions

```bash
helm history pyn3k8 -n pyn3k8
```

Example output:

```
REVISION  STATUS      CHART          APP VERSION  DESCRIPTION
1         superseded  pyn3k8-0.1.0   1.0.0        Install complete
2         deployed    pyn3k8-0.1.0   1.0.0        Upgrade complete
```

### 2. Rollback to a specific revision

```bash
helm rollback pyn3k8 1 -n pyn3k8
```

### 3. Verify rollback

```bash
helm status pyn3k8 -n pyn3k8
kubectl get pods -n pyn3k8
```

### 4. Rollback tips

- Helm keeps release history (default 10 revisions).
- Rollback re-deploys the exact manifest state from that revision.
- Pods will perform a rolling update to the previous image/config.
- Always verify pod health after rollback:

```bash
kubectl get pods -n pyn3k8 -w
```

## Accessing the UI in Minikube

### Option A: Via Ingress (recommended)

```bash
minikube addons enable ingress
minikube addons enable metrics-server
echo "$(minikube ip) pyn3k8.local" | sudo tee -a /etc/hosts
```

Then open: http://pyn3k8.local/

### Option B: Via port-forward

```bash
kubectl port-forward -n pyn3k8 svc/ui-service 5000:5000
```

Then open: http://localhost:5000/

### Option C: Via Minikube service tunnel

```bash
minikube service ui-service -n pyn3k8
```

## Values Files

| File | Purpose |
|------|---------|
| `values.yaml` | Dev defaults (low replicas, low resources, `latest` tags) |
| `values-prod.yaml` | Production overrides (higher replicas, more resources, stricter log level) |

### Key configurable values

| Value | Default | Description |
|-------|---------|-------------|
| `namespace` | `pyn3k8` | Kubernetes namespace |
| `ui.replicaCount` | `1` | UI pod replicas |
| `api.replicaCount` | `2` | API pod replicas |
| `worker.replicaCount` | `2` | Worker pod replicas |
| `ingress.enabled` | `true` | Enable Ingress resource |
| `ingress.host` | `pyn3k8.local` | Ingress hostname |
| `networkPolicies.enabled` | `true` | Enable NetworkPolicies |
| `config.logLevel` | `INFO` | Application log level |
| `secrets.secretKey` | `dev-secret-key` | App secret (override in production) |

## Uninstall

```bash
helm uninstall pyn3k8 -n pyn3k8
kubectl delete namespace pyn3k8
```

## Chart Structure

```
helm/pyn3k8/
├── Chart.yaml             # Chart metadata
├── values.yaml            # Dev defaults
├── values-prod.yaml       # Production overrides
├── .helmignore            # Files excluded from chart packaging
└── templates/
    ├── _helpers.tpl        # Shared template helpers
    ├── namespace.yaml      # Namespace with pod security labels
    ├── configmap.yaml      # Application configuration
    ├── secret.yaml         # Application secrets
    ├── ui-deployment.yaml  # UI Deployment
    ├── ui-service.yaml     # UI ClusterIP Service
    ├── api-deployment.yaml # API Deployment
    ├── api-service.yaml    # API ClusterIP Service
    ├── api-hpa.yaml        # API HorizontalPodAutoscaler
    ├── worker-deployment.yaml  # Worker Deployment
    ├── worker-service.yaml     # Worker ClusterIP Service
    ├── ingress.yaml        # Nginx Ingress
    ├── network-policies.yaml   # Default deny + explicit allows
    ├── pdb.yaml            # PodDisruptionBudgets
    ├── NOTES.txt           # Post-install instructions
    └── README.md           # This file
```
