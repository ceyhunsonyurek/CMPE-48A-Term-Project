# CMPE-48A Term Project - Detailed Architecture Analysis

## 📋 Project Summary

This project is a Flask web application that performs **URL shortening and QR code generation**. Users can shorten their URLs, create customized QR codes for these URLs, and track click statistics.

---

## 🏗️ General Architecture

### Architecture Type: **Monolithic Web Application (Traditional 3-Tier Architecture)**

```
┌─────────────────────────────────────────────────────────┐
│                    CLIENT LAYER                          │
│  (Web Browser - HTML/CSS/JavaScript/Bootstrap)          │
└────────────────────┬────────────────────────────────────┘
                     │ HTTP/HTTPS
┌────────────────────▼────────────────────────────────────┐
│                 APPLICATION LAYER                        │
│  Flask Web Server (Python)                              │
│  - Session Management                                    │
│  - URL Routing                                           │
│  - Business Logic                                        │
└────┬──────────────┬──────────────┬───────────────────────┘
     │              │              │
     │              │              │
┌────▼────┐  ┌──────▼──────┐  ┌───▼──────────────┐
│  MySQL  │  │  AWS S3     │  │  Gradio Client   │
│ Database│  │  (Storage)  │  │  (AI Service)    │
└─────────┘  └─────────────┘  └──────────────────┘
```

---

## 🔧 Technology Stack

### Backend Framework
- **Flask** (Python Web Framework)
  - Simple, lightweight web framework
  - Session-based authentication
  - Template rendering (Jinja2)

### Database
- **MySQL** (with PyMySQL driver)
  - Relational database
  - Stores user and URL data

### Cloud Services
- **AWS S3** (Simple Storage Service)
  - Stores QR code images
  - Static file hosting
  - Integration with Boto3 SDK

### AI/ML Service
- **Gradio Client**
  - Connects to an external Gradio endpoint
  - Uses AI model for QR code generation
  - Endpoint provided from Kaggle notebook

### Frontend
- **Bootstrap 4.3.1** (CSS Framework)
- **Plotly** (Charting library - for statistics)
- **jQuery** (JavaScript library)

### Other Libraries
- **Hashids**: Converts URL IDs to short hashes
- **Plotly**: Creates statistical charts

---

## 📊 Database Schema

### `users` Table
```sql
CREATE TABLE users (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(255) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL  -- ⚠️ WARNING: Passwords are plain text!
);
```

### `urls` Table
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

**Relationships:**
- `urls.user_id` → `users.id` (Many-to-One)
- One user can create multiple URLs

---

## 🔄 Application Flow and Business Logic

### 1. User Registration and Login

**Registration Flow:**
```
1. User navigates to /register page
2. Enters username, password, confirm_password
3. Flask backend:
   - Validation check (empty fields, password match)
   - Username check in MySQL (duplicate check)
   - INSERT INTO users for new user
   - Session not created, redirected to login
```

**Login Flow:**
```
1. User navigates to /login page
2. Enters username and password
3. Flask backend:
   - User query in MySQL (SELECT)
   - If match, set session["user_id"] and session["username"]
   - Redirect to /index page
```

**⚠️ Security Issues:**
- Passwords stored as **plain text** (not hashed!)
- SQL injection risk exists (though parameterized queries are used)
- Weak session security (SECRET_KEY hardcoded)

### 2. URL Shortening and QR Code Generation

**Main Workflow:**
```
1. User enters URL and image description on /index page
2. POST request → Flask backend:
   
   a) URL Registration:
      - insert_url() function called
      - INSERT INTO urls (original_url, user_id) in MySQL
      - url_id = cursor.lastrowid retrieved
   
   b) Short URL Creation:
      - get_short_url() function
      - Hashids.encode(url_id) → short hash (e.g., "aB3d")
      - short_url = "http://host/aB3d" format
   
   c) QR Code Generation (optional):
      - If image_description exists:
        * Request sent to Gradio client
        * client.predict(short_url, img_desc, negative_prompt)
        * AI model generates QR code image
        * Image file path returned
   
   d) S3 Upload:
      - upload_to_s3() function
      - Upload to S3 using Boto3 SDK
      - File name: "{hashid}.png"
      - S3 URL: "https://{bucket_name}.s3.eu-north-1.amazonaws.com/{hashid}.png"
   
   e) Response:
      - short_url and image_path sent to template
      - Displayed to user
```

**Hashids Usage:**
- `Hashids(min_length=4, salt="Divi")`
- Converts URL ID to short, URL-safe hash
- Example: `url_id=1` → `hash="aB3d"` → `short_url="http://localhost:5000/aB3d"`

### 3. URL Redirection and Click Tracking

