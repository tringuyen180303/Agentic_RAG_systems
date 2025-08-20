



### Running Minikube is not creating a LoadBalancer
minikube service grafana --url -n monitoring
# → http://192.168.49.2:30511  (for example)

# Prometheus
minikube service prometheus-server --url -n monitoring

## Port forward
kubectl -n monitoring port-forward svc/grafana 3000:80
# now browse http://localhost:3000
# Prometheus listens on port 80 in‑cluster
kubectl -n monitoring port-forward svc/prometheus-server 9090:80

### Add in connection for server URL
http://prometheus-server.monitoring.svc.cluster.local:80




##### Latest

helm repo add prometheus-community https://prometheus-community.github.io/helm-charts
helm repo add grafana https://grafana.github.io/helm-charts
helm repo update
