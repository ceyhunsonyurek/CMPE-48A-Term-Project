# CMPE 48A Term Project - Migration Roadmap

## 📋 Overview

This document provides a step-by-step roadmap to transform the existing **URL Shortener + QR Code Generator** Flask application into a **cloud-native architecture** that meets CMPE 48A Term Project requirements.

**Current State:**
- Monolithic Flask application
- AWS S3 usage
- MySQL database (not managed)
- Session-based authentication
- Gradio AI service integration

**Target State:**
- Containerized deployment with Kubernetes (GKE) + HPA
- GCP Cloud Storage
- Functional services on VMs
- Serverless operations with Cloud Functions
- Locust performance testing
- End-to-end cloud-native architecture

---

## 🎯 Architecture Transformation Strategy

### Current Architecture → Target Architecture

```
CURRENT:
[Flask App] → [MySQL] → [AWS S3] → [Gradio API]

TARGET:
[GKE Pods] → [VM: MySQL] → [Cloud Storage] → [Gradio API]
     ↓
[Cloud Functions] → [VM: Redis/Cache] → [VM: Monitoring]
```

### Component Distribution Recommendation

1. **Kubernetes (GKE):**
   - Flask web application (main application)
   - Automatic scaling with HPA

2. **VMs (Compute Engine):**
   - **VM 1:** MySQL Database Server (functional role)
   - **VM 2:** Redis Cache + Session Store (optional but recommended)
   - **VM 3:** Monitoring/Logging (Prometheus/Grafana) - optional

3. **Cloud Functions:**
   - URL redirection operation (async, fast response)
   - QR code generation triggering (async processing)
   - Webhook handler (optional)

4. **Cloud Storage:**
   - QR code images
   - Static files (background images, etc.)

---

## 📅 Roadmap - By Difficulty Level

### 🟢 LEVEL 1: Easy (1-2 Days) - Basic Preparation

#### 1.1 Project Structure Preparation
**Duration:** 2-3 hours  
**Difficulty:** Easy

**Tasks:**
- [ ] Organize GitHub repository
- [ ] Create folder structure:
  ```
  /
  ├── app/                    # Flask application
  ├── docker/                 # Dockerfile
  ├── k8s/                    # Kubernetes manifests
  ├── cloud-functions/        # Cloud Functions code
  ├── vm-scripts/             # VM setup scripts
  ├── locust/                 # Locust test scripts
  ├── terraform/              # Terraform (optional)
  └── docs/                   # Documentation
  ```
- [ ] Update `.gitignore` (config.json, secrets, etc.)
- [ ] Create README.md template

**Output:** Organized project structure

---

#### 1.2 Environment Variables and Config Management
**Duration:** 1-2 hours  
**Difficulty:** Easy

**Tasks:**
- [ ] Use environment variables instead of `config.json`
- [ ] Update config loading in `app.py`:
  ```python
  import os
  db_host = os.getenv('DB_HOST', 'localhost')
  # etc.
  ```
- [ ] Create `.env.example` file
- [ ] Prepare Kubernetes manifests for ConfigMap and Secrets

**Output:** Environment-based configuration

---

#### 1.3 AWS S3 → GCP Cloud Storage Migration
**Duration:** 2-3 hours  
**Difficulty:** Easy

**Tasks:**
- [ ] Use `google-cloud-storage` instead of `boto3`
- [ ] Update S3 upload function in `app.py`:
  ```python
  from google.cloud import storage
  
  def upload_to_gcs(file_path, bucket_name, blob_name):
      client = storage.Client()
      bucket = client.bucket(bucket_name)
      blob = bucket.blob(blob_name)
      blob.upload_from_filename(file_path)
      return blob.public_url
  ```
- [ ] Migrate files from existing S3 bucket to GCS (optional)
- [ ] Update S3 URLs in templates to GCS URLs

**Output:** GCP Cloud Storage integration

---

### 🟡 LEVEL 2: Medium (3-5 Days) - Containerization and Kubernetes

#### 2.1 Docker Containerization
**Duration:** 1 day  
**Difficulty:** Medium

**Tasks:**
- [ ] Create `Dockerfile`:
  ```dockerfile
  FROM python:3.9-slim
  WORKDIR /app
  COPY requirements.txt .
  RUN pip install --no-cache-dir -r requirements.txt
  COPY app/ ./app/
  COPY templates/ ./templates/
  EXPOSE 5000
  CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app.app:application"]
  ```
