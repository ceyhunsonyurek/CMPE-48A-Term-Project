# Setup Instructions

This guide provides step-by-step instructions to replicate the URL Shortener application setup on Google Cloud Platform.

## Prerequisites

Before setting up the application, ensure you have:

### GCP Account & Project
- Google Cloud Platform account with billing enabled
- A GCP project created
- Required APIs enabled:
  - Kubernetes Engine API
  - Cloud Functions API
  - Cloud Storage API
  - Compute Engine API
  - Artifact Registry API

### Local Tools
- **gcloud CLI**: [Installation Guide](https://cloud.google.com/sdk/docs/install)
- **kubectl**: [Installation Guide](https://kubernetes.io/docs/tasks/tools/)
- **Docker**: [Installation Guide](https://docs.docker.com/get-docker/)
- **Python 3.9+**: [Download Python](https://www.python.org/downloads/)

## Setup Instructions

### 1. Clone Repository

```bash
git clone <repository-url>
cd CMPE-48A-Term-Project
```

### 2. Database Setup

#### 2.1 Create MySQL VM Instance

```bash
gcloud compute instances create mysql-vm \
  --zone=us-east1-b \
  --machine-type=e2-medium \
  --image-family=ubuntu-2004-lts \
  --image-project=ubuntu-os-cloud \
  --tags=mysql-server \
  --boot-disk-size=20GB
```

#### 2.2 Create Firewall Rule

Allow MySQL access from GKE cluster:

```bash
gcloud compute firewall-rules create allow-mysql-from-gke \
  --allow tcp:3306 \
  --source-ranges 10.0.0.0/8 \
  --target-tags mysql-server \
  --description "Allow MySQL access from GKE cluster"
```

#### 2.3 Setup MySQL Database

SSH to the VM and run the setup script:

```bash
# Copy setup script to VM
gcloud compute scp vm-scripts/setup-mysql.sh mysql-vm:~/ --zone=us-east1-b

# SSH to VM
gcloud compute ssh mysql-vm --zone=us-east1-b

# Make script executable and run
chmod +x setup-mysql.sh
./setup-mysql.sh
```

The script will:
- Install MySQL server
- Create database and user
- Configure remote access
- Create database tables with indexes
- Add performance optimization indexes

#### 2.4 Get MySQL VM Internal IP

Save this IP for later use in Kubernetes configuration:
```bash
gcloud compute instances describe mysql-vm --zone=us-east1-b --format="get(networkInterfaces[0].networkIP)"
```

### 3. GCS Bucket Setup

#### 3.1 Create GCS Bucket

```bash
gsutil mb -p your-gcp-project-id -l us-east1 gs://your-bucket-name
```

#### 3.2 Configure IAM Permissions

Ensure your GKE service account has access to the bucket:

```bash
# Get GKE service account
GKE_SA=$(gcloud iam service-accounts list --filter="Compute Engine default service account" --format="value(email)")

# Grant Storage Object Admin role
gsutil iam ch serviceAccount:$GKE_SA:roles/storage.objectAdmin gs://your-bucket-name
```

### 4. Build Docker Image

#### 4.1 Create Artifact Registry Repository

```bash
gcloud artifacts repositories create url-shortener-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="URL Shortener Docker images"
```

#### 4.2 Build and Push Image

```bash
# Configure Docker for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev

# Build image
docker build -f docker/Dockerfile -t url-shortener:latest .

# Tag for Artifact Registry
docker tag url-shortener:latest \
  us-central1-docker.pkg.dev/your-project-id/url-shortener-repo/url-shortener:latest

# Push image
docker push us-central1-docker.pkg.dev/your-project-id/url-shortener-repo/url-shortener:latest
```

### 5. Deploy to Kubernetes

#### 5.1 Create GKE Cluster

```bash
gcloud container clusters create url-shortener-cluster \
  --zone=us-east1-b \
  --num-nodes=2 \
  --machine-type=e2-medium \
  --enable-autorepair \
  --enable-autoupgrade
```

#### 5.2 Configure kubectl

```bash
gcloud container clusters get-credentials url-shortener-cluster --zone=us-east1-b
```

#### 5.3 Update Kubernetes Manifests

**Edit `k8s/configmap.yaml`:**
- Set `GCP_PROJECT_ID` to your GCP project ID
- Set `GCS_BUCKET_NAME` to your bucket name
- Set `DB_HOST` to MySQL VM internal IP (from step 2.5)
- Set `CLOUD_FUNCTION_REDIRECT_URL` to your Cloud Function URL (after step 6.2)

**Edit `k8s/secret.yaml`:**
- Set `DB_PASSWORD` to your MySQL password
- Set `SECRET_KEY` to a secure random string (generate with: `python3 -c "import secrets; print(secrets.token_hex(32))"`)

**Important**: Base64 encode values for secrets:
```bash
echo -n "your-password" | base64
```

#### 5.4 Apply Kubernetes Manifests

```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Apply Secrets
kubectl apply -f k8s/secret.yaml

# Apply Deployment
kubectl apply -f k8s/deployment.yaml

# Apply Service
kubectl apply -f k8s/service.yaml

# Apply HPA (optional, for auto-scaling)
kubectl apply -f k8s/hpa.yaml
```

#### 5.5 Verify Deployment

```bash
# Check pods
kubectl get pods -l app=url-shortener

# Check service
kubectl get service url-shortener-service

# Get external IP
kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

# Test health endpoint
EXTERNAL_IP=$(kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
curl http://$EXTERNAL_IP/health
```

### 6. Deploy Cloud Function

#### 6.1 Create Firewall Rule for Cloud Function

Allow MySQL access from Cloud Functions:

```bash
gcloud compute firewall-rules create allow-mysql-from-cloud-functions \
  --allow tcp:3306 \
  --source-ranges 0.0.0.0/0 \
  --target-tags mysql-server \
  --description "Allow MySQL access from Cloud Functions"
```

#### 6.2 Deploy Function

```bash
cd cloud-functions/url-redirect

gcloud functions deploy url-redirect \
  --gen2 \
  --runtime python311 \
  --region us-east1 \
  --source . \
  --entry-point url_redirect \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars DB_HOST=your_mysql_vm_ip,DB_PORT=3306,DB_USER=appuser,DB_PASSWORD=your_password,DB_DATABASE=urlshortener,SECRET_KEY=your_secret_key \
  --memory 256MB \
  --timeout 10s
```

#### 6.3 Get Function URL

```bash
FUNCTION_URL=$(gcloud functions describe url-redirect --gen2 --region us-east1 --format="value(serviceConfig.uri)")
echo $FUNCTION_URL
```

**Important**: Update `k8s/configmap.yaml` with this URL in `CLOUD_FUNCTION_REDIRECT_URL`, then reapply:
```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment url-shortener
```
