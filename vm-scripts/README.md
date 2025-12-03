# VM Setup Scripts

This directory contains setup scripts for VM instances.

## MySQL VM Setup

### 1. SSH to MySQL VM

```bash
gcloud compute ssh mysql-vm --zone=us-east1-b
```

### 2. Upload and Run Setup Script

```bash
# From your local machine, copy script to VM
gcloud compute scp vm-scripts/setup-mysql.sh mysql-vm:~/ --zone=us-east1-b

# SSH to VM
gcloud compute ssh mysql-vm --zone=us-east1-b

# Make script executable
chmod +x setup-mysql.sh

# Run script
./setup-mysql.sh
```

### 3. Verify MySQL is Running

```bash
# On VM
sudo systemctl status mysql

# Test connection
mysql -u appuser -p urlshortener
# Password: urlshortener2024
```

### 4. Test Remote Connection

From your local machine (or GKE pod):
```bash
# Test connection (replace with VM internal IP)
mysql -h 10.142.0.15 -u appuser -p urlshortener
```

## Database Credentials

- **Database:** `urlshortener`
- **User:** `appuser`
- **Password:** `urlshortener2024`
- **Host:** `10.142.0.15` (internal IP) or `34.148.55.158` (external IP)

**Note:** Update `k8s/secret.yaml` with the password before deploying to Kubernetes.

