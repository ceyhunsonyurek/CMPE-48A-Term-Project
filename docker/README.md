# Docker Build Instructions

## Building the Docker Image

```bash
# From project root directory
docker build -f docker/Dockerfile -t url-shortener:latest .
```

## Running the Container

```bash
# Run with environment variables
docker run -d \
  -p 5000:5000 \
  -e DB_HOST=your_db_host \
  -e DB_PORT=3306 \
  -e DB_USER=appuser \
  -e DB_PASSWORD=your_password \
  -e DB_DATABASE=urlshortener \
  -e GCP_PROJECT_ID=your_project_id \
  -e GCS_BUCKET_NAME=your_bucket_name \
  -e SECRET_KEY=your_secret_key \
  -e GRADIO_ENDPOINT=your_gradio_endpoint \
  --name url-shortener \
  url-shortener:latest
```

## Using .env file

```bash
# Create .env file with your configuration
# Then run:
docker run -d \
  -p 5000:5000 \
  --env-file .env \
  --name url-shortener \
  url-shortener:latest
```

## Testing

```bash
# Check if container is running
docker ps

# Check logs
docker logs url-shortener

# Test health endpoint
curl http://localhost:5000/health

# Stop container
docker stop url-shortener

# Remove container
docker rm url-shortener
```

## For GCP Deployment

After building, tag the image for GCP Container Registry:

```bash
docker tag url-shortener:latest gcr.io/PROJECT_ID/url-shortener:latest
```