- [ ] Update `requirements.txt` (add gunicorn)
- [ ] Create `.dockerignore`
- [ ] Build and test Docker image locally
- [ ] Multi-stage build (optional, image size optimization)

**Output:** Working Docker image

---

#### 2.2 GCP Container Registry/Artifact Registry Setup
**Duration:** 2-3 hours  
**Difficulty:** Easy-Medium

**Tasks:**
- [ ] Create GCP project
- [ ] Enable Container Registry or Artifact Registry
- [ ] Push Docker image to GCP:
  ```bash
  gcloud auth configure-docker
  docker tag app-image gcr.io/PROJECT_ID/app-image:latest
  docker push gcr.io/PROJECT_ID/app-image:latest
  ```
- [ ] Test image pull

**Output:** Container image on GCP

---

#### 2.3 GKE Cluster Creation
**Duration:** 2-3 hours  
**Difficulty:** Medium

**Tasks:**
- [ ] Create GKE cluster (minimal node count for cost):
  ```bash
  gcloud container clusters create my-cluster \
    --num-nodes=2 \
    --machine-type=e2-small \
    --region=us-central1
  ```
- [ ] Configure `kubectl` connection
- [ ] Test cluster
- [ ] Configure node pools (optional)

**Output:** Working GKE cluster

---

#### 2.4 Kubernetes Deployment Manifests
**Duration:** 1 day  
**Difficulty:** Medium

**Tasks:**
- [ ] Create `k8s/deployment.yaml`:
  - Container image reference
  - Resource requests/limits
  - Environment variables (ConfigMap/Secrets)
  - Health checks (liveness, readiness)
  - Replicas: 2-3 (initial)
- [ ] Create `k8s/service.yaml` (ClusterIP or LoadBalancer)
- [ ] Create `k8s/configmap.yaml` (non-sensitive config)
- [ ] Create `k8s/secret.yaml` (database credentials, etc.)
- [ ] Test with `kubectl apply`
- [ ] Verify pods are running

**Output:** Application running on Kubernetes

---

#### 2.5 Horizontal Pod Autoscaler (HPA)
**Duration:** 3-4 hours  
**Difficulty:** Medium

**Tasks:**
- [ ] Create `k8s/hpa.yaml`:
  ```yaml
  apiVersion: autoscaling/v2
  kind: HorizontalPodAutoscaler
  metadata:
    name: app-hpa
  spec:
    scaleTargetRef:
      apiVersion: apps/v1
      kind: Deployment
      name: app-deployment
    minReplicas: 2
    maxReplicas: 10
    metrics:
    - type: Resource
      resource:
        name: cpu
        target:
          type: Utilization
          averageUtilization: 70
    - type: Resource
      resource:
        name: memory
        target:
          type: Utilization
          averageUtilization: 80
  ```
- [ ] Verify metrics server is installed
- [ ] Test HPA with load test
- [ ] Observe scaling behavior

**Output:** Working HPA

---

### 🟠 LEVEL 3: Medium-Hard (1 Week) - VM and Database Setup

#### 3.1 MySQL Database VM Setup
**Duration:** 1-2 days  
**Difficulty:** Medium-Hard

**Tasks:**
- [ ] Create Compute Engine VM instance:
  ```bash
  gcloud compute instances create mysql-vm \
    --machine-type=e2-small \
    --image-family=ubuntu-2004-lts \
    --image-project=ubuntu-os-cloud \
    --tags=mysql-server
  ```
- [ ] Create firewall rule (MySQL port 3306)
- [ ] SSH to VM
- [ ] Create MySQL installation script (`vm-scripts/setup-mysql.sh`):
  ```bash
  #!/bin/bash
  sudo apt-get update
  sudo apt-get install -y mysql-server
  sudo mysql_secure_installation
  # Create database and user
  ```
- [ ] Create database schema:
  ```sql
  CREATE DATABASE urlshortener;
  CREATE USER 'appuser'@'%' IDENTIFIED BY 'password';
  GRANT ALL PRIVILEGES ON urlshortener.* TO 'appuser'@'%';
  FLUSH PRIVILEGES;
  ```
- [ ] Create `users` and `urls` tables
- [ ] Verify MySQL allows remote connections
- [ ] Test connection from Kubernetes to VM

**Output:** MySQL database running on VM

---

#### 3.2 Network Configuration
**Duration:** 1 day  
**Difficulty:** Medium

**Tasks:**
- [ ] Create VPC network (or use default)
- [ ] Subnet configuration
- [ ] Firewall rules:
  - GKE → MySQL VM (3306)
  - GKE → Cloud Functions (HTTPS)
  - External → GKE (80/443)
