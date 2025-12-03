# Level 4.1: URL Redirect Cloud Function - Progress Report

## Overview
**Duration:** 2-3 Days  
**Difficulty:** Hard  
**Status:** ✅ **COMPLETED**

---

## What Was Needed
- Create Cloud Function to handle URL redirection
- Move redirect logic from Flask app to serverless function
- Implement click tracking in Cloud Function
- Integrate Cloud Function with existing MySQL database (on VM)
- Make Flask app redirect route optional (backward compatibility)

---

## What Was Done

### 4.1.1 Cloud Function Code Creation

**Created Files:**
- `cloud-functions/url-redirect/main.py` - Main Cloud Function code
- `cloud-functions/url-redirect/requirements.txt` - Python dependencies
- `cloud-functions/url-redirect/README.md` - Deployment documentation

**Implementation:**
- Converted Flask `url_redirect()` route logic to Cloud Function format
- Function accepts Flask request object
- Extracts hashid from request path
- Decodes hashid using Hashids (same salt as Flask app)
- Queries MySQL database for original URL
- Increments click count
- Returns HTTP 302 redirect response

**Code Flow:**
```
1. Extract hashid from request path (e.g., "Eq60")
2. Decode hashid → url_id (e.g., 1)
3. Query MySQL: SELECT original_url, clicks FROM urls WHERE id = url_id
4. Update clicks: UPDATE urls SET clicks = clicks + 1 WHERE id = url_id
5. Return HTTP 302 redirect to original_url
```

---

### 4.1.2 Cloud Function Deployment

**Prerequisites:**
- Enabled Cloud Run API (required for Gen2 Functions)
- Enabled Cloud Functions API
- Enabled Cloud Build API

**Deployment Command:**
```bash
gcloud functions deploy url-redirect \
  --gen2 \
  --runtime python311 \
  --region us-east1 \
  --source . \
  --entry-point url_redirect \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars DB_HOST=...,DB_PORT=3306,DB_USER=...,DB_PASSWORD=...,DB_DATABASE=urlshortener,SECRET_KEY=... \
  --memory 256MB \
  --timeout 30s
```

**Deployment Configuration:**
- **Runtime:** Python 3.11
- **Region:** us-east1 (same as MySQL VM for low latency)
- **Memory:** 256MB
- **Timeout:** 30s (increased from 10s for database operations)
- **Trigger:** HTTP (public access)
- **Environment Variables:** Database credentials and Flask secret key

**Deployed Function URL:**
- `https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect`
- Service URL: `https://url-redirect-gl2gf6oisa-ue.a.run.app`

---

### 4.1.3 Network Configuration Issues

**Problem 1: Initial Deployment Error**
```
ERROR: API run.googleapis.com is not enabled
```

**Solution:**
- Enabled Cloud Run API: `gcloud services enable run.googleapis.com`
- Cloud Functions Gen2 uses Cloud Run under the hood

**Problem 2: Database Connectivity**
- **Issue:** Cloud Function couldn't connect to MySQL VM
- **Root Cause:** MySQL VM uses internal IP (`10.142.0.15`) which is only accessible from VPC
- **Initial Error:** HTTP 504 Gateway Timeout

**Attempted Solutions:**

1. **VPC Connector (Preferred):**
   ```bash
   gcloud compute networks vpc-access connectors create url-redirect-connector \
     --region=us-east1 \
     --network=default \
     --range=10.8.0.0/28
   ```
   - **Result:** Failed with "Forbidden" error (likely quota/permission issue)

2. **External IP (Temporary Workaround):**
   - Used MySQL VM external IP: `34.148.55.158`
   - Created firewall rule: `allow-mysql-from-cloud-functions`
   - Allows TCP port 3306 from all IPs (0.0.0.0/0)
   - **Security Note:** This is a temporary solution. Production should use VPC Connector.

**Final Solution:**
- Updated Cloud Function environment variable: `DB_HOST=34.148.55.158`
- Redeployed function
- Function successfully connects to MySQL VM

---

### 4.1.4 Testing and Verification

