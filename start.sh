# Install Kubectl
LATEST=$(curl -sL https://dl.k8s.io/release/stable.txt)   # e.g. v1.33.1

curl -LO "https://dl.k8s.io/release/${LATEST}/bin/linux/amd64/kubectl"
curl -LO "https://dl.k8s.io/release/${LATEST}/bin/linux/amd64/kubectl.sha256"

echo "$(<kubectl.sha256)  kubectl" | sha256sum --check    # should print “OK”

sudo install -m 0755 kubectl /usr/local/bin/kubectl
kubectl version --client

# Install Docker
sudo apt-get update
sudo apt-get install -y \
    ca-certificates curl gnupg lsb-release

# 3) Add Docker’s official GPG key
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | \
  sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

# 4) Add the Docker apt repository
echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
  https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list >/dev/null

# 5) Install Docker Engine, CLI & containerd
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin


# Container toolkit
# add nvidia-container-toolkit repo to apt sources
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg \
&& curl -s -L https://nvidia.github.io/libnvidia-container/stable/deb/nvidia-container-toolkit.list | \
sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# update apt content
sudo apt update

# install container toolkit
sudo apt install -y nvidia-container-toolkit



# Install minikube
curl -Lo minikube https://storage.googleapis.com/minikube/releases/latest/minikube-linux-amd64
sudo install -m 0755 minikube /usr/local/bin/minikube
rm minikube
# Download & run the official install script
curl -fsSL https://baltocdn.com/helm/signing.asc | sudo gpg --dearmor -o /etc/apt/keyrings/helm.gpg
sudo chmod a+r /etc/apt/keyrings/helm.gpg



# 2) Add the Helm apt repository
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
helm version


helm repo add nvidia https://nvidia.github.io/gpu-operator
helm repo update

# Install into its own namespace
helm install gpu-operator nvidia/gpu-operator \
  --namespace gpu-operator --create-namespace \
  --set driver.enabled=true  \
  --set toolkit.enabled=false \
  --wait