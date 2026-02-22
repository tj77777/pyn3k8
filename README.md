# pyn3k8 - Microservices on Kubernetes

A microservices application deployed on Kubernetes (Minikube), Helm packaging, and operational best practices.

---

## Repo Structure

```
pyn3k8/
├── services/          # Application source code & Dockerfiles
│   ├── ui/            # Flask web UI (port 5000)
│   ├── api/           # Flask REST API (port 8080)
│   └── worker/        # Background worker service (port 9090)
├── k8/                # Raw Kubernetes manifests
├── helm/pyn3k8/       # Helm chart for templated deploys
├── gitops/            # ArgoCD Application CRDs for GitOps
├── docs/              # Guides & production discussion
└── scripts/           # Utility scripts (monitoring, ArgoCD setup)
```

---

## Folder Details

### [`services/`](services/README.md)
**Part A — Secure Container Build.** Contains the three Python microservices (UI, API, Worker), each with its own Dockerfile and requirements. Covers multi-stage builds, minimal base images, non-root execution, and secret handling.

### [`k8/`](k8/README.md)
**Part B — Kubernetes Deployment.** Raw YAML manifests for deploying all three services to a `pyn3k8` namespace. Includes namespace with restricted Pod Security Standards, deployments, services, ingress, HPA, PDBs, ConfigMaps, Secrets, and NetworkPolicies.

### [`helm/pyn3k8/`](helm/pyn3k8/README.md)
**Part C — Helm Chart.** A Helm chart that templates all the K8s resources above. Supports dev (`values.yaml`) and production (`values-prod.yaml`) configurations with one command.

### [`docs/`](docs/)
Supplementary documentation:

- [Deployment Guide](docs/deployment-guide.md) — Step-by-step instructions for setting up Minikube, building images, and deploying the app.
- [Production Readiness](docs/production-readiness.md) — Part D discussion covering secrets management, CI/CD, supply chain security, observability, and scaling.

### [`gitops/`](gitops/README.md)
**Bonus 5 — ArgoCD GitOps.** ArgoCD Application CRDs that point at the Helm chart for automated, self-healing deployments. Push to Git → ArgoCD syncs to the cluster.

### [`scripts/`](scripts/)
Helper scripts such as `setup-monitoring.sh` for bootstrapping Prometheus/Grafana and `setup-argocd.sh` for installing ArgoCD.