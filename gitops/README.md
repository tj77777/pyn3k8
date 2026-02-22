# ArgoCD GitOps Deployment



## Prerequisites

| Tool | Purpose |
|------|---------|
| Minikube | Local Kubernetes cluster (running) |
| kubectl | Kubernetes CLI |
| ArgoCD CLI | (Optional) Command-line management — `brew install argocd` |

---

## Quick Start

### 1. Install ArgoCD

```bash
chmod +x scripts/setup-argocd.sh
./scripts/setup-argocd.sh
```

### 2. Update the Git repo URL

Edit both Application files and replace the placeholder `repoURL`:

```bash
# Replace <org> with your GitHub org/user
sed -i '' 's|https://github.com/<org>/pyn3k8.git|https://github.com/YOUR_USER/pyn3k8.git|' \
  gitops/argocd-application.yaml \
  gitops/argocd-application-prod.yaml
```

### 3. Apply the Application CRDs

```bash
# Dev environment
kubectl apply -f gitops/argocd-application.yaml

# Production environment (when ready)
kubectl apply -f gitops/argocd-application-prod.yaml
```

### 4. Access ArgoCD UI

```bash
kubectl port-forward svc/argocd-server -n argocd 8443:443
```

Open https://localhost:8443 — login with `admin` and the password from the install script.

---

## Application Definitions

### Dev (`argocd-application.yaml`)

| Field | Value |
|-------|-------|
| Name | `pyn3k8-dev` |
| Source | `helm/pyn3k8` with `values.yaml` |
| Destination | `https://kubernetes.default.svc` / `pyn3k8` |
| Sync | Automated, prune, self-heal |

### Production (`argocd-application-prod.yaml`)

| Field | Value |
|-------|-------|
| Name | `pyn3k8-prod` |
| Source | `helm/pyn3k8` with `values.yaml` + `values-prod.yaml` |
| Destination | `https://kubernetes.default.svc` / `pyn3k8` |
| Sync | Automated, prune, self-heal |

---

## GitOps Workflow

### Deploy a change

```bash
# 1. Edit values or templates
vim helm/pyn3k8/values.yaml

# 2. Commit and push
git add -A && git commit -m "bump api replicas to 3" && git push

# 3. ArgoCD detects the change and syncs automatically
#    (default poll interval: 3 minutes, or configure a webhook for instant sync)
```

### Check sync status

```bash
# CLI
argocd app get pyn3k8-dev
argocd app get pyn3k8-prod

# Or via kubectl
kubectl get applications -n argocd
```

### Force an immediate sync

```bash
argocd app sync pyn3k8-dev
```

### Rollback

```bash
# List sync history
argocd app history pyn3k8-dev

# Rollback to a previous revision
argocd app rollback pyn3k8-dev <HISTORY_ID>
```

> **Note:** With automated sync enabled, ArgoCD will re-sync to HEAD after a rollback. To keep a rollback permanent, revert the commit in Git.

---

## Uninstall

```bash
# Remove Applications
kubectl delete -f gitops/

# Remove ArgoCD
kubectl delete -n argocd -f \
  "https://raw.githubusercontent.com/argoproj/argo-cd/v2.14.3/manifests/install.yaml"
kubectl delete namespace argocd
```

---

## Troubleshooting

| Symptom | Fix |
|---------|-----|
| App stuck on `Unknown` | Check `argocd app get <name>` — likely a repo URL or auth issue |
| `ComparisonError` | Helm chart has a syntax error — run `helm lint helm/pyn3k8/` locally |
| Sync fails with `namespace not found` | `CreateNamespace=true` is set in syncOptions — check ArgoCD RBAC |
| Resources not pruned | Ensure `prune: true` is in the Application syncPolicy |
| Slow sync detection | Default poll is 3 min. Configure a [GitHub webhook](https://argo-cd.readthedocs.io/en/stable/operator-manual/webhook/) for instant sync |
