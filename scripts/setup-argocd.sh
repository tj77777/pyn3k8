#!/usr/bin/env bash
set -euo pipefail

ARGOCD_VERSION="v2.14.3"
ARGOCD_NS="argocd"

echo "=== Installing ArgoCD ${ARGOCD_VERSION} ==="
echo ""

# Create namespace
kubectl create namespace "${ARGOCD_NS}" --dry-run=client -o yaml | kubectl apply -f -

# Install ArgoCD from upstream manifests (non-HA, suitable for Minikube)
echo "Applying ArgoCD manifests..."
kubectl apply -n "${ARGOCD_NS}" \
  -f "https://raw.githubusercontent.com/argoproj/argo-cd/${ARGOCD_VERSION}/manifests/install.yaml"

echo ""
echo "Waiting for ArgoCD server to be ready..."
kubectl rollout status deployment/argocd-server -n "${ARGOCD_NS}" --timeout=300s

echo ""
echo "=== ArgoCD installed successfully ==="
echo ""

# Retrieve initial admin password
ADMIN_PASS=$(kubectl -n "${ARGOCD_NS}" get secret argocd-initial-admin-secret \
  -o jsonpath="{.data.password}" | base64 -d)

echo "ArgoCD UI access:"
echo "  kubectl port-forward svc/argocd-server -n ${ARGOCD_NS} 8443:443"
echo "  Open https://localhost:8443"
echo ""
echo "  Username: admin"
echo "  Password: ${ADMIN_PASS}"
echo ""
echo "CLI login (install argocd CLI first: brew install argocd):"
echo "  argocd login localhost:8443 --insecure --username admin --password '${ADMIN_PASS}'"
echo ""
echo "Next steps:"
echo "  1. Change the admin password:  argocd account update-password"
echo "  2. Apply Application CRDs:     kubectl apply -f gitops/"
echo "  3. Monitor sync status:        argocd app list"
