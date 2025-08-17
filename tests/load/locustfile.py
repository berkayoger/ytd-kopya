from locust import HttpUser, task, between
import json, random, string, websocket, threading


def random_symbol():
    return "".join(random.choices(string.ascii_uppercase, k=4))


class BatchUser(HttpUser):
    wait_time = between(1, 5)

    @task(2)
    def submit_batch(self):
        symbols = [random_symbol() for _ in range(10)]
        payload = {"asset": "crypto", "symbols": symbols, "timeframe": "1h"}
        self.client.post("/api/batch/submit", json=payload)

    @task(1)
    def get_status(self):
        # Rastgele job_id (gerçekte daha kontrollü kullanılmalı)
        job_id = "dummy"
        self.client.get(f"/api/batch/status/{job_id}")


class WSClient(threading.Thread):
    def run(self):
        ws = websocket.WebSocket()
        ws.connect("ws://localhost:5000/batch")
        ws.send("join:dummy_job")
        try:
            for _ in range(10):
                msg = ws.recv()
                print("[WS]", msg)
        finally:
            ws.close()


class WSUser(HttpUser):
    wait_time = between(5, 10)

    @task
    def ws_connect(self):
        t = WSClient()
        t.start()
        t.join()
