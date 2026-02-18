# Deployment Guide

Step by step guide for deploying the pyn3k8 microservices application to Minikube.

## Prerequisites

Ensure the following tools are installed:

| Tool | Purpose | Install |
|------|---------|---------|
| Docker | Container runtime | https://docs.docker.com/get-docker/ |
| Minikube | Local Kubernetes cluster | https://minikube.sigs.k8s.io/docs/start/ |
| kubectl | Kubernetes CLI | https://kubernetes.io/docs/tasks/tools/ |
| Helm | Kubernetes package manager | https://helm.sh/docs/intro/install/ |

---

## Step 1: Start Minikube with Calico CNI

Delete any existing cluster and start fresh with Calico for NetworkPolicy enforcement:

```bash
minikube delete
minikube start --cni=calico --memory=4096 --cpus=2
```

Expected output:
```
* Configuring Calico (Container Networking Interface) ...
* Verifying Kubernetes components...
* Done! kubectl is now configured to use "minikube" cluster
```

**Why Calico?** The default Minikube CNI does not enforce NetworkPolicies. Calico is required for defaultdeny + explicit allow network policies to actually take effect.

Verify Calico is running:
```bash
kubectl get pods -n kube-system | grep calico
```

Expected output:
```
calico-kube-controllers-xxxxx   1/1     Running   0          2m
calico-node-xxxxx               1/1     Running   0          2m
```

## Step 2: Enable Required Addons

```bash
minikube addons enable ingress
minikube addons enable metrics-server
```

- **ingress** -- Nginx ingress controller for routing external traffic to the UI
- **metrics-server** -- Required for HPA (Horizontal Pod Autoscaler) CPU metrics

Verify addons:
```bash
minikube addons list | grep -E "ingress|metrics"
```

## Step 3: Point Docker to Minikube's Docker Daemon

This makes images you build available directly inside the Minikube node without pushing to a registry:

```bash
eval $(minikube docker-env)
```

> **Note:** This command only affects the current terminal session. Run it again if you open a new terminal.

## Step 4: Build Docker Images

Build all three service images:

```bash
docker build -t pyn3k8-ui:latest services/ui/
docker build -t pyn3k8-api:latest services/api/
docker build -t pyn3k8-worker:latest services/worker/
```

### Verify Images

Check image sizes:
```bash
docker images | grep pyn3k8
```

## Step 5: Lint the Helm Chart

```bash
helm lint helm/pyn3k8/
```

Expected output:
```
==> Linting helm/pyn3k8/
[INFO] Chart.yaml: icon is recommended
1 chart(s) linted, 0 chart(s) failed
```

## Step 6: Deploy with Helm

### Development deployment (default values):

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace
```

### Production deployment:

```bash
helm install pyn3k8 helm/pyn3k8/ -n pyn3k8 --create-namespace -f helm/pyn3k8/values-prod.yaml
```

Expected output:
```
NAME: pyn3k8
LAST DEPLOYED: ...
NAMESPACE: pyn3k8
STATUS: deployed
REVISION: 1
```

## Step 7: Verify All Resources

### Check pods are running:
```bash
kubectl get pods -n pyn3k8
```

Expected output (all pods should be `1/1 Running`):
```
NAME                      READY   STATUS    RESTARTS   AGE
api-696479bd9f-5z7p2      1/1     Running   0          66s
api-696479bd9f-r2qch      1/1     Running   0          50s
ui-845fdcb6f7-bxb8z       1/1     Running   0          66s
worker-7c4455c9bc-8gl6w   1/1     Running   0          66s
worker-7c4455c9bc-g4d9b   1/1     Running   0          66s
```

### Check all resources:
```bash
kubectl get svc,ingress,netpol,hpa,pdb -n pyn3k8
```

Expected resources:
- **3 Services**: `ui-service:5000`, `api-service:8080`, `worker-service:9090` (all ClusterIP)
- **1 Ingress**: `pyn3k8-ingress` with host `pyn3k8.local`
- **5 NetworkPolicies**: `default-deny-all`, `allow-dns`, `ui-policy`, `api-policy`, `worker-policy`
- **1 HPA**: `api-hpa` targeting CPU at 70%
- **3 PDBs**: `ui-pdb`, `api-pdb`, `worker-pdb` (minAvailable: 1)

## Step 8: Test Health Endpoints

Since the images are minimal (no curl/wget), use Python to test:

```bash
kubectl exec -n pyn3k8 deploy/ui -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:5000/healthz').read().decode())"

kubectl exec -n pyn3k8 deploy/api -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:8080/healthz').read().decode())"

kubectl exec -n pyn3k8 deploy/worker -- python -c \
  "import urllib.request; print(urllib.request.urlopen('http://localhost:9090/healthz').read().decode())"
```

All three should return:
```json
{"status":"ok"}
```

## Step 9: Test End to End Flow

Create a task via the API (which internally calls the Worker):

```bash
kubectl exec -n pyn3k8 deploy/api -- python -c "
import urllib.request, json
req = urllib.request.Request(
    'http://localhost:8080/tasks',
    data=json.dumps({'name':'test-task'}).encode(),
    headers={'Content-Type':'application/json'},
    method='POST'
)
print(urllib.request.urlopen(req).read().decode())
"
```

Expected output (task processed by Worker):
```json
{
  "id": "60acd2a5-...",
  "name": "test-task",
  "status": "completed",
  "worker": "worker-7c4455c9bc-8gl6w",
  "created_at": "2026-02-16T12:25:09...",
  "processed_at": "2026-02-16T12:25:09..."
}
```

Verify structured JSON logging:
```bash
kubectl logs -n pyn3k8 deploy/worker --all-containers | grep "Processing"
```

Expected output:
```json
{"timestamp": "2026-02-16T12:25:09.229590+00:00", "level": "INFO", "service": "worker", "message": "Processing task 60acd2a5-...", "module": "app"}
```

## Step 10: Access the UI

### Option A -- Via Ingress (recommended)

On macOS with Docker driver, use `minikube tunnel`:

```bash
# In a separate terminal
minikube tunnel
```

Then add the hosts entry:
```bash
echo "127.0.0.1 pyn3k8.local" | sudo tee -a /etc/hosts
```

Open http://pyn3k8.local/ in your browser.

### Option B -- Via Port Forward

```bash
kubectl port-forward -n pyn3k8 svc/ui-service 5000:5000
```

Open http://localhost:5000/ in your browser.

---

## Upgrade

Upgrade with new image tag:
```bash
helm upgrade pyn3k8 helm/pyn3k8/ -n pyn3k8 --set api.image.tag=v2.0.0
```

Upgrade to production values:
```bash
helm upgrade pyn3k8 helm/pyn3k8/ -n pyn3k8 -f helm/pyn3k8/values-prod.yaml
```

## Rollback

View release history:
```bash
helm history pyn3k8 -n pyn3k8
```

Rollback to a previous revision:
```bash
helm rollback pyn3k8 1 -n pyn3k8
```

Verify rollback:
```bash
kubectl get pods -n pyn3k8
```

## Uninstall

```bash
helm uninstall pyn3k8 -n pyn3k8
kubectl delete namespace pyn3k8
```