# locustfile.py

from locust import HttpUser, task, between
import random
import uuid
from datetime import datetime

class RAGAgentUser(HttpUser):
    wait_time = between(1, 2)  # Wait 1-2 seconds between tasks

    # A list of sample queries to simulate different users
    queries = [
        "Explain the MN-vane code",
        "Summarize the latest quarterly earnings report",
        "What is the weather forecast for New York tomorrow?",
        "How many users signed up last month?",
        "Describe the architecture of a RAG pipeline",
    ]

    @task
    def rag_agent(self):
        # Pick a random query
        query = random.choice(self.queries)
        user_id = f"user_{self.environment.runner.user_count}"
        session_id = f"sess_{uuid.uuid4().hex[:8]}"
        payload = {
            "query": query,
            "user_id": user_id,
            "session_id": session_id,
            "metadata": {"source": "locust_test"}
        }
        headers = {
            "Content-Type": "application/json",
            "X-User-Id": user_id,
            "X-Session-Id": session_id
        }

        with self.client.post("/rag_agent", json=payload, headers=headers, catch_response=True, timeout=60) as response:
            if response.status_code != 200:
                response.failure(f"Unexpected status code: {response.status_code}")
            else:
                try:
                    data = response.json()
                    if "answer" in data:
                        response.success()
                    else:
                        response.failure("No 'answer' field in response")
                except Exception as e:
                    response.failure(f"Invalid JSON: {e}")

# Instructions:
# 1. pip install locust
# 2. Save this as locustfile.py in your project root.
# 3. Run: locust -f locustfile.py --host=http://localhost:8081
# 4. Open http://localhost:8089 in your browser to start the load test.

