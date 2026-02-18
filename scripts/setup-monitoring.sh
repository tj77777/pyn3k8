#!/usr/bin/env bash
set -euo pipefail

echo "Installing kube-prometheus-stack for pod-level monitoring..."
echo ""

# Add Helm repo
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo update

# Install kube-prometheus-stack
helm install prometheus prometheus-community/kube-prometheus-stack \
  -n monitoring --create-namespace

echo ""
echo "Monitoring stack installed successfully."
echo ""
echo "Verify pods:"
echo "  kubectl get pods -n monitoring"
echo ""
echo "Access Prometheus UI:"
echo "  kubectl port-forward -n monitoring svc/prometheus-kube-prometheus-prometheus 9090:9090"
echo "  Open http://localhost:9090"
echo ""
echo "Access Grafana:"
echo "  kubectl port-forward -n monitoring svc/prometheus-grafana 3000:80"
echo "  Open http://localhost:3000  (login: admin / prom-operator)"
echo ""
echo "Pod metrics queries for pyn3k8 namespace:"
echo "  CPU:     sum(rate(container_cpu_usage_seconds_total{namespace=\"pyn3k8\"}[5m])) by (pod)"
echo "  Memory:  sum(container_memory_working_set_bytes{namespace=\"pyn3k8\"}) by (pod)"
echo "  Network: sum(rate(container_network_receive_bytes_total{namespace=\"pyn3k8\"}[5m])) by (pod)"
