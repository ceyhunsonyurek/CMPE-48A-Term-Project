# Technical Report: URL Shortener Cloud Deployment

## 1. Cloud Architecture Diagram

The URL Shortener application is deployed on Google Cloud Platform using a microservices architecture with containerized services, managed infrastructure, and serverless components.

![Cloud Architecture Diagram](architecture.png)

### Architecture Overview

The system follows a **hybrid cloud-native architecture** combining:
- **Containerized services** (Flask application on GKE)
- **Virtual machines** (MySQL database server)
- **Serverless functions** (Cloud Function for URL redirection)
- **Managed storage** (Cloud Storage for static assets)

---

## 2. Component Description and Interactions

### 2.1 Flask Application (GKE Pods)

**Component**: Containerized Flask web application running on Google Kubernetes Engine

**Architecture Type**: This is a **monolithic application** where backend and frontend run together in the same container. Flask serves both the API logic and renders HTML templates using Jinja2. There is no separate frontend service - all HTML/CSS/JavaScript is served directly by Flask pods.

**Responsibilities**:
- User authentication (login/registration)
- URL shortening with hashid encoding
- QR code generation using Python `qrcode` library
- Session management

**Pod Configuration**:
| Setting | Value |
|---------|-------|
| GKE Node Machine Type | e2-small |
| GKE Nodes | 3 (auto-scaled across zones for HA) |
| GKE Region | us-east1 |
| Pod Replicas | 2-10 (HPA controlled) |
| CPU Request | 300m |
| CPU Limit | 1000m |
| Memory Request | 512Mi |
| Memory Limit | 1Gi |
| Container Port | 5000 |
| Gunicorn Workers | 4 |
| Gunicorn Threads | 2 per worker |

**Health Probes**:
| Probe | Path | Initial Delay | Period | Timeout | Failure Threshold |
|-------|------|---------------|--------|---------|-------------------|
| Liveness | /health | 30s | 20s | 3s | 5 |
| Readiness | /health | 15s | 10s | 2s | 3 |

**Connection Pooling** (per pod):
| Setting | Value |
|---------|-------|
| DB_POOL_MIN_SIZE | 5 connections |
| DB_POOL_MAX_SIZE | 20 connections |
| Total Max (2 pods) | 40 connections |

**Interactions**:
- **→ MySQL VM**: Reads/writes user data, URL records, and click statistics
- **→ Cloud Storage**: Uploads generated QR code images
- **← Load Balancer**: Receives HTTP requests from users
- **← HPA**: Automatically scales based on CPU (70%) and memory (80%) utilization

**Configuration**:
- Environment variables from ConfigMap (non-sensitive) and Secrets (sensitive)
- GCS authentication via service account key mounted as volume

---

### 2.2 MySQL Database (Compute Engine VM)

**Component**: MySQL 8.0 server running on Ubuntu 22.04 LTS VM instance

**VM Configuration**:
| Setting | Value |
|---------|-------|
| VM Name | mysql-vm |
| Zone | us-east1-b |
| Machine Type | e2-small (2 vCPUs, 2GB RAM) |
| Boot Disk | 20GB standard persistent disk |
| OS Image | Ubuntu 22.04 LTS |
| Internal IP | 10.142.0.15 |
| External IP | 34.148.55.158 |
| Network Tag | mysql-server |

**Database Schema**:
- **`users` table**: Stores user credentials (id, username, SHA256-hashed password).
- **`urls` table**: Stores shortened URLs with original URL, owner user_id, click count, and creation timestamp.

**Firewall Rules**:
| Rule Name | Source | Port | Purpose |
|-----------|--------|------|---------|
| allow-mysql-from-gke | 10.0.0.0/8 | 3306 | GKE pods access |
| allow-mysql-from-cloud-functions | 0.0.0.0/0 | 3306 | Cloud Function access |

**Interactions**:
- **← Flask Pods**: Handles database queries for user authentication, URL creation, and statistics
- **← Cloud Function**: Processes URL lookup and click increment operations
- **Network**: Protected by firewall rules with network tags

---

### 2.3 Cloud Function (URL Redirect)

**Component**: Google Cloud Function Gen2 for serverless URL redirection

**Function Configuration**:
| Setting | Value |
|---------|-------|
| Function Name | url-redirect |
| Generation | Gen2 (Cloud Run based) |
| Region | us-east1 |
| Runtime | Python 3.11 |
| Entry Point | url_redirect |
| Memory | 256MB |
| Timeout | 30 seconds |
| Min Instances | 0 (scales to zero) |
| Max Instances | 10 |
| Trigger | HTTP (unauthenticated) |
| Function URL | https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect |

**Connection Pooling**: The function maintains a small connection pool (1-5 connections) using DBUtils. Since Cloud Functions can reuse instances, the pool persists across invocations, reducing connection overhead.