- [ ] Use private IP (cost optimization)
- [ ] Test network connectivity

**Output:** Secure network configuration

---

#### 3.3 Redis Cache VM (Optional but Recommended)
**Duration:** 1 day  
**Difficulty:** Medium

**Tasks:**
- [ ] Create Redis VM instance
- [ ] Redis installation script (`vm-scripts/setup-redis.sh`)
- [ ] Use Redis for session store:
  - Redis integration with Flask-Session
  - Update session config in `app.py`
- [ ] Use Redis for URL cache (frequently used URLs)
- [ ] Connection pooling

**Why Recommended:**
- Required for session management (multi-pod scenario)
- Performance improvement
- Strengthens VM's functional role

**Output:** Redis cache VM (optional)

---

### 🔴 LEVEL 4: Hard (1-2 Weeks) - Cloud Functions and Refactoring

#### 4.1 URL Redirect Cloud Function
**Duration:** 2-3 days  
**Difficulty:** Hard

**Tasks:**
- [ ] Create `cloud-functions/url-redirect/main.py`:
  ```python
  from google.cloud import storage
  import pymysql
  from hashids import Hashids
  import os
  
  def url_redirect(request):
      hashid = request.path.split('/')[-1]
      # Decode hashid
      # Get original_url from MySQL
      # Increment clicks
      # Redirect response
  ```
- [ ] Create `cloud-functions/url-redirect/requirements.txt`
- [ ] Deploy Cloud Function (HTTP trigger):
  ```bash
  gcloud functions deploy url-redirect \
    --runtime python39 \
    --trigger-http \
    --allow-unauthenticated \
    --entry-point url_redirect
  ```
- [ ] Test function
- [ ] Remove URL redirect route from Flask app (or make optional)
- [ ] Route ingress/load balancer to Cloud Function

**Output:** Cloud Function for URL redirect

---

#### 4.2 QR Code Generation Trigger Function
**Duration:** 2-3 days  
**Difficulty:** Hard

**Tasks:**
- [ ] Create Pub/Sub topic for async QR code generation
- [ ] Create `cloud-functions/qr-generator/main.py`:
  ```python
  from google.cloud import pubsub_v1
  from google.cloud import storage
  from gradio_client import Client
  
  def qr_generation_trigger(request):
      # Receive Pub/Sub message
      # Generate QR code with Gradio client
      # Upload to GCS
      # Update status in database
  ```
- [ ] Deploy Cloud Function (Pub/Sub trigger)
- [ ] Make QR generation async in Flask app:
  - Register URL
  - Publish Pub/Sub message
  - Return immediate response (until QR code is ready)
- [ ] Add status polling endpoint (is QR code ready?)

**Output:** Async QR code generation

---

#### 4.3 Flask App Refactoring
**Duration:** 1-2 days  
**Difficulty:** Medium-Hard

**Tasks:**
- [ ] Remove URL redirect route (moved to Cloud Function)
- [ ] Make QR generation async
- [ ] Add connection pooling (SQLAlchemy or PyMySQL pool)
- [ ] Improve error handling
- [ ] Add logging (structured logging)
- [ ] Add health check endpoint (`/health`)
- [ ] Add metrics endpoint (Prometheus format, optional)

**Output:** Refactored Flask app

---

### 🟣 LEVEL 5: Medium (3-5 Days) - Performance Testing

#### 5.1 Locust Test Scripts
**Duration:** 2-3 days  
**Difficulty:** Medium

**Tasks:**
- [ ] Create `locust/locustfile.py`:
  ```python
  from locust import HttpUser, task, between
  
  class URLShortenerUser(HttpUser):
      wait_time = between(1, 3)
      
      @task(3)
      def create_short_url(self):
          # Login
          # URL shorten
          # QR code generate
      
      @task(5)
      def redirect_url(self):
          # Click short URL
      
      @task(2)
      def view_stats(self):
          # Stats page
  ```
- [ ] Design test scenarios:
  - Baseline test (normal load)
  - Load test (expected max load)
  - Stress test (system limits)
  - Spike test (sudden load increase)
- [ ] Determine test parameters:
  - Users: 10, 50, 100, 500
  - Spawn rate: 1, 5, 10 users/sec
  - Duration: 5, 10, 30 minutes
- [ ] Distributed Locust setup (optional)

**Output:** Locust test scripts

---

