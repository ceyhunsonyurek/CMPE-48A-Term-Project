# CMPE 48A Term Project - Requirements Analysis

## 📋 Project Overview

**Course:** CMPE 48A - Cloud Computing  
**Platform:** Google Cloud Platform (GCP) - **REQUIRED**  
**Budget:** Must stay within $300 GCP free trial credit  
**Objective:** Cloud-native architecture design, implementation, and evaluation

---

## 🎯 Core Requirements (MANDATORY)

### 1. ✅ Containerized Workloads on Kubernetes

**What is Required:**
- Kubernetes (GKE - Google Kubernetes Engine) must be used
- Containerized workloads
- **Scalable deployment**
- **Deployments** must be used
- **HPA (Horizontal Pod Autoscaler)** must be used

**Why Required:**
- Fundamental component of modern cloud-native applications
- Automatic scaling capability
- Container orchestration learning
- Production-ready deployment patterns

**How It Should Be:**
- Application should be containerized in Docker
- Kubernetes Deployment manifest should be created
- HPA should be configured for CPU/memory-based automatic scaling
- Can start with minimum 2-3 pod replicas
- Resource limits/requests should be defined

**Where:**
- GCP → GKE (Google Kubernetes Engine)
- Kubernetes cluster should be created
- Node pools should be configured

---

### 2. ✅ Virtual Machines (VM)

**What is Required:**
- Virtual Machines must be integrated
- Must serve a **functional role** in the system (just existing is not enough!)

**Why Required:**
- Role of VMs in cloud architecture
- Hybrid approaches (container + VM)
- Integration with legacy systems
- Understanding different workload types

**How It Should Be:**
- VMs should perform an active task in the system
- Example use cases:
  - Database server (MySQL, PostgreSQL)
  - Message queue server (RabbitMQ, Redis)
  - Monitoring/logging server (Prometheus, Grafana)
  - File storage server
  - Background worker
  - API gateway
  - Load balancer (alternative)

**Where:**
- GCP → Compute Engine
- VM instances should be created
- Network configuration (VPC, firewall rules)

**⚠️ IMPORTANT:** VMs should not just "exist", they must serve a necessary function for the system to work!

---

### 3. ✅ Serverless Functions

**What is Required:**
- Google Cloud Functions must be used
- Serverless architecture pattern must be applied

**Why Required:**
- Serverless computing concept
- Event-driven architecture
- Cost optimization (pay-per-use)
- Auto-scaling (unlimited)

**How It Should Be:**
- Functions should be written with Cloud Functions
- Use cases:
  - URL redirection operation
  - QR code generation (async)
  - Webhook handler
  - Scheduled tasks (with Cloud Scheduler)
  - File processing (Cloud Storage trigger)
  - Database operations
  - API endpoints

**Where:**
- GCP → Cloud Functions
- HTTP trigger or event trigger (Cloud Storage, Pub/Sub, etc.)
- Runtime: Python, Node.js, Go, Java

**⚠️ IMPORTANT:** Functions must be part of the system, not just "hello world"!

---

## 📊 Performance Evaluation (MANDATORY)

### Testing Tool: **Locust**

**What is Required:**
- Performance tests with Locust
- Realistic user behavior simulation
- Traffic generation

**Why Locust:**
- Python-based, easy integration
- Distributed load testing
- Real-time metrics
- Custom user behavior scripting

### Test Design

**Independent Variables:**
- Request load (concurrent user count)
- Request rate (requests per second)
- Test duration
- Workload pattern (steady, ramp-up, spike)

**Dependent Variables:**
- Response time / Latency
- Throughput (requests per second)
- Error rate
- Resource utilization (CPU, memory)

### Metrics to Collect

1. **Request Latency:**
   - Average response time
   - P50, P95, P99 percentiles
   - Min/max response times

2. **Throughput:**
   - Requests per second (RPS)
   - Successful requests/sec
   - Failed requests/sec

3. **Resource Usage:**
   - CPU utilization (pod, node, VM)
   - Memory usage
   - Network I/O
   - Disk I/O

4. **Error Rates:**
   - HTTP error codes (4xx, 5xx)
   - Timeout errors
   - Connection errors

### Test Scenarios

1. **Baseline Test:** Performance under normal load
2. **Load Test:** Expected maximum load
3. **Stress Test:** Pushing system limits
4. **Spike Test:** Sudden load increases
5. **Endurance Test:** Long-term load

---

## 📝 Technical Report Requirements

### 1. Cloud Architecture Diagram

**What is Required:**
- Diagram showing system architecture
- All components and their relationships

**How It Should Be:**
- GCP services should be visualized
- Kubernetes cluster structure
- VMs and their roles
- Cloud Functions and their triggers
- Network structure (VPC, subnets)
- Data flow
- Load balancer, ingress

**Tools:**
- Draw.io, Lucidchart, Miro
- GCP Architecture Diagram template
- PlantUML (code-based)

---

### 2. Component Description

**What is Required:**
- Description of each component
- How components interact with each other

