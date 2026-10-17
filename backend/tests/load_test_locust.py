from locust import HttpUser, task, between
import random

class FarmerUser(HttpUser):
    wait_time = between(2, 5)
    token = None
    farm_id = None
    motor_id = None

    def on_start(self):
        # Authenticate simulated farmer
        res = self.client.post("/api/v1/auth/login", json={
            "phone_number": "9876543210",
            "password": "FarmerPass123!"
        })
        if res.status_code == 200:
            data = res.json()
            self.token = data["access_token"]
            self.farm_id = data["user"]["farm_id"]
            self.headers = {"Authorization": f"Bearer {self.token}"}

            # Fetch motor
            m_res = self.client.get(f"/api/v1/farms/{self.farm_id}/motors", headers=self.headers)
            if m_res.status_code == 200 and len(m_res.json()) > 0:
                self.motor_id = m_res.json()[0]["id"]

    @task(5)
    def view_dashboard_and_motors(self):
        if self.token and self.farm_id:
            self.client.get(f"/api/v1/farms/{self.farm_id}/motors", headers=self.headers)

    @task(3)
    def view_pipeline_state(self):
        if self.token and self.motor_id:
            self.client.get(f"/api/v1/motors/{self.motor_id}/pipeline-state", headers=self.headers)

    @task(2)
    def query_voice_assistant(self):
        if self.token:
            queries = [
                ("மோட்டார் ஓடுகிறதா?", "ta"),
                ("Is my motor running?", "en"),
                ("எந்த பைப்லைன் செயலில் உள்ளது?", "ta"),
                ("Next irrigation time", "en")
            ]
            q, lang = random.choice(queries)
            self.client.post("/api/v1/voice/query", json={"text": q, "language": lang}, headers=self.headers)

    @task(1)
    def check_alerts(self):
        if self.token:
            self.client.get("/api/v1/faults", headers=self.headers)
