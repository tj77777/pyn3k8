# Part D — Production Readiness Discussion

---

## 1. How would you manage secrets in production?


Kubernetes Secrets are only base64-encoded, not encrypted. For real production:

| Tool | What it does | Why use it |
|------|-------------|-----------|
| **HashiCorp Vault** | Stores secrets outside Kubernetes, injects them into pods at runtime | Secrets never sit in etcd |
| **External Secrets Operator** | Syncs secrets from AWS/Azure/GCP secret managers into K8s Secrets automatically | Works with cloud-native secret stores |

**Key rule:** Rotate secrets regularly and never commit them to Git unencrypted.

---

## 2. How would you implement CI/CD for this system?

> **Best Practice:** Separate CI and CD into two independent systems.  
> **Jenkins** handles Continuous Integration (build, test, push images).  
> **ArgoCD** handles Continuous Deployment (pull changes from Git, deploy to cluster).  
> This separation follows the **GitOps** model 

---

### Part 1 — Continuous Integration (Jenkins)

Jenkins is responsible for building, testing, and pushing Docker images to the container registry.
                                              
  1. Lint     → helm lint, flake8/ruff on Python     
  2. Test     → pytest for each service              
  3. Build    → docker build for all 3 services      
  4. Scan     → Trivy scans images for CVEs          
  5. Push     → Tag image with Git SHA,              
               push to container registry            
               (ECR / ACR / Docker Hub)              
                                                    
**Key points:**
- Images are tagged with the **Git commit SHA** for full traceability.
- Jenkins **only builds and pushes** — it never directly touches the Kubernetes cluster.
- Failed Trivy scans (critical CVEs) **block the pipeline** and prevent the image from being pushed.

---

### Part 2 — Continuous Deployment (ArgoCD)

ArgoCD is a **GitOps-based** continuous deployment tool. It continuously watches a **separate Git repository** (the manifest repo) and ensures the Kubernetes cluster always matches what's in Git.

> **Key idea:** ArgoCD follows a **pull-based model** — it pulls changes from Git, unlike Jenkins which pushes. ArgoCD never receives commands from Jenkins directly.

---
**breakdown:**

| Step | Who does it | What happens |
|------|-------------|--------------|
| **1** | **Jenkins** | CI is done — image `api-service:abc1234` is now in the container registry |
| **2** | **Ops/Dev team** | Updates `values.yaml` in the **manifest Git repo** with the new image tag (`abc1234`) and pushes the commit |
| **3** | **ArgoCD** | Detects the new commit in the manifest repo (via polling every 3 min or a Git webhook) |
| **4** | **ArgoCD** | Compares the desired state (Git) with the live state (cluster) — finds a difference |
| **5** | **ArgoCD** | Pulls the updated manifests and applies them to the cluster (`kubectl apply` under the hood) |
| **6** | **ArgoCD** | Waits for pods to pass health/readiness checks — confirms deployment is healthy |

---

**Rollback:**

```
Something broke in production?

  1. git revert <bad-commit>    ← revert the manifest change in Git
  2. git push                   ← push to manifest repo
  3. ArgoCD auto-syncs          ← cluster returns to previous working state

No kubectl commands needed. No direct cluster access required.
```

---

## 3. How would you secure the supply chain?

| What | How | File |
|------|-----|------|
| Minimal base image | `python:3.12-slim` (not full `python:3.12`) | All 3 Dockerfiles |
| Multi-stage builds | Dependencies installed in builder stage, only runtime copied to final image | All 3 Dockerfiles |
| Pinned versions | `Flask==3.1.0`, `gunicorn==23.0.0`, `requests==2.32.3` | `requirements.txt` |
| `.dockerignore` | Excludes `.git`, `__pycache__`, `Dockerfile`, `.env` from image | All 3 services |
| Non-root user | `USER 1000:1000` in Dockerfile + `runAsNonRoot: true` in K8s | Dockerfiles + deployments |


 **Trivy in CI** - Scan every image for known vulnerabilities before it's deployed. Fail the build if critical issues are found 


 **Private registry** - Store images in a private container registry (ECR/ACR/GHCR) with access controls  don't pull from public Docker Hub in production 

---

## 4. How would you implement zero downtime deployments?


| Feature | Where | What it does |
|---------|-------|-------------|
| **Rolling update** | All 3 deployments | `maxSurge: 1, maxUnavailable: 0` — new pod starts before old one stops |
| **Readiness probes** | All 3 deployments (`/readyz`) | Traffic only sent to pods that are ready |
| **Liveness probes** | All 3 deployments (`/healthz`) | Unhealthy pods are automatically restarted |
| **Startup probes** | All 3 deployments (`/healthz`) | Gives app time to start before liveness checks begin |
| **PodDisruptionBudgets** | `pdb.yaml` (`minAvailable: 1`) | During node drains/upgrades, at least 1 pod always stays running |
| **HPA** | `api-hpa.yaml` (2–5 replicas) | API always has multiple pods for availability |
---

## 5. What monitoring stack would you recommend and why?

| Component | What it does | How it helps |
|-----------|-------------|-------------|
| **Prometheus** | Collects metrics from the cluster every few seconds | "How much CPU/memory is each pod using?" |
| **Grafana** | Shows metrics as graphs and dashboards | Visual overview of cluster health |
| **Alertmanager** | Sends alerts when things go wrong | "API pod restarted 5 times" → Slack notification |
| **cAdvisor** | Built into every K8s node, tracks container resources | Zero setup — it's already there |
| **kube-state-metrics** | Tracks pod state (running, pending, failed, restarts) | "How many replicas are available right now?" |

---

## 6. How would you design rollback and disaster recovery?

| Feature | How | Why it helps rollback |
|---------|-----|----------------------|
| **Helm chart** | `helm/pyn3k8/` with templated manifests | `helm rollback` reverts to any previous release in seconds |
| **Dev + Prod values** | `values.yaml`, `values-prod.yaml` | Environment-specific configs, easy to switch |
| **Rolling update** | `maxUnavailable: 0` | Failed deploys don't take down existing pods |
| **Readiness probes** | `/readyz` on all services | Broken new pods never receive traffic |
| **Git-tracked manifests** | Everything in `k8s/` and `helm/` | Can always redeploy from any Git commit |



**GitOps (ArgoCD or Flux):**
- The cluster state always matches what's in Git
- To rollback: just `git revert` the bad commit — ArgoCD automatically deploys the previous version

**Cluster-level disaster recovery:**

| Tool | What it does |
|------|-------------|
| **etcd snapshots** | Daily backups of the K8s control plane datastore |
| **Infrastructure as Code** | Cluster defined in Terraform  |
| **Multi-region** | Run in 2+ regions with failover — |


**Key rule:** Test  disaster recovery regularly.

---
