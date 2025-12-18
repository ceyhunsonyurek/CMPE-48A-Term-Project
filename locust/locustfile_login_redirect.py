import random
import re
from locust import HttpUser, task, between

class LoginRedirectUser(HttpUser):
    """
    Simple test: Login + clicking existing shortened URLs.
    Serverless (Cloud Function) redirect test.
    
    NOTE: Does not hit stats endpoint - extracts hashids from URLs.
    """
    wait_time = between(1, 3)
    known_hashids = []
    stats_fetched = False
    
    def on_start(self):
        """Login when each user starts"""
        # Login
        self.client.get("/login", name="GET /login")
        self.client.post(
            "/login",
            data={
                "username": "loadtest",
                "password": "password123"
            },
            name="POST /login"
        )
        
        # Collect hashids only once (to avoid load on stats endpoint)
        # First user fetches from stats, others wait or try random hashids
        if not self.known_hashids and not self.stats_fetched:
            # Call stats only once (for first user)
            # Other users can try random hashids
            stats_response = self.client.get("/stats", name="Setup: Fetch hashids (once)")
            self.stats_fetched = True
            if stats_response.status_code == 200:
                # Extract hashids from HTML - from short_urls
                # Short URL format: https://.../<hashid> or http://.../<hashid>
                hashid_matches = re.findall(r'/([a-zA-Z0-9]{4,})["\s]', stats_response.text)
                # Also extract from download-qr links
                qr_matches = re.findall(r'/download-qr/([a-zA-Z0-9]+)', stats_response.text)
                all_matches = hashid_matches + qr_matches
                if all_matches:
                    # Filter: only take hashids with 4+ characters (Hashids min_length=4)
                    self.known_hashids = list(set([h for h in all_matches if len(h) >= 4]))
    
    @task
    def click_shortened_url(self):
        """
        Click existing shortened URL (redirect test).
        
        If Cloud Function is used:
        - Flask app: GET /<hashid> -> redirect to Cloud Function (302)
        - Cloud Function: Find original_url from database and redirect
        - Database: SELECT + UPDATE clicks
        
        If Cloud Function is not used:
        - Flask app: Find original_url from database and redirect
        - Database: SELECT + UPDATE clicks
        """
        if self.known_hashids:
            hashid = random.choice(self.known_hashids)
            # allow_redirects=False because we only test the redirect
            # (redirect to Cloud Function or final redirect)
            self.client.get(
                f"/{hashid}",
                name="GET /<hashid>: Redirect (Serverless/DB)",
                allow_redirects=False  # Only test redirect response
            )
        else:
            # If no hashid, try random hashid (may 404 but redirect logic is tested)
            # In this case we don't hit stats - only test redirect endpoint
            random_hashid = ''.join(random.choices('abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789', k=6))
            self.client.get(
                f"/{random_hashid}",
                name="GET /<hashid>: Redirect (Random - may 404)",
                allow_redirects=False
            )
