import random
import re
from locust import HttpUser, task, between, tag

# REPLACE with your actual Cloud Function URL
CLOUD_FUNCTION_BASE_URL = "https://us-east1-url-shortener-479913.cloudfunctions.net/url-redirect"

class ProjectUser(HttpUser):
    wait_time = between(1, 2)
    known_hashids = []

    def on_start(self):
        # Login is required for all tasks, so it runs every time
        self.client.get("/login")
        self.client.post("/login", data={
            "username": "loadtest",
            "password": "password123"
        })

    # --- SCENARIO 1: GKE / APP STRESS ---
    # Tests the Flask Pods' ability to serve HTML pages (CPU intensive)
    @tag('app')
    @task(3)
    def view_dashboard(self):
        self.client.get("/", name="GKE: Homepage")

    # --- SCENARIO 2: VM / DATABASE STRESS ---
    # Tests the MySQL VM's write capacity (IO intensive)
    @tag('db')
    @task(2)
    def shorten_url(self):
        random_id = random.randint(1, 1000000)
        target_url = f"https://www.google.com/search?q={random_id}"
        self.client.post("/", data={"url": target_url}, name="VM: Insert URL")

    # --- SCENARIO 3: SERVERLESS STRESS ---
    # Tests the Cloud Function + VPC Connector throughput (Network intensive)
    @tag('serverless')
    @task(4)
    def test_serverless_redirect(self):
        # First, harvest an ID if we don't have one
        if not self.known_hashids:
             response = self.client.get("/stats", name="Setup: Fetch IDs")
             if response.status_code == 200:
                 self.known_hashids = re.findall(r'/download-qr/([a-zA-Z0-9]+)', response.text)
        
        if self.known_hashids:
            hashid = random.choice(self.known_hashids)
            target_url = f"{CLOUD_FUNCTION_BASE_URL}/{hashid}"
            # This hits the Cloud Function directly
            self.client.get(target_url, name="Serverless: Redirect")