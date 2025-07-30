#!/bin/bash

# RegulensAI Advanced Monitoring Deployment Script
# Deploys comprehensive monitoring stack with Grafana dashboards and alerting

set -e

# Configuration
NAMESPACE="regulensai-monitoring"
GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-admin123}"
SLACK_WEBHOOK_URL="${SLACK_WEBHOOK_URL:-}"
SMTP_HOST="${SMTP_HOST:-smtp.gmail.com}"
SMTP_PORT="${SMTP_PORT:-587}"
SMTP_USERNAME="${SMTP_USERNAME:-alerts@regulens.ai}"
SMTP_PASSWORD="${SMTP_PASSWORD:-}"

echo "🚀 Deploying RegulensAI Advanced Monitoring Stack"

# Create namespace
echo "📁 Creating monitoring namespace..."
kubectl create namespace $NAMESPACE --dry-run=client -o yaml | kubectl apply -f -

# Add Helm repositories
echo "📦 Adding Helm repositories..."
helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update

# Deploy Prometheus with custom configuration
echo "📊 Deploying Prometheus..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: prometheus-config
  namespace: $NAMESPACE
data:
  prometheus.yml: |
    global:
      scrape_interval: 15s
      evaluation_interval: 15s
    
    rule_files:
      - "/etc/prometheus/rules/*.yml"
    
    alerting:
      alertmanagers:
        - static_configs:
            - targets:
              - alertmanager:9093
    
    scrape_configs:
      - job_name: 'prometheus'
        static_configs:
          - targets: ['localhost:9090']
      
      - job_name: 'regulensai-api'
        static_configs:
          - targets: ['regulensai-api:8000']
        metrics_path: '/api/v1/operations/metrics/prometheus'
        scrape_interval: 30s
      
      - job_name: 'node-exporter'
        static_configs:
          - targets: ['node-exporter:9100']
      
      - job_name: 'postgres-exporter'
        static_configs:
          - targets: ['postgres-exporter:9187']
      
      - job_name: 'redis-exporter'
        static_configs:
          - targets: ['redis-exporter:9121']
EOF

# Deploy AlertManager with RegulensAI configuration
echo "🚨 Deploying AlertManager..."
kubectl create configmap alertmanager-config \
  --from-file=monitoring/alertmanager/alertmanager.yaml \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy Prometheus alert rules
echo "📋 Deploying alert rules..."
kubectl create configmap prometheus-rules \
  --from-file=monitoring/alerts/ \
  --namespace=$NAMESPACE \
  --dry-run=client -o yaml | kubectl apply -f -

# Deploy Prometheus stack
helm upgrade --install prometheus prometheus-community/kube-prometheus-stack \
  --namespace $NAMESPACE \
  --set prometheus.prometheusSpec.configMaps[0]=prometheus-config \
  --set prometheus.prometheusSpec.ruleSelector.matchLabels.app=prometheus \
  --set alertmanager.config.global.smtp_smarthost="$SMTP_HOST:$SMTP_PORT" \
  --set alertmanager.config.global.smtp_from="$SMTP_USERNAME" \
  --set alertmanager.config.global.smtp_auth_username="$SMTP_USERNAME" \
  --set alertmanager.config.global.smtp_auth_password="$SMTP_PASSWORD" \
  --set grafana.adminPassword="$GRAFANA_ADMIN_PASSWORD" \
  --set grafana.persistence.enabled=true \
  --set grafana.persistence.size=10Gi

# Wait for Prometheus to be ready
echo "⏳ Waiting for Prometheus to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=prometheus --namespace=$NAMESPACE --timeout=300s

# Deploy Grafana dashboards
echo "📈 Deploying Grafana dashboards..."