**Request Flow**:
1. User clicks short URL (e.g., `/aB3d`)
2. Cloud Function receives HTTP request
3. Extracts hashid from path
4. Decodes hashid using Hashids library (same salt as Flask app)
5. Queries MySQL for original URL: `SELECT original_url, clicks FROM urls WHERE id = ?`
6. Increments click count: `UPDATE urls SET clicks = ? WHERE id = ?`
7. Returns HTTP 302 redirect to original URL

**Interactions**:
- **→ MySQL VM**: Queries database for URL lookup and updates click count
- **← Users**: Receives HTTP requests for short URLs
- **→ Users**: Returns HTTP 302 redirect response

**Why Serverless for Redirects**:
- URL redirects are stateless operations (no session needed)
- Low latency requirement (users expect instant redirects)
- Variable traffic (scales to zero when not in use, saves cost)
- Offloads redirect traffic from main Flask application

---

### 2.4 Cloud Storage (GCS Bucket)

**Component**: Google Cloud Storage bucket for static asset storage

**Responsibilities**:
- Stores QR code images generated by Flask application
- Provides public URLs for QR code access
- Versioning enabled for backup and recovery

**Interactions**:
- **← Flask Pods**: Receives QR code image uploads after generation
- **→ Users**: Serves QR code images via public URLs
- **Authentication**: Uses GKE service account with Storage Object Admin role

**Storage Configuration**:
- Uniform bucket-level access enabled
- Lifecycle rules for automatic cleanup of old objects

---

### 2.5 Artifact Registry

**Component**: Docker image repository for container images

**Responsibilities**:
- Stores Docker images for Flask application
- Provides secure image pull access for GKE cluster
- Supports versioning and image management

**Interactions**:
- **← CI/CD or Manual Build**: Receives pushed Docker images
- **→ GKE Pods**: Provides container images for pod deployment

---

### 2.6 Horizontal Pod Autoscaler (HPA)

**Component**: Kubernetes HPA for automatic scaling

**Configuration**:
- **Min Replicas**: 2
- **Max Replicas**: 10
- **CPU Threshold**: 70% utilization
- **Memory Threshold**: 80% utilization

**Scaling Behavior**:
- **Scale Up**: Immediate (0s stabilization), can double pods per minute or add 2 pods
- **Scale Down**: 5-minute stabilization window, max 50% reduction per minute

**Interactions**:
- **Monitors**: Pod CPU and memory metrics
- **Controls**: Number of Flask application replicas
- **Triggers**: Automatic scaling based on resource utilization

---

### 2.7 Load Balancer Service

**Component**: Kubernetes LoadBalancer service

**Responsibilities**:
- Distributes incoming HTTP traffic across Flask pods
- Provides external IP address for public access
- Maintains session affinity (ClientIP) for 3 hours

**Session Affinity (Sticky Sessions)**:

Since Flask uses in-memory cookie-based sessions, we configured the LoadBalancer with `sessionAffinity: ClientIP`. This ensures that requests from the same client IP are always routed to the same pod during a session.

| Setting | Value |
|---------|-------|
| Session Affinity Type | ClientIP |
| Timeout | 10800 seconds (3 hours) |

**How it works**:
1. When a user first connects, the LoadBalancer picks a pod and remembers the client IP
2. All subsequent requests from that IP go to the same pod for 3 hours
3. This prevents session loss - if user A logs in on Pod 1, their session cookie data stays on Pod 1

**Why this is needed**:
- Flask stores session data in memory (not in a shared database)
- Without sticky sessions, a user might log in on Pod 1, but their next request goes to Pod 2, which has no knowledge of their session
- The user would appear logged out on every other request

**Trade-off**: Less optimal load distribution, but necessary for session consistency without external session storage (like Redis).

**Interactions**:
- **← Internet**: Receives user requests
- **→ GKE Pods**: Routes requests to same pod based on client IP
- **Port Mapping**: External port 80 → Container port 5000

---

### 2.8 Network and Security

**Firewall Rules**:
1. **allow-mysql-from-gke**: Allows TCP 3306 from GKE cluster IP range (10.0.0.0/8) to MySQL VM
2. **allow-mysql-from-cloud-functions**: Allows TCP 3306 from Cloud Functions to MySQL VM

**Network Flow**:
- GKE pods communicate with MySQL via internal IP addresses
- Cloud Function accesses MySQL through firewall-allowed connections
- All inter-service communication happens within GCP network

---

## 3. Deployment Process

This section documents the actual deployment process we followed to deploy the URL Shortener application on GCP.

### Phase 1: Project Preparation

We started by organizing the repository structure for cloud-native deployment:
- Created `app/` folder for Flask application code
- Created `docker/` folder for Dockerfile and Docker-related files
- Created `k8s/` folder for Kubernetes manifests
- Created `cloud-functions/` folder for Cloud Function code
- Created `vm-scripts/` folder for VM setup scripts

We migrated from AWS S3 to GCP Cloud Storage by replacing `boto3` with `google-cloud-storage` library and updating all template references.

### Phase 2: Docker Containerization

We created a production-ready Dockerfile with the following specifications:

| Setting | Value |
|---------|-------|
| Base Image | python:3.9-slim |
| WSGI Server | Gunicorn (4 workers, 2 threads) |
| Port | 5000 |
| User | Non-root (appuser) |

