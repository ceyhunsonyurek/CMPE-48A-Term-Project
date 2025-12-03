# Complete Setup Guide - Step by Step

This guide provides all commands needed to set up the entire project from scratch, in the correct order.

**Prerequisites:**
- GCP account with billing enabled
- `gcloud` CLI installed and authenticated
- Docker installed
- `kubectl` installed (comes with gcloud)

---

## 🚀 Quick Start for Collaborators

**If you're joining an existing project (resources already created):**

Your teammate should have already:
- ✅ Created GCS bucket
- ✅ Created Artifact Registry repository
- ✅ Created GKE cluster
- ✅ Set up MySQL VM
- ✅ Deployed Cloud Function

**You only need to:**

1. **Get IAM access** (ask project owner to run):
   ```bash
   gcloud projects add-iam-policy-binding url-shortener-479913 \
     --member="user:YOUR_EMAIL" \
     --role="roles/editor"
   ```

2. **Authenticate and configure:**
   ```bash
   # Login
   gcloud auth login
   
   # Set project
   gcloud config set project url-shortener-479913
   
   # Configure Docker
   gcloud auth configure-docker us-central1-docker.pkg.dev
   
   # Get GKE credentials
   gcloud container clusters get-credentials url-shortener-cluster --region us-east1
   ```

3. **Verify access:**
   ```bash
   # Test GKE
   kubectl get pods
   
   # Test GCS
   gsutil ls gs://url-shortener-assets
   
   # Test Cloud Functions
   gcloud functions list --region us-east1
   ```

**That's it!** You can now work with existing resources. Skip to [Step 10: Common Operations](#step-10-common-operations) for daily tasks.

**For full setup from scratch, continue below:**

---

## Step 1: Initial GCP Setup

### 1.1 Set Project and Enable APIs

```bash
# Set your project
export PROJECT_ID="url-shortener-479913"
gcloud config set project $PROJECT_ID

# Enable required APIs
gcloud services enable container.googleapis.com
gcloud services enable artifactregistry.googleapis.com
gcloud services enable cloudfunctions.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable compute.googleapis.com
gcloud services enable storage-component.googleapis.com
```

### 1.2 Grant Collaborator Access (Optional)

```bash
# Replace COLLABORATOR_EMAIL with your teammate's email
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="user:COLLABORATOR_EMAIL" \
  --role="roles/editor"
```

---

## Step 2: Cloud Storage Setup

### 2.1 Create GCS Bucket

```bash
# Create bucket for static assets and QR codes
gsutil mb -p $PROJECT_ID -c STANDARD -l us-central1 gs://url-shortener-assets

# Make bucket publicly readable (for QR codes)
gsutil iam ch allUsers:objectViewer gs://url-shortener-assets

# Verify bucket
gsutil ls gs://url-shortener-assets
```

---

## Step 3: Artifact Registry Setup

### 3.1 Create Artifact Registry Repository

```bash
# Create Docker repository
gcloud artifacts repositories create url-shortener-repo \
  --repository-format=docker \
  --location=us-central1 \
  --description="Docker repository for URL shortener"

# Configure Docker authentication
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### 3.2 Grant GKE Service Account Access

```bash
# Get project number
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")

# Grant Artifact Registry reader role to GKE service account
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

---

## Step 4: Docker Image Build and Push

### 4.1 Build Docker Image

```bash
# Navigate to project root
cd /path/to/CMPE-48A-Term-Project

# Build image for linux/amd64 platform
docker build --platform linux/amd64 -f docker/Dockerfile -t url-shortener:latest .

# Verify image
docker images | grep url-shortener
```

### 4.2 Tag and Push to Artifact Registry

```bash
# Tag image
docker tag url-shortener:latest \
  us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener:latest

# Push image
docker push us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener:latest

# Verify push
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener
```

---

## Step 5: GKE Cluster Setup

### 5.1 Create GKE Cluster