**Redirection Flow:**
```
1. User clicks short URL: /<id> (e.g., /aB3d)
2. Flask route: url_redirect(id)
   
   a) Hash Decode:
      - hashids.decode(id) → [url_id]
      - If invalid → error
   
   b) Database Query:
      - SELECT original_url, clicks FROM urls WHERE id = url_id
      - If not found → error
   
   c) Click Increment:
      - UPDATE urls SET clicks = clicks + 1 WHERE id = url_id
      - Transaction commit
   
   d) Redirection:
      - redirect(original_url) → user redirected to original URL
```

### 4. Statistics Page

**Stats Flow:**
```
1. User navigates to /stats page
2. Flask backend:
   
   a) Data Retrieval:
      - SELECT id, created, original_url, clicks FROM urls WHERE user_id = ?
      - All user's URLs retrieved
   
   b) Data Processing:
      - Calculate short_url for each URL
      - Aggregate clicks data
      - Calculate total URLs, total clicks, average
   
   c) Chart Creation:
      - Bar chart with Plotly (click count)
      - Pie chart with Plotly (distribution)
      - Convert to HTML format
   
   d) Template Render:
      - Data sent to stats.html template
      - Charts and table displayed
```

---

## ☁️ Cloud Integration

### AWS S3 Usage

**Configuration:**
```python
s3 = boto3.client(
    "s3",
    aws_access_key_id=aws_access_key_id,
    aws_secret_access_key=aws_secret_access_key,
)
```

**Use Cases:**
1. **QR Code Images:**
   - Generated QR code images uploaded to S3
   - File name: `{hashid}.png`
   - Public URL: `https://{bucket_name}.s3.eu-north-1.amazonaws.com/{hashid}.png`

2. **Static Files:**
   - Login page background image: `Background.jpeg`
   - Loading animation: `Loading_Animation.gif`
   - These files are used like a CDN from S3

**S3 Region:**
- `eu-north-1` (Stockholm, Sweden)

**Security:**
- Access keys stored in `config.json` file (⚠️ risky!)
- Bucket policies not specified in code
- Public read access required (for images)

---

## 🤖 AI/ML Integration

### Gradio Client Usage

**Configuration:**
```python
client_uri = input("Enter the Generative Endpoint: ")
client = Client(client_uri)
```

**Operation:**
- Endpoint obtained from user at application startup
- Gradio endpoint from Kaggle notebook is used
- QR code content and image description sent
- AI model generates customized QR code image

**API Call:**
```python
result = client.predict(
    f"{short_url}",           # QR Code Content
    f"{img_desc}",            # Prompt (image description)
    "ugly, disfigured...",    # Negative Prompt
    fn_index=0,
)
```

**Note:** This is an **external service** call, does not run on the application's own server.

---

## 🚫 Missing Cloud Technologies

### ❌ Kubernetes (K8s)
- **Status:** Not used
- **Why It Might Be Needed:**
  - Container orchestration
  - Auto-scaling
  - Load balancing
  - Rolling updates
- **Current State:** Single Flask application, no containerization

### ❌ Docker
- **Status:** No Dockerfile, no containerization
- **Why Needed:**
  - Application isolation
  - Deployment ease
  - Environment consistency

### ❌ Virtual Machines (EC2, GCE, etc.)
- **Status:** No VM reference in code
- **Note:** Application might be running on a VM, but not at code level

### ❌ Serverless Functions (Lambda, Cloud Functions)
- **Status:** Not used
- **Current State:** Traditional Flask server (long-running process)
- **Why It Could Be Used:**
  - URL redirection could be serverless
  - QR code generation could be async

### ❌ GCP (Google Cloud Platform)
- **Status:** Not used
- **Only AWS S3 is used**

### ❌ Load Balancer
- **Status:** Not in code
- **Current:** Single instance, single Flask server

### ❌ Auto-scaling
- **Status:** None
- **Current:** Static deployment

### ❌ CDN (Content Delivery Network)
- **Status:** S3 used directly, no CDN like CloudFront
- **Note:** S3 itself is global, but no CDN optimization

### ❌ Database as a Service (RDS, Cloud SQL)
- **Status:** MySQL used but not a managed service
- **Note:** `db_host` comes from config, likely manual setup

### ❌ Message Queue (SQS, Pub/Sub)
- **Status:** None
- **Why It Might Be Needed:**
  - QR code generation could be async
  - Background job processing

### ❌ Caching (Redis, ElastiCache)
- **Status:** None
- **Why Needed:**
  - Caching frequently used URLs
  - Session storage (currently using Flask session)

---

## 🔐 Security Analysis

### ⚠️ Identified Security Issues:

1. **Password Security:**
   - Passwords stored as plain text
   - No hashing (bcrypt, argon2, etc.)
   - **Risk:** All passwords exposed in database breach

2. **Secret Key:**
   - `SECRET_KEY = "Divi"` hardcoded
   - Should be environment variable in production
   - **Risk:** Session hijacking

3. **SQL Injection:**
   - Parameterized queries used (good)
   - But should check if string concatenation risk exists anywhere

