import random
from locust import HttpUser, task, between

class LoginAndInsertUser(HttpUser):
    """
    Locust test scenario that only performs login and URL insert operations.
    """
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Runs when each user starts - perform login"""
        # Get login page
        self.client.get("/login", name="GET /login")
        
        # Perform login
        response = self.client.post(
            "/login",
            data={
                "username": "loadtest",
                "password": "password123"
            },
            name="POST /login"
        )
        
        # If login successful, session has been created
        if response.status_code == 200 or response.status_code == 302:
            # May have been redirected to homepage, success
            pass
    
    @task(3)
    def insert_url(self):
        """
        Performs URL shortening operation.
        
        This single POST request actually includes:
        1. Database write (INSERT to MySQL VM) - IO intensive
        2. QR code generation (Python qrcode library) - CPU intensive (in pod)
        3. GCS upload (QR code upload to Google Cloud Storage) - Network + Storage
        4. File I/O (temp file creation and deletion) - Disk I/O
        
        So this test covers database, CPU, network, and storage.
        """
        random_id = random.randint(1, 1000000)
        target_url = f"https://www.google.com/search?q={random_id}"
        
        self.client.post(
            "/",
            data={"url": target_url},
            name="POST /: Insert URL (DB+QR+GCS)"
        )
    
    @task(1)
    def view_homepage(self):
        """
        Views homepage (after login).
        """
        self.client.get("/", name="GET /: Homepage")