#### 5.2 Performance Metrics Collection
**Duration:** 1-2 days  
**Difficulty:** Medium

**Tasks:**
- [ ] Google Cloud Monitoring setup
- [ ] Kubernetes metrics collection
- [ ] VM metrics collection
- [ ] Cloud Functions metrics
- [ ] Custom metrics (application-level)
- [ ] Create Grafana dashboard (optional)
- [ ] Metrics export script (CSV/JSON)

**Output:** Collected performance metrics

---

#### 5.3 Performance Testing Execution
**Duration:** 1 day  
**Difficulty:** Easy-Medium

**Tasks:**
- [ ] Run each test scenario
- [ ] Save Locust HTML reports
- [ ] Collect and save metrics
- [ ] Observe HPA scaling events
- [ ] Record error rates
- [ ] Take screenshots (dashboards, graphs)

**Output:** Performance test results

---

### 🔵 LEVEL 6: Medium (2-3 Days) - Documentation and Finalization

#### 6.1 Architecture Diagram
**Duration:** 1 day  
**Difficulty:** Easy-Medium

**Tasks:**
- [ ] Use Draw.io or Lucidchart
- [ ] Use GCP Architecture Diagram template
- [ ] Show all components:
  - GKE cluster (pods, services, HPA)
  - VMs (MySQL, Redis)
  - Cloud Functions
  - Cloud Storage
  - VPC network
  - Load balancer/Ingress
- [ ] Show data flow
- [ ] Show network connections
- [ ] Export (PNG, PDF)

**Output:** Architecture diagram

---

#### 6.2 Technical Report Writing
**Duration:** 2-3 days  
**Difficulty:** Medium

**Tasks:**
- [ ] Write all sections:
  1. Architecture diagram
  2. Component descriptions
  3. Deployment process (step-by-step)
  4. Locust experiment design
  5. Performance results visualization
  6. Results explanation
  7. Cost breakdown
- [ ] Add screenshots
- [ ] Add graphs and charts
- [ ] Add references
- [ ] Format: Markdown → PDF

**Output:** Technical report

---

#### 6.3 README.md Detailing
**Duration:** 1 day  
**Difficulty:** Easy-Medium

**Tasks:**
- [ ] Project description
- [ ] Architecture overview
- [ ] **Step-by-step setup instructions:**
  - GCP project creation
  - GKE cluster setup
  - VM setup
  - Cloud Functions deployment
  - Kubernetes deployment
  - Configuration
- [ ] Test execution instructions
- [ ] Troubleshooting section
- [ ] Cost estimation
- [ ] Add screenshots

**Output:** Detailed README.md

---

#### 6.4 Demo Video Preparation
**Duration:** 1 day  
**Difficulty:** Easy

**Tasks:**
- [ ] Screen recording:
  - System overview (GCP console)
  - Main features (URL shorten, QR generate)
  - Kubernetes dashboard (pods, HPA)
  - Performance test execution (brief)
  - Scaling behavior (HPA)
  - Results (metrics, charts)
- [ ] Video editing (max 2 minutes)
- [ ] Voice narration (optional)
- [ ] Upload to YouTube/Google Drive

**Output:** Demo video

---

#### 6.5 Cost Breakdown Preparation
**Duration:** 1 day  
**Difficulty:** Easy

**Tasks:**
- [ ] Collect costs from GCP Billing Console
- [ ] Breakdown for each service:
  - GKE cluster (nodes, egress)
  - VM instances (compute, disk, network)
  - Cloud Functions (invocations, compute time)
  - Cloud Storage (storage, egress)
  - Network (egress, load balancer)
- [ ] Calculate total cost
- [ ] Show it stayed within $300
- [ ] Add cost optimization strategies

**Output:** Cost breakdown report

---

## 🎁 Bonus: Terraform (Optional, Not Priority)

### Terraform Infrastructure as Code
**Duration:** 3-5 days (if everything goes well)  
**Difficulty:** Hard

**Tasks:**
- [ ] Create `terraform/main.tf`
- [ ] Create `terraform/variables.tf`
- [ ] Create `terraform/outputs.tf`
- [ ] Define all GCP resources with Terraform:
  - GKE cluster
  - VM instances
  - VPC and network
  - Cloud Functions
  - Cloud Storage buckets
  - IAM roles
  - Firewall rules
- [ ] Test with `terraform apply`
- [ ] Add documentation

**Note:** This bonus should only be done after all other tasks are completed.

---

## 📊 Recommended Additional Features (Optional)