4. **Config File:**
   - `config.json` should not be committed to git
   - Should be added to `.gitignore`
   - AWS credentials exposed

5. **HTTPS:**
   - No HTTPS requirement in code
   - SSL/TLS required in production

6. **CORS:**
   - CORS policy not defined
   - Cross-origin requests not controlled

---

## 📈 Scalability Analysis

### Current Limitations:

1. **Single Instance:**
   - Flask application runs on single server
   - Becomes bottleneck under high traffic

2. **Database:**
   - Single MySQL instance
   - No replication
   - No connection pooling (new connection per request)

3. **Session Storage:**
   - Flask default session (memory-based)
   - Problem with multiple instances
   - External session store like Redis needed

4. **Synchronous Processing:**
   - QR code generation is synchronous
   - Long-running operations block requests

### Scalability Improvements:

1. **Horizontal Scaling:**
   - Multiple Flask instances
   - Load balancer (ALB, NLB)
   - Session store (Redis)

2. **Database:**
   - Read replicas
   - Connection pooling (SQLAlchemy)
   - Caching layer (Redis)

3. **Async Processing:**
   - QR code generation should be background job
   - Message queue (SQS, RabbitMQ)
   - Worker processes

4. **CDN:**
   - CloudFront or similar
   - Static asset caching

---

## 🗂️ File Structure

```
CMPE-48A-Term-Project/
├── app.py                 # Main Flask application (281 lines)
├── init_db.py            # Database init script (not used, commented out)
├── requirements.txt      # Python dependencies
├── README.md             # Project documentation
├── config.json           # ⚠️ Should not be committed to git! (AWS credentials)
├── templates/            # Jinja2 HTML templates
│   ├── base.html         # Base template (Bootstrap navbar)
│   ├── index.html        # Main page (URL shortening form)
│   ├── login.html        # Login page
│   ├── register.html     # Registration page
│   └── stats.html        # Statistics page
└── AWS-PPT.pptx          # Presentation file
```

---

## 🔄 Deployment Scenario

### Current Deployment (Estimate):

1. **Server:**
   - Likely an EC2 instance or similar VM
   - Python 3.6+ installed
   - Flask application runs with `python app.py`

2. **Database:**
   - MySQL server (separate instance or same server)
   - Connects via `db_host` from config

3. **Storage:**
   - AWS S3 bucket (eu-north-1)
   - Public read access

4. **Web Server:**
   - Flask development server (⚠️ not suitable for production!)
   - Should use WSGI server like Gunicorn, uWSGI

5. **Reverse Proxy:**
   - Likely Nginx or Apache
   - Proxy from port 5000 to 80/443

### Recommended Production Deployment:

```
Internet
   │
   ▼
[CloudFront CDN]  (optional)
   │
   ▼
[Application Load Balancer]
   │
   ├──► [EC2 Instance 1] ──► [Flask App] ──► [RDS MySQL]
   ├──► [EC2 Instance 2] ──► [Flask App] ──► [RDS MySQL]
   └──► [EC2 Instance N] ──► [Flask App] ──► [RDS MySQL]
                                    │
                                    ▼
                              [ElastiCache Redis] (session store)
                                    │
                                    ▼
                              [SQS Queue] ──► [Worker EC2] ──► [Gradio API]
                                    │
                                    ▼
                              [S3 Bucket] (QR code images)
```

---

## 📝 Summary and Evaluation

### ✅ Strengths:

1. **Simple and Understandable Architecture:**
   - Monolithic structure, easy to maintain
   - Flask's simplicity

2. **Cloud Integration:**
   - AWS S3 usage
   - Static file hosting

3. **AI Integration:**
   - Gradio AI model integration
   - Customized QR code generation

4. **Statistics Features:**
   - Visualization with Plotly
   - Click tracking

### ⚠️ Areas Needing Improvement:

1. **Security:**
   - Password hashing
   - Secret key management
   - Config file security

2. **Cloud Native Features:**
   - Containerization (Docker)
   - Orchestration (Kubernetes)
   - Serverless functions
   - Managed services (RDS, ElastiCache)

3. **Scalability:**
   - Horizontal scaling
   - Database replication
   - Caching layer
   - Async processing

4. **Production Readiness:**
   - WSGI server (Gunicorn)
   - Environment variables
   - Logging and monitoring
   - Health checks

### 🎯 Conclusion:

This project is functional as a **basic URL shortening service** and includes cloud features with **AWS S3 integration**. However, it lacks **modern cloud-native architecture** features (Kubernetes, serverless, containerization) and is not **production-ready**. Improvements are needed in terms of security and scalability.

---

## 📚 References and Notes

- **Gradio Endpoint:** Provided from Kaggle notebook
- **AWS Region:** eu-north-1 (Stockholm)
- **Database:** MySQL (not a managed service)
- **Framework:** Flask (Python)
- **Frontend:** Bootstrap 4.3.1

---

*This analysis was created based on code review and architectural evaluation.*

