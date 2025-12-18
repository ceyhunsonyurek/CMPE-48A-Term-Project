import random
import re
from locust import HttpUser, task, between

class ComprehensiveUser(HttpUser):
    """
    Comprehensive Locust test scenario that tests all application features.
    """
    wait_time = between(1, 3)
    known_hashids = []
    username = None
    
    def on_start(self):
        """Runs when each user starts - register or login"""
        # Randomly register or login
        if random.random() < 0.3:  # 30% chance to create new user
            self.username = f"testuser_{random.randint(1000, 9999)}"
            self.register()
        else:  # 70% chance to login with existing user
            self.username = "loadtest"
            self.login()
    
    def register(self):
        """Creates new user registration (Database write test)"""
        password = "password123"
        self.client.get("/register", name="GET /register")
        response = self.client.post(
            "/register",
            data={
                "username": self.username,
                "password": password,
                "confirm_password": password
            },
            name="POST /register"
        )
    
    def login(self):
        """Performs login operation"""
        self.client.get("/login", name="GET /login")
        self.client.post(
            "/login",
            data={
                "username": self.username,
                "password": "password123"
            },
            name="POST /login"
        )
    
    # === DATABASE WRITE TESTS ===
    
    @task(3)
    def insert_url(self):
        """
        URL shortening operation (Database write + QR generation + GCS upload)
        - Database: INSERT into urls
        - CPU: QR code generation
        - Network: GCS upload
        """
        random_id = random.randint(1, 1000000)
        target_url = f"https://www.google.com/search?q={random_id}"
        
        response = self.client.post(
            "/",
            data={"url": target_url},
            name="POST /: Insert URL (DB+QR+GCS)"
        )
        
        # Extract hashid from response (if successful)
        if response.status_code == 200:
            hashid_match = re.search(r'/download-qr/([a-zA-Z0-9]+)', response.text)
            if hashid_match:
                hashid = hashid_match.group(1)
                if hashid not in self.known_hashids:
                    self.known_hashids.append(hashid)
    
    # === DATABASE READ TESTS ===
    
    @task(2)
    def view_stats(self):
        """
        Statistics page (Database read test)
        - Database: SELECT queries (urls WHERE user_id)
        - CPU: Plotly chart generation
        - Memory: Chart rendering
        """
        self.client.get("/stats", name="GET /stats (DB Read)")
    
    @task(4)
    def redirect_url(self):
        """
        URL redirect operation (Database read + update test)
        - Database: SELECT original_url, clicks
        - Database: UPDATE clicks (increment)
        - Network: Redirect response
        
        If Cloud Function is used, redirects to Cloud Function.
        """
        if self.known_hashids:
            hashid = random.choice(self.known_hashids)
            # Cloud Function veya Flask redirect
            self.client.get(f"/{hashid}", name="GET /<id>: Redirect (DB Read+Update)", allow_redirects=False)
    
    # === GCS READ TESTS ===
    
    @task(1)
    def download_qr_code(self):
        """
        QR code download (GCS read test)
        - Network: Blob download from GCS
        - Memory: Image data in-memory
        - Response: Binary file serving
        """
        if self.known_hashids:
            hashid = random.choice(self.known_hashids)
            self.client.get(f"/download-qr/{hashid}", name="GET /download-qr/<id> (GCS Read)")
    
    # === UI TESTS ===
    
    @task(2)
    def view_homepage(self):
        """View homepage (simple HTML serving)"""
        self.client.get("/", name="GET /: Homepage")
    
    @task(1)
    def logout(self):
        """Logout operation (session clearing)"""
        self.client.get("/logout", name="GET /logout")
        # Login again after logout
        self.login()
    
    # === MONITORING ENDPOINTS ===
    
    @task(1)
    def check_health(self):
        """Health check endpoint (ultra-fast, no DB query)"""
        self.client.get("/health", name="GET /health")
    
    @task(1)
    def check_metrics(self):
        """Metrics endpoint (Prometheus format)"""
        self.client.get("/metrics", name="GET /metrics")
