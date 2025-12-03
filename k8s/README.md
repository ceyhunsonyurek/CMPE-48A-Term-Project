# Kubernetes Deployment Manifests

This directory contains Kubernetes manifests for deploying the URL Shortener application to GKE.

## Files

- `deployment.yaml` - Main application deployment with 2 replicas
- `service.yaml` - LoadBalancer service for external access
- `configmap.yaml` - Non-sensitive configuration
- `secret.yaml` - Sensitive data (database credentials, secret keys)

## Prerequisites

1. GKE cluster created and `kubectl` configured
2. Artifact Registry image pushed
3. MySQL VM created (for DB_HOST)
4. GCS bucket created (for GCS_BUCKET_NAME)

## Setup Instructions

### 1. Update ConfigMap

Edit `configmap.yaml` and set:
- `GCS_BUCKET_NAME`: Your GCS bucket name
- `DB_HOST`: MySQL VM internal IP address

### 2. Update Secrets

**IMPORTANT:** Update `secret.yaml` with your actual values:
- `DB_PASSWORD`: MySQL database password
- `SECRET_KEY`: Strong random string for Flask sessions

Generate a secret key:
```bash
python3 -c "import secrets; print(secrets.token_hex(32))"
```

### 3. Apply Manifests

```bash
# Apply ConfigMap
kubectl apply -f k8s/configmap.yaml

# Apply Secrets
kubectl apply -f k8s/secret.yaml

# Apply Deployment
kubectl apply -f k8s/deployment.yaml

# Apply Service
kubectl apply -f k8s/service.yaml
```

### 4. Verify Deployment

```bash
# Check pods
kubectl get pods -l app=url-shortener

# Check service
kubectl get service url-shortener-service

# Check logs
kubectl logs -l app=url-shortener --tail=50

# Get external IP
kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
```

### 5. Test Health Endpoint

```bash
# Get service external IP
EXTERNAL_IP=$(kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')

# Test health endpoint
curl http://$EXTERNAL_IP/health
```

## Updating Configuration

### Update ConfigMap
```bash
kubectl edit configmap url-shortener-config
# Or
kubectl apply -f k8s/configmap.yaml
# Then restart pods
kubectl rollout restart deployment url-shortener
```

### Update Secrets
```bash
kubectl edit secret url-shortener-secrets
# Or recreate secret
kubectl delete secret url-shortener-secrets
kubectl apply -f k8s/secret.yaml
kubectl rollout restart deployment url-shortener
```

## Troubleshooting

### Pods not starting
```bash
# Check pod status
kubectl describe pod <pod-name>

# Check logs
kubectl logs <pod-name>
```

### Image pull errors
- Verify image exists in Artifact Registry
- Check GKE cluster has access to Artifact Registry
- Verify image pull secrets if needed

### Database connection errors
- Verify DB_HOST is correct (MySQL VM IP)
- Check firewall rules (GKE → MySQL VM port 3306)
- Verify database credentials in secrets

### GCS access errors
- Verify GCS bucket exists
- Check GKE service account has Storage Object Admin role
- Or set up Workload Identity

## Scaling

```bash
# Scale manually
kubectl scale deployment url-shortener --replicas=3

# Or use HPA (see hpa.yaml)
kubectl apply -f k8s/hpa.yaml
```

## 5. Horizontal Pod Autoscaler (HPA)

HPA automatically scales the number of pods based on CPU and memory usage.

### Deploy HPA

```bash
kubectl apply -f k8s/hpa.yaml
```

### Verify HPA

```bash
# Check HPA status
kubectl get hpa url-shortener-hpa

# Watch HPA in real-time
kubectl get hpa url-shortener-hpa -w

# Describe HPA for detailed information
kubectl describe hpa url-shortener-hpa
```

### HPA Configuration

- **Min Replicas:** 2 (always maintain at least 2 pods)
- **Max Replicas:** 10 (can scale up to 10 pods)
- **CPU Threshold:** 70% (scale up if average CPU > 70%)
- **Memory Threshold:** 80% (scale up if average memory > 80%)

### Test HPA

1. **Generate Load:**
   ```bash
   # Get external IP
   EXTERNAL_IP=$(kubectl get service url-shortener-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
   
   # Generate load (install hey: brew install hey)
   hey -n 10000 -c 50 http://$EXTERNAL_IP/
   ```

2. **Watch Scaling:**
   ```bash
   # In another terminal
   kubectl get hpa url-shortener-hpa -w
   kubectl get pods -w
   ```

### Troubleshooting

**HPA shows `<unknown>` metrics:**
- GKE clusters usually have metrics-server pre-installed
- If metrics not available, check:
  ```bash
  kubectl get apiservice | grep metrics
  kubectl top nodes  # Should show CPU/memory usage
  ```

**HPA not scaling:**
- Ensure deployment has resource requests/limits (already configured)
- Check HPA events: `kubectl describe hpa url-shortener-hpa`

## Cleanup

```bash
# Delete all resources
kubectl delete -f k8s/
```

