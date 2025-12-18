# Performance Testing Updates

## Overview
This document outlines the performance testing improvements and optimizations made to the URL Shortener application.

## Test Files Created

### 1. `locustfile_login_insert.py`
**Purpose:** Test URL insertion performance
- **What it does:** Login + URL shortening operations
- **Why:** Test database write, QR generation, and GCS upload under load
- **Steps:**
  1. Login
  2. POST / with URL (3x weight) - includes:
     - Database INSERT
     - QR code generation
     - GCS upload
  3. GET / homepage (1x weight)

### 2. `locustfile_login_stats.py`
**Purpose:** Test stats endpoint performance
- **What it does:** Login + stats page access
- **Why:** Test database read queries and response time
- **Steps:**
  1. Login
  2. GET /stats - database SELECT queries

### 3. `locustfile_login_redirect.py`
**Purpose:** Test URL redirection performance
- **What it does:** Login + click shortened URLs
- **Why:** Test serverless Cloud Function redirect and database updates
- **Steps:**
  1. Login
  2. Fetch hashids from stats (once per user)
  3. GET /<hashid> - redirect test (may hit Cloud Function)

### 4. `locustfile_comprehensive.py`
**Purpose:** Comprehensive end-to-end testing
- **What it does:** Tests all application features
- **Why:** Real-world usage simulation
- **Steps:**
  1. Register (30%) or Login (70%)
  2. URL insertion (3x weight)
  3. Stats viewing (2x weight)
  4. URL redirection (4x weight)
  5. QR code download (1x weight)
  6. Homepage viewing (2x weight)
  7. Logout/login cycle (1x weight)
  8. Health/metrics endpoints (1x weight each)

## Performance Optimizations

### 1. Health Endpoint Optimization
**Problem:** Health checks were causing pod restarts under load
- **Solution:** Removed database query from health check
- **Result:** Ultra-fast health endpoint (<1ms response time)
- **Implementation:**
  - Check only for connection pool existence
  - No actual database connectivity test
  - Fast failure detection for Kubernetes probes

### 2. Stats Endpoint Optimization
**Problem:** Stats endpoint had high response times and large response sizes
- **Solution 1:** Removed Plotly charts
  - Charts were generating large HTML responses (20MB+)
  - Removed chart generation logic
  - Removed Plotly.js CDN from template
- **Solution 2:** Limited database query results
  - Added `MAX_TABLE_ITEMS = 100` limit
  - Fetch only last 100 URLs instead of all
  - Reduced database load and response size
- **Solution 3:** Optimized database queries
  - Combined COUNT and SUM into single query
  - Reduced from 3 queries to 2 queries
  - Added database indexes for faster SELECT
- **Solution 4:** Added database indexes
  - Created `idx_user_id` on `urls(user_id)`
  - Created `idx_user_id_id` on `urls(user_id, id DESC)`
  - Significantly improved query performance

### 3. Connection Pooling
**Problem:** Database connection overhead under load
- **Solution:** Implemented connection pooling with DBUtils
- **Configuration:**
  - Min connections: 5 per pod
  - Max connections: 20 per pod
  - Connection reuse instead of creating new connections
- **Result:** Reduced connection overhead and improved performance

### 4. Gunicorn Configuration
**Problem:** Limited concurrency under load
- **Solution:** Increased workers and added threads
- **Configuration:**
  - Workers: 4 (increased from 2)
  - Threads: 2 per worker
  - Keep-alive: 5 seconds
- **Result:** Better handling of concurrent requests

### 5. Resource Limits
**Problem:** Pods running out of resources under load
- **Solution:** Increased CPU and memory limits
- **Configuration:**
  - CPU requests: 500m (increased from 300m)
  - CPU limits: 2000m (increased from 1000m)
  - Memory requests: 512Mi (increased from 384Mi)
  - Memory limits: 1Gi (increased from 768Mi)
- **Result:** More headroom for workers and connection pooling

### 6. Probe Configuration
**Problem:** Pods restarting due to probe timeouts
- **Solution:** Adjusted probe timings
- **Configuration:**
  - Liveness: 30s initial delay, 20s period, 3s timeout
  - Readiness: 15s initial delay, 10s period, 2s timeout
- **Result:** Reduced false positives and pod restarts

## Database Indexes

### Script: `vm-scripts/add-indexes.sh`
**Purpose:** Add performance indexes to database
- **Indexes created:**
  - `idx_user_id` on `urls(user_id)` - speeds up user-specific queries
  - `idx_user_id_id` on `urls(user_id, id DESC)` - optimizes stats page queries
- **Impact:** Significantly faster SELECT queries filtered by user_id

## Testing Strategy

### Isolated Tests
1. **Login + Insert** - Database write and file operations
2. **Login + Stats** - Database read performance
3. **Login + Redirect** - Serverless function and redirect performance

### Comprehensive Test
- **Full application test** - Real-world usage patterns
- Tests all endpoints with weighted tasks
- Includes registration, login, CRUD operations, and monitoring

## Metrics Tracked

### Application Metrics (`/metrics` endpoint)
- `url_shortener_requests_total` - Total requests
- `url_shortener_errors_total` - Total errors

### Locust Metrics
- Response times (min, max, median, 95th, 99th percentile)
- Request rate (requests per second)
- Failure rate (percentage)
- Response size (bytes)

## Key Findings

1. **Stats endpoint** was the main bottleneck
   - High response times due to chart generation
   - Large response sizes (20MB+)
   - Multiple database queries

2. **Health checks** were too slow
   - Database queries in health check caused timeouts
   - Led to pod restarts under load

3. **Database queries** needed optimization
   - Missing indexes on frequently queried columns
   - Multiple separate queries instead of combined queries

4. **Connection overhead** was significant
   - Creating new connections for each request
   - Connection pooling solved this issue

## Files Modified

- `app/app.py` - Health endpoint, stats endpoint, connection pooling
- `app/templates/stats.html` - Removed charts, added limit message
- `docker/Dockerfile` - Increased Gunicorn workers
- `k8s/deployment.yaml` - Resource limits, probe configuration
- `k8s/configmap.yaml` - Connection pool configuration
- `vm-scripts/setup-mysql.sh` - Added index creation
- `vm-scripts/add-indexes.sh` - New script for adding indexes

## Test Execution

### Running Individual Tests
```bash
# Login + Insert
locust -f locustfile_login_insert.py --host=https://your-domain.com

# Login + Stats
locust -f locustfile_login_stats.py --host=https://your-domain.com

# Login + Redirect
locust -f locustfile_login_redirect.py --host=https://your-domain.com

# Comprehensive
locust -f locustfile_comprehensive.py --host=https://your-domain.com
```

### Headless Mode
```bash
locust -f locustfile_comprehensive.py --host=https://your-domain.com \
  --users 100 --spawn-rate 10 --run-time 5m --headless
```

## Next Steps

1. Monitor performance metrics under different load patterns
2. Fine-tune connection pool sizes based on actual usage
3. Consider additional optimizations based on test results
4. Document performance baselines for future comparisons