```bash
# Create cluster
gcloud container clusters create url-shortener-cluster \
  --region us-east1 \
  --num-nodes 1 \
  --machine-type e2-small \
  --enable-autorepair \
  --enable-autoupgrade \
  --release-channel regular

# Get cluster credentials
gcloud container clusters get-credentials url-shortener-cluster \
  --region us-east1

# Verify cluster
kubectl get nodes
kubectl cluster-info
```

### 5.2 Verify Metrics Server (for HPA)

```bash
# Check if metrics server is running
kubectl get deployment metrics-server -n kube-system

# If not running, install it
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
```

---

## Step 6: MySQL VM Setup

### 6.1 Create VM Instance

```bash
# Create MySQL VM
gcloud compute instances create mysql-vm \
  --zone us-east1-b \
  --machine-type e2-small \
  --image-family ubuntu-2204-lts \
  --image-project ubuntu-os-cloud \
  --tags mysql-server \
  --boot-disk-size 20GB

# Get VM internal IP (save this for later)
gcloud compute instances describe mysql-vm \
  --zone us-east1-b \
  --format="get(networkInterfaces[0].networkIP)"
# Output: 10.142.0.15 (example)
```

### 6.2 Create Firewall Rule

```bash
# Allow MySQL access from GKE cluster
gcloud compute firewall-rules create allow-mysql-from-gke \
  --allow tcp:3306 \
  --source-ranges 10.0.0.0/8 \
  --target-tags mysql-server \
  --description "Allow MySQL access from GKE cluster"
```

### 6.3 Setup MySQL on VM

```bash
# Copy setup script to VM
gcloud compute scp vm-scripts/setup-mysql.sh mysql-vm:~/ \
  --zone us-east1-b

# SSH to VM
gcloud compute ssh mysql-vm --zone us-east1-b

# On VM, run setup script
chmod +x setup-mysql.sh
sudo ./setup-mysql.sh

# Verify MySQL is running
sudo systemctl status mysql

# Test database connection
sudo mysql -u appuser -purlshortener2024 urlshortener -e "SHOW TABLES;"

# Exit VM
exit
```

---

## Step 7: Cloud Function Setup

### 7.1 Create Firewall Rule for Cloud Function (Temporary)

```bash
# Allow MySQL access from Cloud Functions (using external IP)
gcloud compute firewall-rules create allow-mysql-from-cloud-functions \
  --allow tcp:3306 \
  --source-ranges 0.0.0.0/0 \
  --target-tags mysql-server \
  --description "Allow MySQL access from Cloud Functions (temporary)"
```

### 7.2 Deploy Cloud Function

```bash
# Navigate to Cloud Function directory
cd cloud-functions/url-redirect

# Get MySQL VM external IP
export MYSQL_EXTERNAL_IP=$(gcloud compute instances describe mysql-vm \
  --zone us-east1-b \
  --format="get(networkInterfaces[0].accessConfigs[0].natIP)")

# Deploy Cloud Function
gcloud functions deploy url-redirect \
  --gen2 \
  --runtime python311 \
  --region us-east1 \
  --source . \
  --entry-point url_redirect \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars DB_HOST=$MYSQL_EXTERNAL_IP,DB_PORT=3306,DB_USER=appuser,DB_PASSWORD=urlshortener2024,DB_DATABASE=urlshortener,SECRET_KEY="YOUR_SECRET_KEY" \
  --memory 256MB \
  --timeout 30s

# Get Cloud Function URL
gcloud functions describe url-redirect \
  --region us-east1 \
  --gen2 \
  --format="value(serviceConfig.uri)"

# Output: https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect
```

### 7.3 Test Cloud Function

```bash
# Test function (replace HASHID with actual hashid)
curl -I https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect/HASHID
```

---

## Step 8: Kubernetes Deployment

### 8.1 Prepare Kubernetes Manifests

**Update `k8s/configmap.yaml`:**
- Set `GCP_PROJECT_ID`: `url-shortener-479913`
- Set `GCS_BUCKET_NAME`: `url-shortener-assets`
- Set `DB_HOST`: MySQL VM internal IP (e.g., `10.142.0.15`)
- Set `CLOUD_FUNCTION_REDIRECT_URL`: Cloud Function URL from Step 7.2

