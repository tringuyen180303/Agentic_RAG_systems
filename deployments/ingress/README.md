<!-- helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx --create-namespace

minikube tunnel to create loadbalancer

create TLS
cat > san.cnf <<EOF
[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = v3_req

[dn]
C  = US
ST = State
L  = City
O  = Observability
CN = grafana.example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = grafana.example.com
DNS.2 = prometheus.example.com
EOF


then with openssl to generate key + crt

openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout observability.key \
  -out observability.crt \
  -config san.cnf \
  -extensions v3_req

## apply the secret
kubectl create secret tls observability-tls \
  --namespace=monitoring \
  --key=observability.key \
  --cert=observability.crt

## apply
 kubectl apply -f deployments/ingress/monitoring.yaml 

 sudo sh -c 'cat >> /etc/hosts <<EOF
127.0.0.1 grafana.example.com
127.0.0.1 prometheus.example.com
EOF' -->

# Observability Ingress Setup Guide for Minikube

## Table of Contents
1. [Prerequisites](#prerequisites)  
2. [Add & Update the Ingress‑NGINX Helm Repo](#add-update-the-ingress-nginx-helm-repo)  
3. [Install the Ingress‑NGINX Controller](#install-the-ingress-nginx-controller)  
4. [Create a LoadBalancer via Minikube Tunnel](#create-a-loadbalancer-via-minikube-tunnel)  
5. [Generate a TLS Certificate with SANs](#generate-a-tls-certificate-with-sans)  
6. [Create the Kubernetes TLS Secret](#create-the-kubernetes-tls-secret)  
7. [Deploy Your Ingress Resources](#deploy-your-ingress-resources)  
8. [Map Hostnames Locally](#map-hostnames-locally)  

---

## Prerequisites

- **Minikube** installed and running  
- **kubectl** configured to talk to your Minikube cluster  
- **Helm 3** installed  
- **OpenSSL** available on your local machine  

---

## Add & Update the Ingress‑NGINX Helm Repo

```bash
helm repo add ingress-nginx https://kubernetes.github.io/ingress-nginx
helm repo update
```

## Install the Ingress-NGINX Controller
```
helm install ingress-nginx ingress-nginx/ingress-nginx \
  --namespace ingress-nginx \
  --create-namespace
```

## Create a LoadBalancer via Minikube Tunnel
```
minikube tunnel
```

## Generate TLS Certificate with SANS
### create san.cnf

"""[req]
default_bits       = 2048
prompt             = no
default_md         = sha256
distinguished_name = dn
req_extensions     = v3_req

[dn]
C  = US
ST = State
L  = City
O  = Observability
CN = grafana.example.com

[v3_req]
subjectAltName = @alt_names

[alt_names]
DNS.1 = grafana.example.com
DNS.2 = prometheus.example.com
"""

### Generate key and cert
```
openssl req -x509 -nodes -days 365 \
  -newkey rsa:2048 \
  -keyout observability.key \
  -out observability.crt \
  -config san.cnf \
  -extensions v3_req
```

## Create Kubernetes TSL Secret
```
kubectl create secret tls observability-tls \
  --namespace=monitoring \
  --key=observability.key \
  --cert=observability.crt
```

## Deploy Ingress Resources
```
kubectl apply -f deployments/ingress/monitoring.yaml
```


## Map Hostnames Locally
```
sudo sh -c 'cat >> /etc/hosts <<EOF
127.0.0.1 grafana.example.com
127.0.0.1 prometheus.example.com
EOF'
```