# Create dashboard configmaps
for dashboard in monitoring/dashboards/*.json; do
  dashboard_name=$(basename "$dashboard" .json)
  kubectl create configmap "grafana-dashboard-$dashboard_name" \
    --from-file="$dashboard" \
    --namespace=$NAMESPACE \
    --dry-run=client -o yaml | kubectl apply -f -
done

# Configure Grafana dashboard provisioning
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-dashboard-provider
  namespace: $NAMESPACE
data:
  dashboards.yaml: |
    apiVersion: 1
    providers:
      - name: 'RegulensAI Dashboards'
        orgId: 1
        folder: 'RegulensAI'
        type: file
        disableDeletion: false
        updateIntervalSeconds: 10
        allowUiUpdates: true
        options:
          path: /var/lib/grafana/dashboards
EOF

# Deploy additional exporters
echo "🔧 Deploying additional exporters..."

# PostgreSQL Exporter
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: postgres-exporter
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: postgres-exporter
  template:
    metadata:
      labels:
        app: postgres-exporter
    spec:
      containers:
      - name: postgres-exporter
        image: prometheuscommunity/postgres-exporter:latest
        ports:
        - containerPort: 9187
        env:
        - name: DATA_SOURCE_NAME
          value: "postgresql://\${POSTGRES_USER}:\${POSTGRES_PASSWORD}@\${POSTGRES_HOST}:5432/\${POSTGRES_DB}?sslmode=disable"
        envFrom:
        - secretRef:
            name: postgres-credentials
---
apiVersion: v1
kind: Service
metadata:
  name: postgres-exporter
  namespace: $NAMESPACE
spec:
  selector:
    app: postgres-exporter
  ports:
  - port: 9187
    targetPort: 9187
EOF

# Redis Exporter
cat <<EOF | kubectl apply -f -
apiVersion: apps/v1
kind: Deployment
metadata:
  name: redis-exporter
  namespace: $NAMESPACE
spec:
  replicas: 1
  selector:
    matchLabels:
      app: redis-exporter
  template:
    metadata:
      labels:
        app: redis-exporter
    spec:
      containers:
      - name: redis-exporter
        image: oliver006/redis_exporter:latest
        ports:
        - containerPort: 9121
        env:
        - name: REDIS_ADDR
          value: "redis://\${REDIS_HOST}:6379"
        - name: REDIS_PASSWORD
          valueFrom:
            secretKeyRef:
              name: redis-credentials
              key: password
---
apiVersion: v1
kind: Service
metadata:
  name: redis-exporter
  namespace: $NAMESPACE
spec:
  selector:
    app: redis-exporter
  ports:
  - port: 9121
    targetPort: 9121
EOF

# Create ingress for Grafana
echo "🌐 Creating Grafana ingress..."
cat <<EOF | kubectl apply -f -
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: grafana-ingress
  namespace: $NAMESPACE
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
    nginx.ingress.kubernetes.io/ssl-redirect: "true"
spec:
  tls:
  - hosts:
    - grafana.regulens.ai
    secretName: grafana-tls
  rules:
  - host: grafana.regulens.ai
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: prometheus-grafana
            port:
              number: 80
EOF

# Configure Grafana data sources
echo "🔗 Configuring Grafana data sources..."
cat <<EOF | kubectl apply -f -
apiVersion: v1
kind: ConfigMap
metadata:
  name: grafana-datasources
  namespace: $NAMESPACE
data:
  datasources.yaml: |
    apiVersion: 1
    datasources:
      - name: Prometheus
        type: prometheus
        access: proxy
        url: http://prometheus-server:80
        isDefault: true
        editable: true
      - name: AlertManager
        type: alertmanager
        access: proxy
        url: http://alertmanager:9093
        editable: true
EOF

# Wait for all components to be ready
echo "⏳ Waiting for all monitoring components to be ready..."
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=grafana --namespace=$NAMESPACE --timeout=300s
kubectl wait --for=condition=ready pod -l app.kubernetes.io/name=alertmanager --namespace=$NAMESPACE --timeout=300s

# Get access information
echo "✅ Monitoring stack deployed successfully!"
echo ""
echo "📊 Access Information:"
echo "===================="

# Get Grafana URL
GRAFANA_URL=$(kubectl get ingress grafana-ingress -n $NAMESPACE -o jsonpath='{.spec.rules[0].host}' 2>/dev/null || echo "localhost:3000")
echo "🎯 Grafana: https://$GRAFANA_URL"
echo "   Username: admin"
echo "   Password: $GRAFANA_ADMIN_PASSWORD"

# Get Prometheus URL
echo "📈 Prometheus: http://localhost:9090 (port-forward required)"
echo "🚨 AlertManager: http://localhost:9093 (port-forward required)"

echo ""
echo "🔧 Port Forward Commands:"
echo "========================"
echo "kubectl port-forward -n $NAMESPACE svc/prometheus-server 9090:80"
echo "kubectl port-forward -n $NAMESPACE svc/alertmanager 9093:9093"
echo "kubectl port-forward -n $NAMESPACE svc/prometheus-grafana 3000:80"

echo ""
echo "📋 Available Dashboards:"
echo "========================"
echo "• Executive Overview - Business metrics and system health"
echo "• Technical Operations - Infrastructure and performance"
echo "• RegulensAI Application - Application-specific metrics"
echo "• Alerting Overview - Real-time alerts and incidents"

echo ""
echo "🎉 Monitoring deployment complete!"
echo "   Check the Operations Center for integrated monitoring access."