**Update `k8s/secret.yaml`:**
- Set `DB_PASSWORD`: `urlshortener2024`
- Set `SECRET_KEY`: Generate a random key (same as Cloud Function)

### 8.2 Create GCS Service Account Key (for GCS Access)

```bash
# Get compute service account email
export COMPUTE_SA="${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Grant Storage Admin role
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:$COMPUTE_SA" \
  --role="roles/storage.admin"

# Create service account key
gcloud iam service-accounts keys create gcs-key.json \
  --iam-account=$COMPUTE_SA

# Create Kubernetes Secret from key
kubectl create secret generic gcs-key \
  --from-file=key.json=./gcs-key.json

# Clean up local key file (optional, for security)
rm gcs-key.json
```

### 8.3 Apply Kubernetes Manifests

```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Apply Secret
kubectl apply -f k8s/secret.yaml

# Apply Deployment
kubectl apply -f k8s/deployment.yaml

# Apply Service
kubectl apply -f k8s/service.yaml

# Apply HPA
kubectl apply -f k8s/hpa.yaml

# Verify deployment
kubectl get pods
kubectl get services
kubectl get hpa
```

### 8.4 Get External IP

```bash
# Get LoadBalancer external IP
kubectl get service url-shortener-service

# Output will show EXTERNAL-IP (e.g., 35.237.64.253)
```

---

## Step 9: Verification

### 9.1 Verify Application

```bash
# Get external IP
export EXTERNAL_IP=$(kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$EXTERNAL_IP/health

# Test metrics endpoint
curl http://$EXTERNAL_IP/metrics
```

### 9.2 Verify Pods

```bash
# Check pod status
kubectl get pods -l app=url-shortener

# Check pod logs
kubectl logs -l app=url-shortener --tail=50

# Check HPA status
kubectl get hpa url-shortener-hpa
```

### 9.3 Verify Database Connection

```bash
# Test from pod
kubectl exec -it $(kubectl get pod -l app=url-shortener -o jsonpath='{.items[0].metadata.name}') -- \
  python3 -c "import pymysql; conn = pymysql.connect(host='10.142.0.15', user='appuser', password='urlshortener2024', database='urlshortener'); print('Connected!'); conn.close()"
```

### 9.4 Verify GCS Access

```bash
# Test from pod
kubectl exec -it $(kubectl get pod -l app=url-shortener -o jsonpath='{.items[0].metadata.name}') -- \
  python3 -c "from google.cloud import storage; client = storage.Client(); bucket = client.bucket('url-shortener-assets'); print('GCS access OK!')"
```

---

---

## Step 10: Common Operations

**Note:** These operations work for both new setups and collaborators joining existing projects.

### 10.1 Update Application Code

```bash
# After code changes, rebuild and push
docker build --platform linux/amd64 -f docker/Dockerfile -t url-shortener:latest .
docker tag url-shortener:latest \
  us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener:latest
docker push us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener:latest

# Restart deployment to pull new image
kubectl rollout restart deployment url-shortener
kubectl rollout status deployment url-shortener
```

### 10.2 Update Kubernetes Config

```bash
# Update ConfigMap
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment url-shortener

# Update Secret
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment url-shortener
```

### 10.3 View Logs

```bash
# Application logs
kubectl logs -l app=url-shortener --tail=100 -f

# Cloud Function logs
gcloud functions logs read url-redirect --region us-east1 --limit 50
```

### 10.4 Scale Manually

```bash
# Scale deployment manually (HPA will override if thresholds exceeded)
kubectl scale deployment url-shortener --replicas=3

# Check current replicas
kubectl get deployment url-shortener
```

---

## Step 11: Cleanup (When Project Ends)

### 11.1 Delete Kubernetes Resources

