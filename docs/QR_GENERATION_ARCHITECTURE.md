# QR Code Generation - Architecture Options

## 🎯 Requirement
- Replace Gradio API with Python `qrcode` library
- Internal implementation (no external dependencies)
- Determine best placement in cloud architecture

---

## 📊 Architecture Options Comparison

### Option 1: Direct in Flask App (Synchronous) ⭐ **RECOMMENDED**
**Placement:** Same Flask app, same pod, same endpoint

```
User Request → Flask /index → Generate QR → Upload GCS → Return Response
```

**Implementation:**
```python
# In app.py, index() route
def generate_qr_code(short_url, hashid):
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    temp_path = f"/tmp/{hashid}.png"
    img.save(temp_path)
    return temp_path

@application.route("/", methods=["POST"])
def index():
    # ... URL shortening logic ...
    if img_desc:  # Optional, QR always generated
        qr_path = generate_qr_code(short_url, hashid)
        gcs_url = upload_to_gcs(qr_path, gcs_bucket_name, f"{hashid}.png")
    return render_template("index.html", short_url=short_url, image_path=gcs_url)
```

**Pros:**
- ✅ Simplest implementation
- ✅ No additional infrastructure
- ✅ Fast (no network calls)
- ✅ No extra costs
- ✅ Works with HPA (scales with app)

**Cons:**
- ❌ Blocks request thread (but QR generation is fast ~50-100ms)
- ❌ CPU usage in app pods (minimal impact)

**Best For:** Current architecture, simple and efficient

---

### Option 2: Separate Endpoint in Flask App (Internal API)
**Placement:** Same Flask app, different route

```
User Request → Flask /index → Return immediately
              ↓
              Async: POST /api/generate-qr → Generate QR → Upload GCS
```

**Implementation:**
```python
@application.route("/api/generate-qr", methods=["POST"])
def generate_qr_endpoint():
    data = request.json
    short_url = data.get("short_url")
    hashid = data.get("hashid")
    
    qr_path = generate_qr_code(short_url, hashid)
    gcs_url = upload_to_gcs(qr_path, gcs_bucket_name, f"{hashid}.png")
    
    return {"status": "success", "qr_url": gcs_url}, 200

# In index() route:
if img_desc:
    # Fire and forget or poll
    requests.post(f"{request.host_url}api/generate-qr", 
                  json={"short_url": short_url, "hashid": hashid})
```

**Pros:**
- ✅ Separates concerns
- ✅ Can be called from multiple places
- ✅ Can add rate limiting separately

**Cons:**
- ❌ More complex (needs async handling)
- ❌ Still uses same resources
- ❌ Overkill for simple use case

**Best For:** If you need QR generation from multiple endpoints

---

### Option 3: Cloud Function (Serverless)
**Placement:** Separate GCP Cloud Function

```
User Request → Flask /index → Call Cloud Function → Generate QR → Upload GCS
```

**Implementation:**
```python
# cloud-functions/qr-generator/main.py
import qrcode
from google.cloud import storage
import tempfile

def generate_qr(request):
    data = request.get_json()
    short_url = data.get("short_url")
    hashid = data.get("hashid")
    bucket_name = data.get("bucket_name")
    
    # Generate QR
    qr = qrcode.QRCode(version=1, box_size=10, border=4)
    qr.add_data(short_url)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Upload to GCS
    temp_path = f"/tmp/{hashid}.png"
    img.save(temp_path)
    
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob(f"{hashid}.png")
    blob.upload_from_filename(temp_path)
    blob.make_public()
    
    return {"qr_url": blob.public_url}, 200
```

**Pros:**
- ✅ Serverless (pay per use)
- ✅ Scales independently
- ✅ Isolated from main app
- ✅ Good for Cloud Functions requirement

**Cons:**
- ❌ Network latency (~100-200ms)
- ❌ Cold start latency (first request)
- ❌ More complex deployment
- ❌ Additional cost (minimal)

**Best For:** If you want to demonstrate Cloud Functions usage

---

### Option 4: Separate Microservice in GKE
**Placement:** Separate Kubernetes Deployment

```
User Request → Flask /index → Service: qr-generator → Generate QR → Upload GCS
```

**Implementation:**
- Separate deployment `qr-generator-deployment.yaml`
- Separate service `qr-generator-service.yaml`
- Internal cluster communication

**Pros:**
- ✅ True microservice architecture
- ✅ Can scale independently
- ✅ Isolated from main app

**Cons:**
- ❌ Overkill for simple QR generation
- ❌ More complex (2 deployments to manage)
- ❌ Network overhead (internal but still)
- ❌ More resources (extra pods)

**Best For:** Large-scale systems with multiple services

---

## 🏆 Recommended Architecture

### **Option 1: Direct in Flask App** ⭐

**Why:**
1. **Simplicity:** QR generation is fast (~50-100ms), doesn't need async
2. **Performance:** No network latency, no cold starts
3. **Cost:** No additional infrastructure
4. **Scalability:** HPA scales the app pods, QR generation scales with it
5. **Maintainability:** One codebase, easier to debug

**Implementation Plan:**
1. Add `qrcode[pil]` to `requirements.txt`
2. Create `generate_qr_code()` function in `app.py`
3. Update `index()` route to use internal generation
4. Remove Gradio client dependency
5. Test and deploy

**Code Changes:**
```python
# requirements.txt
qrcode[pil]  # Add this

# app.py
import qrcode
import tempfile
import os

def generate_qr_code(short_url, hashid):
    """Generate QR code locally using qrcode library"""
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(short_url)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save to temp directory
    temp_dir = "/tmp"
    os.makedirs(temp_dir, exist_ok=True)
    temp_path = os.path.join(temp_dir, f"{hashid}.png")
    img.save(temp_path)
    
    return temp_path

# In index() route, replace Gradio client call:
# OLD:
# if img_desc and client:
#     result = client.predict(...)

# NEW:
# Always generate QR code (img_desc optional for future customization)
qr_path = generate_qr_code(short_url, hashid)
blob_name = f"{hashid}.png"
result = upload_to_gcs(qr_path, gcs_bucket_name, blob_name)
```

---

## 🔄 Alternative: Cloud Function (If You Want to Use Cloud Functions)

If you want to demonstrate Cloud Functions usage for the project requirement, **Option 3** is also valid:

**Pros:**
- ✅ Meets Cloud Functions requirement
- ✅ Shows serverless architecture
- ✅ Can be called from multiple places

**Trade-off:**
- Slight latency increase (~100-200ms)
- More complex deployment
- But still acceptable for project

**Recommendation:** Start with Option 1, move to Option 3 if you need Cloud Functions demonstration.

---

## 📝 Summary

| Option | Complexity | Performance | Cost | Best For |
|--------|-----------|-------------|------|----------|
| **1. Direct in Flask** | ⭐ Low | ⭐⭐⭐ Fast | ⭐ Free | **Recommended** |
| 2. Separate Endpoint | ⭐⭐ Medium | ⭐⭐⭐ Fast | ⭐ Free | Multiple callers |
| 3. Cloud Function | ⭐⭐ Medium | ⭐⭐ Medium | ⭐⭐ Low | Serverless demo |
| 4. Microservice | ⭐⭐⭐ High | ⭐⭐ Medium | ⭐⭐ Medium | Large scale |

**Final Recommendation:** **Option 1 (Direct in Flask App)** - Simple, fast, efficient, meets all requirements.

