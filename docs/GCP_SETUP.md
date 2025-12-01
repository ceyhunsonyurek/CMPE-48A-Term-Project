# GCP Setup Guide

## Project Information
- **Project ID:** `url-shortener-479913`
- **Project Name:** `url-shortener`
- **Project Number:** `755261402036`
- **Region:** `us-central1` (Iowa) - Recommended
- **Registry Type:** Artifact Registry (Recommended)

## Step 1: Authenticate with Different Gmail Account

```bash
# Login with the new Gmail account
gcloud auth login

# Set the project
gcloud config set project url-shortener-479913

# Verify project
gcloud config get-value project
```

## Step 2: Enable Required APIs

```bash
# Enable Artifact Registry API
gcloud services enable artifactregistry.googleapis.com

# Enable Container Registry API (if needed for backward compatibility)
gcloud services enable containerregistry.googleapis.com

# Enable GKE API (for later steps)
gcloud services enable container.googleapis.com

# Enable Cloud Storage API (already using for QR codes)
gcloud services enable storage-api.googleapis.com
```

## Step 3: Configure Docker for Artifact Registry

```bash
# Configure Docker authentication for Artifact Registry
gcloud auth configure-docker us-central1-docker.pkg.dev
```

## Step 4: Create Artifact Registry Repository

```bash
# Create repository for Docker images
gcloud artifacts repositories create url-shortener-repo \
    --repository-format=docker \
    --location=us-central1 \
    --description="Docker repository for URL Shortener application"
```

## Step 5: Tag and Push Docker Image

```bash
# From project root directory
cd /Users/flau/Desktop/CLOUD/CMPE-48A-Term-Project

# Tag the image for Artifact Registry
docker tag url-shortener:latest \
    us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo/url-shortener:latest

# Push to Artifact Registry
docker push us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo/url-shortener:latest
```

## Step 6: Verify Image Push

```bash
# List images in repository
gcloud artifacts docker images list \
    us-central1-docker.pkg.dev/url-shortener-479913/url-shortener-repo
```

## Troubleshooting

### If you get permission errors:
```bash
# Check if you have the right permissions
gcloud projects get-iam-policy url-shortener-479913

# You need at least: Artifact Registry Writer or Editor role
```

### If Docker authentication fails:
```bash
# Re-authenticate
gcloud auth login
gcloud auth configure-docker us-central1-docker.pkg.dev
```

### If project access is denied:
- Make sure the Gmail account has been added to the project with appropriate permissions
- Contact project owner to grant access

