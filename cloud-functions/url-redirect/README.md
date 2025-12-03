# URL Redirect Cloud Function

This Cloud Function handles short URL redirection and click tracking.

## Functionality

- Decodes hashid to get URL ID
- Looks up original URL from MySQL database (on VM)
- Increments click count
- Redirects user to original URL (HTTP 302)

## Deployment

```bash
# Deploy Cloud Function
gcloud functions deploy url-redirect \
  --gen2 \
  --runtime python311 \
  --region us-east1 \
  --source . \
  --entry-point url_redirect \
  --trigger-http \
  --allow-unauthenticated \
  --set-env-vars DB_HOST=10.142.0.15,DB_PORT=3306,DB_USER=appuser,DB_PASSWORD=urlshortener2024,DB_DATABASE=urlshortener,SECRET_KEY=YOUR_SECRET_KEY \
  --memory 256MB \
  --timeout 10s
```

## Environment Variables

- `DB_HOST`: MySQL VM internal IP (10.142.0.15)
- `DB_PORT`: MySQL port (3306)
- `DB_USER`: Database user (appuser)
- `DB_PASSWORD`: Database password
- `DB_DATABASE`: Database name (urlshortener)
- `SECRET_KEY`: Flask secret key (same as Flask app for hashid decoding)

## Testing

```bash
# Get function URL
FUNCTION_URL=$(gcloud functions describe url-redirect --gen2 --region us-east1 --format="value(serviceConfig.uri)")

# Test redirect
curl -L "$FUNCTION_URL/url-redirect/aB3d"
```

## Integration

After deployment:
1. Update Flask app to remove or make optional the `/<id>` route
2. Update short URL format to point to Cloud Function
3. Or use Cloud Load Balancer to route short URLs to Cloud Function