### 1. Monitoring VM (Recommended)
**Why:** Strengthens VM's functional role, improves system monitoring

**Tasks:**
- [ ] Prometheus + Grafana VM setup
- [ ] Kubernetes metrics scraping
- [ ] Custom dashboards
- [ ] Alerting rules

**Difficulty:** Medium  
**Duration:** 1-2 days

---

### 2. Background Worker VM
**Why:** Dedicated worker for QR code generation, strengthens VM's role

**Tasks:**
- [ ] Create worker VM
- [ ] Pub/Sub subscriber worker
- [ ] Perform QR code generation on worker
- [ ] Upload to GCS

**Difficulty:** Medium-Hard  
**Duration:** 2-3 days

---

### 3. API Gateway Cloud Function
**Why:** Increases Cloud Functions usage, API versioning

**Tasks:**
- [ ] API Gateway Cloud Function
- [ ] Request routing
- [ ] Authentication/Authorization
- [ ] Rate limiting

**Difficulty:** Hard  
**Duration:** 2-3 days

---

## ⚠️ Critical Notes and Things to Watch Out For

### Budget Management
- [ ] Set up GCP Billing alerts
- [ ] Use preemptible/spot instances (for cost)
- [ ] Minimal node count (2 nodes sufficient for testing)
- [ ] Auto-shutdown scripts (when not in use)
- [ ] Resource sizing (e2-small, e2-medium sufficient)

### Security
- [ ] Secrets management (GCP Secret Manager)
- [ ] IAM roles and permissions
- [ ] Firewall rules (minimal open ports)
- [ ] HTTPS/SSL (for Ingress)
- [ ] Database credentials security

### Testing
- [ ] Test at each step
- [ ] Staging environment (optional)
- [ ] Prepare rollback plan
- [ ] Backup strategy

### Documentation
- [ ] Document each step
- [ ] Take screenshots
- [ ] Save commands
- [ ] Keep troubleshooting notes

---

## 📅 Recommended Timeline

### Week 1-2: Basic Preparation and Containerization
- Level 1 (Easy): Project structure, config, GCS migration
- Level 2 (Medium): Docker, GKE, Kubernetes deployment, HPA

### Week 3-4: VM and Database
- Level 3 (Medium-Hard): MySQL VM, Network, Redis (optional)

### Week 5-6: Cloud Functions and Refactoring
- Level 4 (Hard): Cloud Functions, Flask refactoring

### Week 7: Performance Testing
- Level 5 (Medium): Locust tests, metrics collection

### Week 8: Documentation and Finalization
- Level 6 (Medium): Documentation, report, video, cost breakdown

### Bonus (Optional):
- Terraform: Week 9 (if time remains)

**Total Duration:** 8 weeks (approximately 2 months)

---

## ✅ Final Checklist

### Mandatory Components:
- [ ] Kubernetes cluster (GKE) - running
- [ ] Containerized application (Docker) - deployed
- [ ] Kubernetes Deployments - running
- [ ] HPA (Horizontal Pod Autoscaler) - active and tested
- [ ] Virtual Machines (Compute Engine) - functional (MySQL)
- [ ] Cloud Functions - active usage (URL redirect, QR generation)

### Performance Testing:
- [ ] Locust test scripts - ready
- [ ] Test scenarios - executed
- [ ] Metric collection - completed
- [ ] Visualization - charts/graphs ready

### Documentation:
- [ ] Cloud architecture diagram - ready
- [ ] Component descriptions - written
- [ ] Deployment process - documented
- [ ] Locust experiment design - explained
- [ ] Performance results visualization - graphs ready
- [ ] Results explanation - analyzed
- [ ] Cost breakdown - within $300

### Deliverables:
- [ ] Working system on GCP - running
- [ ] Technical report - ready
- [ ] Demo video (max 2 min) - ready
- [ ] GitHub repository - organized, README detailed

---

## 🎯 Conclusion

This roadmap provides step-by-step guidance to transform the existing Flask application into a cloud-native architecture. Each level depends on the completion of the previous level.

**Priority order:**
1. Basic preparation (Level 1)
2. Kubernetes deployment (Level 2)
3. VM and database (Level 3)
4. Cloud Functions (Level 4)
5. Performance testing (Level 5)
6. Documentation (Level 6)
7. Terraform (Bonus, optional)

**For Success:**
- Test each step
- Document it
- Monitor budget
- Manage time

---

*This roadmap is based on ARCHITECTURE_ANALYSIS.md and PROJECT_REQUIREMENTS_ANALYSIS.md files.*

