from locust import HttpUser, task, between

class DapurProfitUser(HttpUser):
    wait_time = between(1, 3)
    token = None

    def on_start(self):
        response = self.client.post("/api/auth/login", json={
            "email": "loadtest@dapurprofit.com",
            "password": "password123"
        })
        if response.status_code == 200:
            self.token = response.json().get("access_token")

    @task(3)
    def health_check(self):
        self.client.get("/api/health")

    @task(1)
    def simulate_chat(self):
        if self.token:
            self.client.post("/api/chat", json={
                "message": "test load",
                "chat_history": [],
                "fase_saat_ini": "PAGI_COSTING",
                "total_belanja": 0,
                "hpp_unit": 0
            }, headers={"Authorization": f"Bearer {self.token}"})
