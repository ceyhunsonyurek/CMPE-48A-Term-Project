# Level 1: Basic Preparation - Progress Report

## Overview
**Duration:** 1-2 Days  
**Difficulty:** Easy  
**Status:** ✅ **COMPLETED**

---

## 1.1 Project Structure Preparation

### What Was Needed
- Organize repository structure for cloud-native deployment
- Create proper folder hierarchy for different components
- Set up `.gitignore` to exclude sensitive files

### What Was Done
- Created folder structure:
  - `app/` - Flask application code
  - `docker/` - Dockerfile and Docker-related files
  - `k8s/` - Kubernetes manifests
  - `cloud-functions/` - Cloud Functions code
  - `vm-scripts/` - VM setup scripts
  - `locust/` - Performance testing scripts
  - `terraform/` - Infrastructure as Code (optional)
  - `docs/` - Documentation
- Created comprehensive `.gitignore` to exclude:
  - Sensitive files (`config.json`, `.env`)
  - Build artifacts
  - Credentials and cache files

### Issues Encountered
- None - straightforward file organization

### Solution
- N/A

---

## 1.2 Environment Variables and Config Management

### What Was Needed
- Replace hardcoded configuration with environment variables
- Support both environment variables and config.json (backward compatibility)
- Create `.env.example` template for documentation

### What Was Done
- Updated `app.py` to use `python-dotenv` for loading environment variables
- Implemented `load_config()` function with fallback to `config.json`
- Created `.env.example` with all required environment variables:
  - Database configuration (DB_HOST, DB_PORT, DB_USER, DB_PASSWORD, DB_DATABASE)
  - GCP configuration (GCP_PROJECT_ID, GCS_BUCKET_NAME)
  - Flask configuration (SECRET_KEY)
  - Gradio endpoint (GRADIO_ENDPOINT - later removed)

### Issues Encountered
- `config.json` was blocked by globalignore (security feature)
- Needed to ensure backward compatibility

### Solution
- Used environment variables as primary source
- Kept `config.json` as fallback for local development
- Documented all required variables in `.env.example`

---

## 1.3 AWS S3 → GCP Cloud Storage Migration

### What Was Needed
- Replace AWS S3 (`boto3`) with Google Cloud Storage
- Update upload function to use GCS
- Update all template references from S3 URLs to GCS URLs

### What Was Done
- Removed `boto3` dependency from `requirements.txt`
- Added `google-cloud-storage` dependency
- Replaced `upload_to_s3()` with `upload_to_gcs()` function
- Updated GCS client initialization with error handling
- Added Flask context processor to inject `gcs_base_url` into all templates
- Updated templates:
  - `index.html` - Loading animation image
  - `login.html` - Background image
  - `stats.html` - QR code images and enlargement function

### Issues Encountered
- Template syntax complexity in `stats.html` (Jinja2 in JavaScript onclick)
- Linter errors due to complex template expressions

### Solution
- Pre-calculated `hash_id` variable using `{% set %}` before using in HTML attributes
- Simplified template expressions to avoid linter errors

---

## Summary

**Completed Tasks:**
- ✅ Project structure organized
- ✅ Environment variable management implemented
- ✅ AWS S3 fully migrated to GCP Cloud Storage
- ✅ All templates updated for GCS URLs

**Key Achievements:**
- Clean, organized codebase ready for containerization
- Secure configuration management (no hardcoded secrets)
- Cloud-agnostic storage layer (GCS instead of S3)

**Time Spent:** ~1 day  
**Files Modified:** `app/app.py`, `requirements.txt`, templates, created `.gitignore`, `.env.example`

