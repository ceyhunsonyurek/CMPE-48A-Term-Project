# Database Schema and Data Flow

## 📊 Database Tables

### 1. `users` Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL
);
```

**Stored Data:**
- `id`: User ID (auto increment)
- `username`: Username (unique)
- `password`: Password (⚠️ **plain text**, not hashed!)

**Example:**
```
id | username | password
1  | testuser | testpass123
```

---

### 2. `urls` Table
```sql
CREATE TABLE urls (
    id INT PRIMARY KEY AUTO_INCREMENT,
    original_url TEXT NOT NULL,
    user_id INT NOT NULL,
    clicks INT DEFAULT 0,
    created DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id)
);
```

**Stored Data:**
- `id`: URL ID (auto increment) - **Used to generate short URL**
- `original_url`: Original URL to be shortened (e.g., "https://www.google.com")
- `user_id`: Which user owns this URL
- `clicks`: Number of times clicked (click tracking)
- `created`: Creation timestamp

**Example:**
```
id | original_url              | user_id | clicks | created
1  | https://www.google.com    | 1       | 5      | 2025-12-03 17:00:00
2  | https://github.com        | 1       | 2      | 2025-12-03 17:05:00
```

---

## 🔑 How Short URLs Are Generated

### **Short URLs Are NOT Stored in Database!**

**Logic:**
1. URL is saved to database → `url_id` is retrieved (e.g., `1`)
2. `url_id` → Encoded using Hashids → `hashid` (e.g., `"Eq60"`)
3. Short URL is created: `http://host/Eq60`

**Code:**
```python
def get_short_url(url_id):
    hashid = hashids.encode(url_id)  # 1 → "Eq60"
    short_url = request.host_url + hashid  # "http://localhost:5000/Eq60"
    return short_url, hashid
```

**Why This Approach?**
- ✅ **No database storage needed** - Saves space
- ✅ **Always derivable** - Can be generated from `url_id` anytime
- ✅ **Deterministic** - Same `url_id` + `SECRET_KEY` = same hashid
- ✅ **No redundancy** - Don't store what can be computed

**Decode Process (during redirect):**
```python
hashid = "Eq60"
decoded = hashids.decode(hashid)  # [1]
url_id = decoded[0]  # 1
# Query database with url_id=1 to get original_url
```

**Why Not Store Short URL?**
1. **Storage Efficiency:** Short URLs are redundant - they can always be generated from `url_id`
2. **Data Consistency:** If stored, we'd need to update it if `SECRET_KEY` changes
3. **Simplicity:** One less field to manage and maintain
4. **Flexibility:** Can change short URL format without database migration

---

## 🖼️ Where QR Code Images Are Stored

### **QR Code Images Are NOT Stored in Database!**

**Logic:**
1. QR code is generated (using Python `qrcode` library)
2. Saved as temporary file: `/tmp/{hashid}.png`
3. **Uploaded to Google Cloud Storage (GCS)**
4. Temporary file is deleted

**Code:**
```python
# 1. Generate QR code
qr_path = generate_qr_code(short_url, hashid)  # /tmp/Eq60.png

# 2. Upload to GCS
blob_name = f"{hashid}.png"  # "Eq60.png"
result = upload_to_gcs(qr_path, gcs_bucket_name, blob_name)
# → https://storage.googleapis.com/url-shortener-assets/Eq60.png

# 3. Delete temporary file
os.remove(qr_path)
```

**GCS Bucket:**
- Bucket name: `url-shortener-assets`
- File naming: `{hashid}.png` (e.g., `Eq60.png`)
- Public URL: `https://storage.googleapis.com/url-shortener-assets/Eq60.png`

**Why GCS Instead of Database?**
1. **Scalability:** Can store millions of QR codes without database bloat
2. **Performance:** Object storage is optimized for binary files (images)
3. **Cost:** GCS is cheaper than database storage for large files
4. **CDN Support:** GCS can be used with CDN for fast global access
5. **Database Size:** Storing images in database would make it huge and slow
6. **Separation of Concerns:** Database for structured data, GCS for files

