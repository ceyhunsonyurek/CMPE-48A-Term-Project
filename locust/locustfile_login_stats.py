from locust import HttpUser, task, between

class LoginStatsUser(HttpUser):
    """
    Simple test: Only login and stats check.
    Database read + chart generation test.
    """
    wait_time = between(1, 3)
    
    def on_start(self):
        """Login when each user starts"""
        self.client.get("/login", name="GET /login")
        self.client.post(
            "/login",
            data={
                "username": "loadtest",
                "password": "password123"
            },
            name="POST /login"
        )
    
    @task
    def check_stats(self):
        """
        Check stats page.
        - Database: SELECT queries (all user's URLs)
        - CPU: Plotly chart generation (bar chart + pie chart)
        """
        self.client.get("/stats", name="GET /stats (DB Read)")
