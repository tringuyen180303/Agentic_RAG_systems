# start with docker-compose
docker-compose up -d

# start with kubect
helm repo add langfuse https://langfuse.github.io/langfuse-k8s
helm repo update
helm install langfuse langfuse/langfuse -f values.yaml

# Get the public and secret key of langfuse
kubectl port-forward svc/langfuse-web 3000:3000 -n observable

Go in localhost:3000 to get public key and get public key and secretkey