**Why Not Store QR Code Path in Database?**
1. **Predictable Path:** QR code path can always be derived from `hashid`
   - Path: `https://storage.googleapis.com/{bucket}/{hashid}.png`
   - No need to store what can be computed
2. **Consistency:** If bucket name changes, we'd need to update all records
3. **Simplicity:** One less field to manage
4. **Flexibility:** Can change storage location without database migration

---

## 📝 Complete Data Flow

### **URL Shortening Flow:**
```
1. User enters URL → Flask app
2. Save to database → INSERT INTO urls
   → url_id = 1 (auto increment)
3. Hashids encode → hashid = "Eq60"
4. Create short URL → "http://host/Eq60"
5. Generate QR code → /tmp/Eq60.png
6. Upload to GCS → gs://url-shortener-assets/Eq60.png
7. Get public URL → https://storage.googleapis.com/.../Eq60.png
8. Display to user → short_url + image_path
```

### **URL Redirect Flow:**
```
1. User clicks short URL → http://host/Eq60
2. Hashids decode → "Eq60" → url_id = 1
3. Query database → SELECT * FROM urls WHERE id=1
   → original_url = "https://www.google.com"
4. Increment clicks → UPDATE urls SET clicks=clicks+1 WHERE id=1
5. Redirect → HTTP 302 → https://www.google.com
```

### **QR Code Access Flow:**
```
1. Need QR code for hashid "Eq60"
2. Construct URL: https://storage.googleapis.com/url-shortener-assets/Eq60.png
3. GCS serves the image (no database query needed)
```

---

## ❓ Frequently Asked Questions

### **Q: Why don't we store short URLs in the database?**
**A:** Short URLs are **deterministic** - they can always be generated from `url_id` using Hashids. Storing them would be redundant and waste database space. If we stored them, we'd need to update all records if `SECRET_KEY` changes.

### **Q: Why don't we store QR code image paths in the database?**
**A:** QR code paths are **predictable** - they follow the pattern `{bucket}/{hashid}.png`. Since `hashid` is already derivable from `url_id`, we can always construct the path. Storing it would be redundant and create maintenance overhead.

### **Q: What if hashid changes?**
**A:** Hashid is generated from `url_id` + `SECRET_KEY`. If `SECRET_KEY` changes, all hashids change, but we can regenerate them. If we stored hashids, we'd need to update all records.

### **Q: How do we find the QR code?**
**A:** From hashid: `https://storage.googleapis.com/{bucket}/{hashid}.png`. Since hashid is derivable from `url_id`, we can always construct the path.

### **Q: What is actually stored in the database?**
**A:** 
- ✅ `original_url`: The URL to be shortened
- ✅ `user_id`: Which user owns this URL
- ✅ `clicks`: Click tracking counter
- ✅ `created`: Creation timestamp
- ❌ `short_url`: **NOT stored** (derived from `url_id`)
- ❌ `hashid`: **NOT stored** (derived from `url_id` + `SECRET_KEY`)
- ❌ `qr_code_path`: **NOT stored** (derived from `hashid` + bucket name)

---

## 🔍 Current Database State

**Check database:**
```bash
# Users
gcloud compute ssh mysql-vm --zone=us-east1-b \
  --command="sudo mysql -u appuser -purlshortener2024 urlshortener \
  -e 'SELECT * FROM users;'"

# URLs
gcloud compute ssh mysql-vm --zone=us-east1-b \
  --command="sudo mysql -u appuser -purlshortener2024 urlshortener \
  -e 'SELECT * FROM urls;'"
```

**Check GCS bucket:**
```bash
gsutil ls gs://url-shortener-assets/
```

---

## 📊 Design Principles

### **1. Normalization (Database)**
- Store only essential, non-derivable data
- Avoid redundancy
- Keep database lean and fast

### **2. Computability (Application Logic)**
- Derive values that can be computed
- Use deterministic algorithms (Hashids)
- Maintain single source of truth

### **3. Separation of Concerns (Storage)**
- Database: Structured, relational data
- Object Storage (GCS): Binary files, images
- Each storage type optimized for its purpose

### **4. Scalability**
- Database stays small (no large files)
- Object storage scales independently
- No performance degradation as data grows