**Test Setup:**
1. Created test data in database:
   - URL ID: 1
   - Original URL: `https://www.google.com`
   - Hashid: `Eq60` (hashids.encode(1))

2. Tested Cloud Function:
   ```bash
   curl -I https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect/Eq60
   ```

**Results:**
- ✅ HTTP 302 redirect returned
- ✅ Location header points to original URL
- ✅ Click count incremented in database (verified: 1 → 2)
- ✅ Function logs show successful execution

**Verification:**
```bash
# Check click count
gcloud compute ssh mysql-vm --zone=us-east1-b \
  --command="sudo mysql -u appuser -purlshortener2024 urlshortener \
  -e 'SELECT id, original_url, clicks FROM urls WHERE id=1;'"
```

---

### 4.1.5 Flask App Integration

**Changes Made:**
- Updated `app/app.py` `url_redirect()` route to be optional
- Added environment variable check: `USE_CLOUD_FUNCTION_REDIRECT`
- If enabled, Flask route redirects to Cloud Function
- Maintains backward compatibility for local development

**Code Changes:**
```python
@application.route("/<id>")
def url_redirect(id):
    use_cloud_function = os.getenv("USE_CLOUD_FUNCTION_REDIRECT", "false").lower() == "true"
    cloud_function_url = os.getenv("CLOUD_FUNCTION_REDIRECT_URL", "")
    
    if use_cloud_function and cloud_function_url:
        return redirect(f"{cloud_function_url}/{id}", code=302)
    else:
        # Fallback to Flask app redirect (local development)
        ...
```

**Kubernetes ConfigMap Update:**
- Added `USE_CLOUD_FUNCTION_REDIRECT: "true"`
- Added `CLOUD_FUNCTION_REDIRECT_URL: "https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect"`

---

## Issues Encountered

### Issue 1: Cloud Run API Not Enabled
**Error:** `API run.googleapis.com is not enabled`  
**Solution:** Enabled Cloud Run API via `gcloud services enable run.googleapis.com`

### Issue 2: Database Connectivity (504 Timeout)
**Error:** HTTP 504 Gateway Timeout when accessing Cloud Function  
**Root Cause:** Cloud Function couldn't reach MySQL VM internal IP (10.142.0.15)  
**Solution:** Used external IP temporarily (34.148.55.158) with firewall rule

### Issue 3: VPC Connector Creation Failed
**Error:** `Operation failed: Forbidden` when creating VPC connector  
**Possible Causes:** Quota limits, permission issues, or free tier restrictions  
**Workaround:** Using external IP (not ideal for production)

---

## Solutions Implemented

1. **API Enablement:** Enabled required GCP APIs (Cloud Run, Cloud Functions, Cloud Build)
2. **Network Configuration:** Used external IP for MySQL VM (temporary solution)
3. **Firewall Rules:** Created rule to allow MySQL access from Cloud Functions
4. **Environment Variables:** Configured database credentials in Cloud Function
5. **Flask Integration:** Made redirect route optional with environment variable control

---

## Summary

**Completed Tasks:**
- ✅ Cloud Function code created and deployed
- ✅ Database connectivity established (via external IP)
- ✅ URL redirection working correctly
- ✅ Click tracking functional
- ✅ Flask app integration completed
- ✅ Testing and verification done

**Key Achievements:**
- Serverless URL redirection implemented
- Automatic scaling for redirect traffic
- Cost-efficient solution (pay per use)
- Separation of concerns (redirect logic independent)

**Current Limitations:**
- ⚠️ Using external IP for MySQL (security risk)
- ⚠️ Firewall rule too permissive (allows all IPs)
- ⚠️ VPC Connector not implemented (quota/permission issues)

**Production Recommendations:**
1. Implement VPC Connector for secure internal communication
2. Restrict firewall rules to Cloud Function IP ranges only
3. Use internal IP for MySQL VM
4. Consider removing Flask redirect route entirely

**Time Spent:** ~2-3 days  
**Files Created:** `cloud-functions/url-redirect/main.py`, `requirements.txt`, `README.md`  
**Files Modified:** `app/app.py`, `k8s/configmap.yaml`

**Function URL:** `https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect`