```bash
# Delete all Kubernetes resources
kubectl delete -f k8s/hpa.yaml
kubectl delete -f k8s/service.yaml
kubectl delete -f k8s/deployment.yaml
kubectl delete -f k8s/secret.yaml
kubectl delete -f k8s/configmap.yaml
kubectl delete secret gcs-key
```

### 11.2 Delete GKE Cluster

```bash
# Delete cluster
gcloud container clusters delete url-shortener-cluster --region us-east1
```

### 11.3 Delete Cloud Function

```bash
# Delete function
gcloud functions delete url-redirect --region us-east1 --gen2
```

### 11.4 Delete VM

```bash
# Delete MySQL VM
gcloud compute instances delete mysql-vm --zone us-east1-b
```

### 11.5 Delete Firewall Rules

```bash
# Delete firewall rules
gcloud compute firewall-rules delete allow-mysql-from-gke
gcloud compute firewall-rules delete allow-mysql-from-cloud-functions
```

### 11.6 Delete Cloud Storage

```bash
# Delete all objects in bucket
gsutil rm -r gs://url-shortener-assets/*

# Delete bucket
gsutil rb gs://url-shortener-assets
```

### 11.7 Delete Artifact Registry

```bash
# Delete repository
gcloud artifacts repositories delete url-shortener-repo \
  --location us-central1
```

---

## Troubleshooting

### Docker Build Issues

```bash
# Clear Docker cache
docker system prune -a

# Rebuild without cache
docker build --platform linux/amd64 --no-cache -f docker/Dockerfile -t url-shortener:latest .
```

### Image Pull Issues

```bash
# Verify Artifact Registry access
gcloud artifacts docker images list \
  us-central1-docker.pkg.dev/$PROJECT_ID/url-shortener-repo/url-shortener

# Re-grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/artifactregistry.reader"
```

### Pod Startup Issues

```bash
# Check pod events
kubectl describe pod <pod-name>

# Check pod logs
kubectl logs <pod-name>

# Check ConfigMap and Secret
kubectl get configmap url-shortener-config -o yaml
kubectl get secret url-shortener-secrets -o yaml
```

### Database Connection Issues

```bash
# Test from VM
gcloud compute ssh mysql-vm --zone us-east1-b
sudo mysql -u appuser -purlshortener2024 urlshortener

# Test from pod
kubectl exec -it <pod-name> -- bash
# Then test connection manually
```

### GCS Access Issues

```bash
# Verify service account has Storage Admin role
gcloud projects get-iam-policy $PROJECT_ID \
  --flatten="bindings[].members" \
  --filter="bindings.members:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com"

# Re-grant if needed
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member="serviceAccount:${PROJECT_NUMBER}-compute@developer.gserviceaccount.com" \
  --role="roles/storage.admin"
```

---

## Quick Reference

### Environment Variables

```bash
export PROJECT_ID="url-shortener-479913"
export PROJECT_NUMBER=$(gcloud projects describe $PROJECT_ID --format="value(projectNumber)")
export REGION="us-east1"
export ZONE="us-east1-b"
export CLUSTER_NAME="url-shortener-cluster"
export VM_NAME="mysql-vm"
export BUCKET_NAME="url-shortener-assets"
```

### Key Commands

```bash
# Get GKE credentials
gcloud container clusters get-credentials $CLUSTER_NAME --region $REGION

# Get pod names
kubectl get pods -l app=url-shortener

# Restart deployment
kubectl rollout restart deployment url-shortener

# View logs
kubectl logs -l app=url-shortener -f

# Get external IP
kubectl get service url-shortener-service
```

---

## Summary

**Complete setup order:**
1. ✅ GCP project setup and APIs
2. ✅ Cloud Storage bucket
3. ✅ Artifact Registry
4. ✅ Docker image build and push
5. ✅ GKE cluster creation
6. ✅ MySQL VM setup
7. ✅ Cloud Function deployment
8. ✅ Kubernetes deployment
9. ✅ Verification

**Total setup time:** ~2-3 hours

**For collaborator:** Follow Step 1.2 to grant access, then they can run steps 4-10.

