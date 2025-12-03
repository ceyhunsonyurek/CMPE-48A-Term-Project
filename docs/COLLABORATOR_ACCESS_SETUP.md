# Collaborator Access Setup Guide

## Project Owner Steps (You)

Grant Editor role to collaborator:

**GCP Console:**
1. Go to [GCP Console](https://console.cloud.google.com/)
2. Select project: `url-shortener-479913`
3. Navigate to **IAM & Admin** → **IAM**
4. Click **+ ADD**
5. Enter collaborator's email
6. Select role: **Editor**
7. Click **SAVE**

**Or via CLI:**
```bash
gcloud projects add-iam-policy-binding url-shortener-479913 \
  --member="user:COLLABORATOR_EMAIL" \
  --role="roles/editor"
```

---

## Collaborator Steps (Your Teammate)

1. **Accept email invitation**

2. **Run these commands:**
```bash
gcloud auth login
gcloud config set project url-shortener-479913
gcloud auth configure-docker us-central1-docker.pkg.dev
gcloud container clusters get-credentials url-shortener-cluster --region us-east1
```

3. **Verify access:**
```bash
kubectl get pods
gsutil ls gs://url-shortener-assets
```

**That's it!**
