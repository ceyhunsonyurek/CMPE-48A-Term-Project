# Cloud Functions Implementation Plan

## 🎯 Requirement
**Mandatory:** Cloud Functions must be used with **active usage** (not just "hello world")

---

## ✅ Cloud Functions Kullanımı

### 1. **URL Redirect Cloud Function** ⭐ **PRIMARY**

**What:** Short URL'leri redirect eden Cloud Function

**Why:**
- ✅ En çok kullanılan endpoint (her short URL click'inde çalışır)
- ✅ High traffic → Serverless'in avantajı
- ✅ Fast response time gerekli
- ✅ Auto-scaling (unlimited)

**Implementation:**
```python
# cloud-functions/url-redirect/main.py
from flask import redirect
import pymysql
from hashids import Hashids
import os

def url_redirect(request):
    """
    HTTP Cloud Function to handle URL redirection
    Trigger: HTTP request to short URL
    """
    hashid = request.path.split('/')[-1]
    
    # Decode hashid to get url_id
    hashids = Hashids(min_length=4, salt="Divi")
    decoded = hashids.decode(hashid)
    
    if not decoded:
        return "Invalid URL", 404
    
    url_id = decoded[0]
    
    # Get original URL from MySQL (on VM)
    conn = pymysql.connect(
        host=os.getenv("DB_HOST"),
        port=int(os.getenv("DB_PORT", 3306)),
        user=os.getenv("DB_USER"),
        password=os.getenv("DB_PASSWORD"),
        database=os.getenv("DB_DATABASE")
    )
    
    cursor = conn.cursor()
    cursor.execute("SELECT original_url FROM urls WHERE id = %s", (url_id,))
    result = cursor.fetchone()
    
    if not result:
        return "URL not found", 404
    
    original_url = result[0]
    
    # Increment click count
    cursor.execute("UPDATE urls SET clicks = clicks + 1 WHERE id = %s", (url_id,))
    conn.commit()
    
    cursor.close()
    conn.close()
    
    # Redirect to original URL
    return redirect(original_url, code=302)
```

**Deployment:**
```bash
gcloud functions deploy url-redirect \
  --runtime python39 \
  --trigger-http \
  --allow-unauthenticated \
  --entry-point url_redirect \
  --set-env-vars DB_HOST=mysql-vm-ip,DB_PORT=3306,DB_USER=appuser,DB_PASSWORD=xxx,DB_DATABASE=urlshortener
```

**Usage:**
- Short URL: `https://your-domain.com/aB3d`
- Cloud Function URL: `https://us-central1-url-shortener-479913.cloudfunctions.net/url-redirect/aB3d`
- User clicks → Cloud Function → MySQL lookup → Redirect

**Why This is "Active Usage":**
- ✅ Core functionality (URL redirection)
- ✅ High traffic (every short URL click)
- ✅ Real database operations
- ✅ Click tracking (database update)

---

### 2. **Optional: Click Analytics Cloud Function** (Bonus)

**What:** Click statistics ve analytics için Cloud Function

**Why:**
- ✅ Additional Cloud Functions usage
- ✅ Demonstrates event-driven architecture
- ✅ Can be triggered by Pub/Sub (from URL redirect)

**Implementation:**
```python
# cloud-functions/click-analytics/main.py
from google.cloud import pubsub_v1
import json

def track_click(data, context):
    """
    Cloud Function triggered by Pub/Sub
    Processes click events for analytics
    """
    import base64
    import pymysql
    import os
    
    # Decode Pub/Sub message
    message_data = base64.b64decode(data['data']).decode('utf-8')
    click_data = json.loads(message_data)
    
    # Process analytics (store in database, aggregate, etc.)
    # ...
    
    return "OK", 200
```

**Usage:**
- URL redirect function → Publishes to Pub/Sub → Analytics function processes

---

## 📊 Cloud Functions Summary

| Function | Purpose | Trigger | Status |
|----------|---------|---------|--------|
| **url-redirect** | Short URL redirection | HTTP | ✅ **PRIMARY** |
| click-analytics | Click tracking/analytics | Pub/Sub | ⭐ Optional |

---

## 🎯 Final Architecture

```
User clicks short URL
    ↓
Cloud Function: url-redirect
    ↓
MySQL VM (lookup original URL)
    ↓
Increment click count
    ↓
HTTP 302 Redirect to original URL
```

**Flask App:**
- URL shortening (POST /)
- QR code generation (internal)
- User authentication
- Statistics dashboard

**Cloud Function:**
- URL redirection (GET /{hashid})
- Click tracking

---

## ✅ Requirements Met

1. ✅ **Cloud Functions used:** URL redirect function
2. ✅ **Active usage:** Core functionality, high traffic
3. ✅ **Not "hello world":** Real database operations, redirects
4. ✅ **Serverless pattern:** Auto-scaling, pay-per-use
5. ✅ **Event-driven:** Can add Pub/Sub triggers for analytics

---

## 🔄 Alternative: QR Generation as Cloud Function

If you want to use Cloud Functions for QR generation instead of internal:

**Pros:**
- ✅ Demonstrates Cloud Functions
- ✅ Isolated from main app
- ✅ Can scale independently

**Cons:**
- ❌ Network latency (~100-200ms)
- ❌ More complex (2 Cloud Functions to manage)
- ❌ QR generation is fast anyway (~50ms internal)

**Recommendation:** Keep QR internal, use Cloud Function for URL redirect (more traffic, better fit for serverless)