**Should Include:**
- Kubernetes components (Deployments, Services, HPA, Ingress)
- VM roles and configurations
- Cloud Functions purposes and triggers
- Database structure
- Storage (Cloud Storage, Persistent Volumes)
- Network structure
- Security (IAM, firewall rules)

---

### 3. Deployment Process

**What is Required:**
- Step-by-step deployment explanation

**Should Include:**
1. GCP project creation
2. GKE cluster setup
3. VM instance creation
4. Cloud Functions deployment
5. Container image build and push (Container Registry/Artifact Registry)
6. Kubernetes manifest application
7. Network configuration
8. Security settings
9. Monitoring/logging setup
10. Testing and validation

**Format:**
- Numbered steps
- Commands and outputs
- Screenshots (optional but helpful)

---

### 4. Locust Experiment Design

**What is Required:**
- Locust test design
- Parameter configurations

**Should Include:**
- Test scenario descriptions
- Locust script structure
- User behavior definitions
- Test parameters:
  - Number of users
  - Spawn rate
  - Test duration
  - Target endpoints
- Test environment (where it's run)

---

### 5. Performance Results Visualization

**What is Required:**
- Visualized performance results
- Charts, graphs

**Should Include:**
- Response time graphs (line chart, histogram)
- Throughput graphs
- CPU/Memory utilization graphs
- Error rate graphs
- HPA scaling events
- Comparison charts (different load levels)

**Tools:**
- Locust HTML report
- Grafana dashboards
- Google Cloud Monitoring
- Custom Python scripts (matplotlib, plotly)

---

### 6. Results Explanation

**What is Required:**
- Explanation of results
- Analysis of observed behaviors
- Explanations supported by performance metrics

**Should Include:**
- Commentary for each metric
- Bottleneck analysis
- Scaling behavior (how HPA worked)
- Error patterns
- Resource utilization analysis
- Recommendations and improvements

---

### 7. Cost Breakdown

**What is Required:**
- Cost breakdown
- Demonstration that it stayed within $300 budget

**Should Include:**
- Cost for each service:
  - GKE cluster (nodes, egress)
  - VM instances (compute, disk, network)
  - Cloud Functions (invocations, compute time)
  - Cloud Storage
  - Network (egress, load balancer)
  - Database (Cloud SQL, if used)
- Total cost
- Budget usage percentage
- Cost optimization strategies

**Source:**
- GCP Billing Console
- Cost calculator
- Actual billing reports

---

## 📦 Project Deliverables

### 1. ✅ Fully Working System on GCP

**What is Required:**
- Fully functional system running on GCP

**Checklist:**
- [ ] Kubernetes cluster is running
- [ ] Deployments are successful
- [ ] HPA is active and working
- [ ] VMs are running and functional
- [ ] Cloud Functions are deployed and working
- [ ] All components are connected
- [ ] Application works end-to-end

---

### 2. ✅ Comprehensive Technical Report

**What is Required:**
- Comprehensive report including all sections above

**Format:**
- PDF or Markdown
- Professional structure
- References and sources
- Screenshots and diagrams

---

### 3. ✅ Demo Video

**What is Required:**
- Video showing the system in action
- **Maximum 2 minutes**

**Should Include:**
- System overview
- Demonstration of main features
- Performance test execution (brief)
- Scaling behavior (HPA)
- Results display

**Format:**
- Screen recording
- Voice narration (optional but recommended)
- YouTube, Google Drive, etc. link

---

### 4. ✅ GitHub Repository

**What is Required:**
- Repository containing all code and deployment files

**Should Include:**

#### a) Application Source Code
- Application source code
- Dependencies (requirements.txt, package.json, etc.)
- Configuration files

#### b) Deployment Scripts/Manifests
- **Kubernetes YAML files:**
  - Deployment manifests
  - Service manifests
  - HPA manifests
  - Ingress manifests
  - ConfigMap, Secrets
  - PersistentVolumeClaims

- **Terraform files (for Bonus):**
  - main.tf
  - variables.tf
  - outputs.tf
  - modules (optional)

- **VM setup scripts:**
  - Startup scripts
  - Installation scripts
  - Configuration scripts

- **Cloud Functions code:**
  - Function source code
  - requirements.txt (for Python)
  - package.json (for Node.js)

#### c) Locust Test Scripts
- Locustfile.py
- Test data files
- Configuration files

#### d) README.md
- Project description
- Architecture overview
- **Step-by-step setup instructions**
- Deployment guide
- Test execution instructions
- Troubleshooting
- Cost estimation

**⚠️ IMPORTANT:** README should be detailed enough for someone else to set up the system from scratch!

---

## 💰 Budget and Platform Constraints

### Platform: Google Cloud Platform (GCP) - REQUIRED

**Why GCP:**
- Course requirement
- $300 free trial
- All necessary services available

**GCP Services to Use:**
- GKE (Google Kubernetes Engine)
- Compute Engine (for VMs)
- Cloud Functions
- Cloud Storage (container images, static files)
- VPC (Virtual Private Cloud)
- Cloud Load Balancing
- Cloud Monitoring
- Container Registry / Artifact Registry

### Budget: $300 Free Trial

**Constraints:**
- All resources must stay within $300
- You are responsible for budget overruns
- Monitoring and optimization required

**Cost Optimization:**
- Use preemptible/spot instances
- Minimal node count (for testing)
- Auto-shutdown (when not in use)
- Resource sizing (don't use unnecessarily large instances)
- Region selection (cheaper regions)

**⚠️ WARNING:** Automatic billing may occur after free trial ends! Set up billing alerts!

---

## 🎁 Bonus Challenge: Terraform (Optional)

### What is Required:
- Infrastructure as Code (IaC) usage
- Define entire infrastructure with Terraform

### Why Bonus:
- Advanced DevOps practices
- System reproducibility
- Version control for infrastructure
- +5% extra points

### How It Should Be:
- All GCP resources should be defined with Terraform
- Terraform state management
- Use of variables and outputs
- Modules (optional but good practice)
- Terraform usage instructions in README

### What to Define with Terraform:
- GKE cluster
- VM instances
- VPC and network
- Cloud Functions
- Cloud Storage buckets
- IAM roles and policies
- Firewall rules

---

## 📊 Grading Criteria

| Component | Weight |
|-----------|--------|
| Technical Report Content | 45% |
| In-Class Presentation Quality | 25% |
| GitHub Repo Organization & Reproducibility | 15% |
| Demo Video Clarity & Quality | 15% |
| **Bonus: Terraform** | **+5%** |

### Detailed Explanation:

#### 1. Technical Report (45%)
- **Highest weight!**
- Comprehensiveness of all sections
- Architecture diagram quality
- Depth of performance analysis
- Explanation of results
- Accuracy of cost breakdown

#### 2. In-Class Presentation (25%)
- Presentation quality
- Time management
- Answering questions
- Demo (live or video)

#### 3. GitHub Repo (15%)
- Code organization
- README quality
- Reproducibility (can someone else set it up?)
- Deployment scripts functionality
- Documentation

#### 4. Demo Video (15%)
- Clarity and quality
- Adherence to 2-minute limit
- Showing all system features
- Professional appearance

#### 5. Terraform Bonus (+5%)
- Entire infrastructure defined with Terraform
- Must be working
- Documentation

---

## 🔍 Critical Points and Things to Watch Out For

### ✅ Things to Do:

1. **All 3 mandatory components must be present:**
   - Kubernetes (with HPA)
   - VM (functional role)
   - Cloud Functions (active usage)

2. **Performance testing is mandatory:**
   - Real tests with Locust
   - Metric collection
   - Visualization

3. **GCP usage is mandatory:**
   - Must be GCP, not AWS!

4. **Budget control:**
   - Stay within $300
   - Active monitoring

5. **Reproducibility:**
   - Others should be able to set it up
   - README should be detailed

### ❌ Things NOT to Do:

1. **Just "hello world" functions:**
   - Cloud Functions should do real work

2. **Passive VMs:**
   - VMs should be necessary for the system

3. **Kubernetes without HPA:**
   - HPA is mandatory!

4. **AWS usage:**
   - GCP is mandatory!

5. **Budget overrun:**
   - $300 limit should not be exceeded

6. **Insufficient documentation:**
   - README should not be inadequate

---

## 📚 Summary: Project Requirements Checklist

### Mandatory Components:
- [ ] Kubernetes cluster (GKE)
- [ ] Containerized application (Docker)
- [ ] Kubernetes Deployments
- [ ] HPA (Horizontal Pod Autoscaler)
- [ ] Virtual Machines (Compute Engine) - functional
- [ ] Cloud Functions - active usage

### Performance Testing:
- [ ] Locust test scripts
- [ ] Test scenario design
- [ ] Metric collection (latency, throughput, CPU, memory, errors)
- [ ] Visualization (charts, graphs)

### Documentation:
- [ ] Cloud architecture diagram
- [ ] Component descriptions
- [ ] Deployment process (step-by-step)
- [ ] Locust experiment design
- [ ] Performance results visualization
- [ ] Results explanation
- [ ] Cost breakdown

### Deliverables:
- [ ] Working system on GCP
- [ ] Technical report (PDF/Markdown)
- [ ] Demo video (max 2 min)
- [ ] GitHub repository:
  - [ ] Application source code
  - [ ] Kubernetes YAMLs
  - [ ] VM setup scripts
  - [ ] Cloud Functions code
  - [ ] Locust test scripts
  - [ ] README.md (detailed)

### Bonus (Optional):
- [ ] Terraform infrastructure code
- [ ] Terraform documentation

---

## 🎯 Conclusion

This project offers an opportunity to apply **cloud-native architecture** concepts in practice. It's not just about writing code, but requires **complete cloud system design, deployment, and performance evaluation**.

**For Success:**
1. Integrate all mandatory components
2. Perform realistic performance tests
3. Prepare detailed documentation
4. Monitor budget
5. Ensure reproducibility

**Most Important Point:** The system must work **end-to-end** and be **scalable**!

---

*This analysis is based on CMPE 48A Term Project PDF requirements.*

