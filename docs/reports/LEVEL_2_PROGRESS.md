# Level 2: Containerization and Kubernetes - Progress Report

## Overview
**Duration:** 3-5 Days  
**Difficulty:** Medium  
**Status:** ✅ **COMPLETED**

---

## 2.1 Docker Containerization

### What Was Needed
- Create Dockerfile for Flask application
- Configure production-ready WSGI server (gunicorn)
- Add health check endpoint
- Optimize image size and security

### What Was Done
- Created `docker/Dockerfile`:
  - Base image: `python:3.9-slim`
  - Installed system dependencies (gcc for pymysql)
  - Installed Python dependencies
  - Created non-root user (`appuser`) for security
  - Configured gunicorn with 2 workers
  - Added HEALTHCHECK command
- Created `.dockerignore` to optimize build context
- Added `/health` endpoint to `app.py` for Kubernetes health checks
- Updated `requirements.txt` with `gunicorn`

### Issues Encountered
- Initial Docker build failed due to Gradio client `input()` call
- Container couldn't start in non-interactive mode

### Solution
- Modified `app.py` to check if running in container (`os.isatty(0)`)
- Only prompt for input if running interactively
- In containers, use environment variable `GRADIO_ENDPOINT` (later removed)

---

## 2.2 GCP Container Registry Setup

### What Was Needed
- Set up Artifact Registry for Docker images
- Configure Docker authentication for GCP
- Push Docker image to registry

### What Was Done
- Created Artifact Registry repository: `url-shortener-repo` (us-central1)
- Configured Docker authentication: `gcloud auth configure-docker`
- Tagged and pushed image: `us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo/url-shortener:latest`
- Verified image push and tested pull

### Issues Encountered
- None - straightforward setup

### Solution
- N/A

---

## 2.3 GKE Cluster Creation

### What Was Needed
- Create GKE cluster in GCP
- Configure kubectl connection
- Verify cluster is operational

### What Was Done
- Created cluster: `url-shortener-cluster` (us-east1 region)
- Configuration:
  - Machine type: `e2-small` (cost-effective)
  - Requested nodes: 1
  - Region: us-east1 (due to quota limits in us-central1)
  - Auto-repair and auto-upgrade enabled
- Configured kubectl: `gcloud container clusters get-credentials`
- Verified cluster: 3 nodes running (GKE auto-scaled for system pods)

### Issues Encountered
- **Quota Error:** `IN_USE_ADDRESSES` limit exceeded in us-central1 (limit: 4)
- Attempted quota increase but free trial account not eligible
- Same quota issue in us-east1 initially

### Solution
- Switched to us-east1 region (similar pricing)
- Used `--num-nodes=1` (GKE created 3 nodes across zones for HA)
- Region-based cluster provides high availability across zones

**Note:** Free trial accounts have strict quota limits. us-east1 worked with 1 node request.

---

## 2.4 Kubernetes Deployment Manifests

### What Was Needed
- Create Kubernetes Deployment manifest
- Create Service manifest (LoadBalancer)
- Create ConfigMap for non-sensitive configuration
- Create Secret for sensitive data
- Deploy application to GKE

### What Was Done
- Created `k8s/deployment.yaml`:
  - 2 replicas
  - Resource requests/limits (CPU: 200m-500m, Memory: 256Mi-512Mi)
  - Liveness and readiness probes (`/health` endpoint)
  - Environment variables from ConfigMap and Secret
- Created `k8s/service.yaml`:
  - LoadBalancer type for external access
  - Session affinity (ClientIP) for 3 hours
- Created `k8s/configmap.yaml`:
  - GCP project ID, GCS bucket name
  - Database host (MySQL VM IP), port, database name
- Created `k8s/secret.yaml`:
  - Database credentials
  - Flask secret key (randomly generated)
- Created GCS bucket: `url-shortener-assets`
- Applied all manifests to cluster

### Issues Encountered
- **Image Pull Error:** "no match for platform in manifest"
  - Image was built for wrong platform (ARM vs AMD64)
- **IAM Permission:** GKE nodes couldn't pull from Artifact Registry
  - Missing `roles/artifactregistry.reader` permission

### Solution
- Rebuilt Docker image with `--platform linux/amd64` flag
- Granted Artifact Registry reader role to GKE service account:
  ```bash
  gcloud projects add-iam-policy-binding \
    --member="serviceAccount:PROJECT_NUMBER-compute@developer.gserviceaccount.com" \
    --role="roles/artifactregistry.reader"
  ```

### Deployment Results
- ✅ 2 pods running and ready
- ✅ LoadBalancer service with external IP: `35.237.64.253`
- ✅ Health check endpoint responding
- ✅ Application accessible from internet

---

## Summary

**Completed Tasks:**
- ✅ Docker containerization with production-ready setup
- ✅ Artifact Registry configured and image pushed
- ✅ GKE cluster created and configured
- ✅ Kubernetes deployment manifests created and deployed
- ✅ Application running on Kubernetes

**Key Achievements:**
- Production-ready containerized application
- Scalable Kubernetes deployment
- External access via LoadBalancer
- Health checks configured for reliability

---

## 2.5 Horizontal Pod Autoscaler (HPA)

### What Was Needed
- Create HPA manifest for automatic pod scaling
- Configure CPU and memory thresholds
- Verify metrics server is available
- Test HPA scaling behavior

### What Was Done
- Created `k8s/hpa.yaml`:
  - Min replicas: 2
  - Max replicas: 10
  - CPU threshold: 70% utilization
  - Memory threshold: 80% utilization
  - Scale up behavior: Immediate (can double pods per minute or add 2 pods)
  - Scale down behavior: 5-minute stabilization window (max 50% reduction per minute)
- Deployed HPA to cluster
- Verified metrics server is available and working
- Updated `k8s/README.md` with HPA documentation

### Issues Encountered
- None - HPA deployed successfully
- Metrics server was already available in GKE cluster

### Solution
- N/A

### Verification
- HPA created and active
- Metrics showing: CPU 0%, Memory 34% (below thresholds)
- Current replicas: 2 (min)
- HPA ready to scale when thresholds are exceeded

---

## Summary

**Completed Tasks:**
- ✅ Docker containerization with production-ready setup
- ✅ Artifact Registry configured and image pushed
- ✅ GKE cluster created and configured
- ✅ Kubernetes deployment manifests created and deployed
- ✅ Application running on Kubernetes
- ✅ HPA configured for automatic scaling

**Key Achievements:**
- Production-ready containerized application
- Scalable Kubernetes deployment
- External access via LoadBalancer
- Health checks configured for reliability
- Automatic scaling with HPA (2-10 pods based on CPU/memory)

**Time Spent:** ~3-4 days  
**Files Created:** `docker/Dockerfile`, `docker/.dockerignore`, `k8s/*.yaml`, `k8s/README.md`

