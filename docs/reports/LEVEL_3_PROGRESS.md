# Level 3: VM and Database Setup - Progress Report

## Overview
**Duration:** 1 Week  
**Difficulty:** Medium-Hard  
**Status:** ✅ **COMPLETED** (3.1, 3.2) | ⏸️ **DEFERRED** (3.3)

---

## 3.1 MySQL Database VM Setup

### What Was Needed
- Create Compute Engine VM instance for MySQL database
- Install and configure MySQL server
- Create database schema (users, urls tables)
- Configure remote access from GKE cluster
- Set up firewall rules

### What Was Done
- Created VM instance:
  - Name: `mysql-vm`
  - Zone: `us-east1-b`
  - Machine type: `e2-small`
  - Image: Ubuntu 22.04 LTS
  - Internal IP: `10.142.0.15`
  - External IP: `34.148.55.158`
- Created firewall rule: `allow-mysql-from-gke`
  - Allows TCP port 3306 from GKE cluster (10.0.0.0/8)
  - Target tag: `mysql-server`
- Created setup script: `vm-scripts/setup-mysql.sh`
  - Installs MySQL Server
  - Configures MySQL for remote connections (`bind-address = 0.0.0.0`)
  - Creates database: `urlshortener`
  - Creates user: `appuser` with password `urlshortener2024`
  - Creates tables: `users`, `urls`
- Executed setup script on VM
- Verified database and tables created
- Tested connection from Kubernetes pod

### Issues Encountered
- None - setup script executed successfully on first attempt

### Solution
- N/A

---

## 3.2 Network Configuration

### What Was Needed
- Configure network connectivity between GKE and MySQL VM
- Set up firewall rules for secure communication
- Verify network connectivity

### What Was Done
- Used default VPC network (sufficient for project)
- Created firewall rule for MySQL access:
  - Source: GKE cluster IP range (10.0.0.0/8)
  - Destination: MySQL VM (tag: mysql-server)
  - Port: 3306
- Verified connectivity:
  - Tested MySQL connection from Kubernetes pod
  - Connection successful from GKE to MySQL VM

### Issues Encountered
- None - default VPC network worked correctly

### Solution
- N/A

---

## 3.3 Redis Cache VM (Deferred)

### What Was Needed
- Create Redis VM for session store and caching
- Integrate Redis with Flask application

### What Was Done
- **Status:** ⏸️ **DEFERRED**
- Decision: Evaluate after Locust performance tests
- May not be necessary if current session management works

### Issues Encountered
- N/A (not implemented yet)

### Solution
- Will be evaluated after performance testing to determine if needed

---

## Integration with Kubernetes

### What Was Done
- Updated `k8s/configmap.yaml`:
  - Set `DB_HOST` to MySQL VM internal IP: `10.142.0.15`
- Updated `k8s/secret.yaml`:
  - Set `DB_PASSWORD` to MySQL password: `urlshortener2024`
- Applied updated ConfigMap and Secret to cluster
- Verified pods can connect to MySQL VM

### Issues Encountered
- None - connection worked immediately after configuration

### Solution
- N/A

---

## Summary

**Completed Tasks:**
- ✅ MySQL VM created and configured
- ✅ Database schema created (users, urls tables)
- ✅ Firewall rules configured
- ✅ Network connectivity verified
- ✅ Kubernetes integration completed

**Deferred Tasks:**
- ⏸️ Redis Cache VM (evaluate after performance tests)

**Key Achievements:**
- Functional database server on VM (meets project requirement)
- Secure network configuration
- Successful integration between GKE and VM
- Database ready for application use

**Time Spent:** ~1-2 days  
**Files Created:** `vm-scripts/setup-mysql.sh`, `vm-scripts/README.md`

**VM Details:**
- **VM Name:** mysql-vm
- **Internal IP:** 10.142.0.15
- **Database:** urlshortener
- **User:** appuser
- **Tables:** users, urls