We encountered an issue where the container couldn't start due to Gradio client's `input()` call in non-interactive mode. We solved this by removing the external Gradio dependency and implementing internal QR code generation using the Python `qrcode` library.

### Phase 3: GKE Cluster Setup

We created the GKE cluster with the following configuration:

| Setting | Value |
|---------|-------|
| Cluster Name | url-shortener-cluster |
| Region | us-east1 |
| Machine Type | e2-small |
| Requested Nodes | 1 |
| Actual Nodes | 3 (GKE auto-scaled across zones for HA) |
| Features | Auto-repair, Auto-upgrade enabled |

**Issue Encountered**: We initially tried us-central1 region but hit the `IN_USE_ADDRESSES` quota limit (limit: 4). Free trial accounts are not eligible for quota increases, so we switched to us-east1 region.

### Phase 4: Artifact Registry and Image Push

We set up Artifact Registry to store our Docker images:

| Setting | Value |
|---------|-------|
| Repository Name | url-shortener-repo |
| Location | us-central1 |
| Image | url-shortener:latest |

**Issue Encountered**: Initial image pull failed with "no match for platform in manifest" error because the image was built for ARM architecture (M1 Mac). We fixed this by rebuilding with `--platform linux/amd64` flag.

### Phase 5: Kubernetes Deployment

We created and applied the following Kubernetes manifests:

| Manifest | Purpose |
|----------|---------|
| deployment.yaml | Flask app with 2 replicas, resource limits, health probes |
| service.yaml | LoadBalancer with session affinity (ClientIP, 3h timeout) |
| configmap.yaml | Non-sensitive config (DB host, GCS bucket, etc.) |
| secret.yaml | Sensitive data (DB password, Flask secret key) |
| hpa.yaml | Auto-scaling (2-10 pods, CPU 70%, Memory 80%) |

**Issue Encountered**: GKE nodes couldn't pull images from Artifact Registry due to missing IAM permissions. We granted `roles/artifactregistry.reader` to the GKE service account.

**Deployment Results**:
- 2 pods running and ready
- LoadBalancer external IP: `35.237.64.253`
- Health check endpoint responding

### Phase 6: MySQL VM Setup

We created a Compute Engine VM for the MySQL database:

| Setting | Value |
|---------|-------|
| VM Name | mysql-vm |
| Zone | us-east1-b |
| Machine Type | e2-small |
| OS | Ubuntu 22.04 LTS |
| Internal IP | 10.142.0.15 |
| External IP | 34.148.55.158 |

We created a setup script (`vm-scripts/setup-mysql.sh`) that:
1. Installs MySQL server
2. Configures remote access (bind-address = 0.0.0.0)
3. Creates `urlshortener` database
4. Creates `appuser` with appropriate privileges
5. Creates `users` and `urls` tables with indexes

We also created a firewall rule (`allow-mysql-from-gke`) to allow TCP port 3306 from GKE cluster IP range (10.0.0.0/8).

### Phase 7: Cloud Function Deployment

We deployed a Cloud Function for URL redirection:

| Setting | Value |
|---------|-------|
| Function Name | url-redirect |
| Region | us-east1 |
| Runtime | Python 3.11 |
| Memory | 256MB |
| Timeout | 30s |
| Trigger | HTTP (unauthenticated) |
| Function URL | https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect |

**Issue Encountered**: Cloud Function couldn't connect to MySQL VM using internal IP (10.142.0.15). VPC Connector creation failed due to quota/permission issues. As a workaround, we used the external IP (34.148.55.158) with a permissive firewall rule.

### Phase 8: Final Integration

After deploying the Cloud Function, we updated the Kubernetes ConfigMap with the function URL and restarted the deployment:

```bash
kubectl apply -f k8s/configmap.yaml
kubectl rollout restart deployment url-shortener
```

### Issues Encountered and Solutions

| Issue | Solution |
|-------|----------|
| Quota limit in us-central1 | Switched to us-east1 region |
| ARM vs AMD64 image mismatch | Rebuilt with `--platform linux/amd64` |
| Artifact Registry permission denied | Granted `artifactregistry.reader` role to GKE SA |
| Cloud Function can't reach MySQL internal IP | Used external IP with firewall rule (temporary workaround) |
| Gradio client blocking container start | Replaced with internal `qrcode` library |

### Final Deployment State

| Component | Status | Details |
|-----------|--------|---------|
| GKE Cluster | ✅ Running | 3 nodes, us-east1 |
| Flask Pods | ✅ Running | 2 replicas, auto-scaling enabled |
| MySQL VM | ✅ Running | e2-small, us-east1-b |
| Cloud Function | ✅ Running | Gen2, us-east1 |
| Cloud Storage | ✅ Running | url-shortener-assets bucket |
| LoadBalancer | ✅ Running | External IP: 35.237.64.253 |
| HPA | ✅ Active | 2-10 replicas |

**Total Deployment Time**: ~9-12 days (including learning, debugging, and iterating)

---

