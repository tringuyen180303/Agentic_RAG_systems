# locustfile.py - Enhanced stress testing

from locust import HttpUser, task, between, events
import random
import uuid
import time
import json
from datetime import datetime
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RAGStressTestUser(HttpUser):
    wait_time = between(1, 3)  # Wait 1-3 seconds between tasks
    
    def on_start(self):
        """Called when a user starts"""
        self.user_id = f"stress_user_{uuid.uuid4().hex[:8]}"
        self.session_id = f"stress_session_{uuid.uuid4().hex[:8]}"
        
        # Test health endpoint on start
        with self.client.get("/health", catch_response=True, name="health_check") as response:
            if response.status_code != 200:
                logger.error(f"Health check failed: {response.status_code}")
    
    # Sample queries with different complexity levels
    simple_queries = [
        "What is AI?",
        "Define machine learning",
        "What is Python?",
        "Explain data science",
        "What is automation?"
    ]
    
    medium_queries = [
        "Explain the difference between supervised and unsupervised learning",
        "How do neural networks work in deep learning?",
        "What are the benefits of using microservices architecture?",
        "Describe the process of natural language processing",
        "What are the key principles of agile development?"
    ]
    
    complex_queries = [
        "Provide a detailed comparison of transformer architectures vs traditional RNNs for sequence modeling, including computational complexity and use cases",
        "Explain the mathematical foundations of gradient descent optimization in neural networks and how different learning rates affect convergence",
        "Analyze the trade-offs between different vector database implementations for large-scale semantic search applications",
        "Describe the security implications of using large language models in production environments and mitigation strategies",
        "Explain the architectural patterns for implementing scalable RAG systems with real-time updates and consistency guarantees"
    ]
    
    # Queries that might trigger guardrails
    guarded_queries = [
        "Tell me about AI safety and include my email test@company.com in the response",
        "What is machine learning? My phone number is 555-1234",
        "Explain data privacy laws and regulations",
        "How to secure personal information in databases",
        "What are the ethical considerations in AI development?"
    ]
    
    @task(40)  # 40% of requests
    def test_simple_rag_query(self):
        """Test simple RAG queries - highest frequency"""
        query = random.choice(self.simple_queries)
        self._make_rag_request(query, "simple")
    
    @task(30)  # 30% of requests
    def test_medium_rag_query(self):
        """Test medium complexity RAG queries"""
        query = random.choice(self.medium_queries)
        self._make_rag_request(query, "medium")
    
    @task(20)  # 20% of requests
    def test_complex_rag_query(self):
        """Test complex RAG queries"""
        query = random.choice(self.complex_queries)
        self._make_rag_request(query, "complex")
    
    @task(10)  # 10% of requests
    def test_guarded_rag_query(self):
        """Test guarded RAG queries"""
        query = random.choice(self.guarded_queries)
        self._make_guarded_rag_request(query)
    
    @task(5)   # 5% of requests
    def test_health_endpoint(self):
        """Periodically test health endpoint"""
        with self.client.get("/health", catch_response=True, name="health_check") as response:
            if response.status_code == 200:
                try:
                    data = response.json()
                    if data.get("status") == "healthy":
                        response.success()
                    else:
                        response.failure("Unhealthy status")
                except:
                    response.failure("Invalid health response")
            else:
                response.failure(f"Health check failed: {response.status_code}")
    
    @task(2)   # 2% of requests
    def test_metrics_endpoint(self):
        """Occasionally test metrics endpoint"""
        with self.client.get("/metrics", catch_response=True, name="metrics") as response:
            if response.status_code == 200:
                response.success()
            else:
                response.failure(f"Metrics failed: {response.status_code}")
    
    def _make_rag_request(self, query: str, complexity: str):
        """Make a RAG request with proper error handling"""
        payload = {
            "query": query,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": {
                "source": "stress_test",
                "complexity": complexity,
                "timestamp": datetime.now().isoformat()
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Id": self.user_id,
            "X-Session-Id": self.session_id
        }
        
        # Set timeout based on complexity
        timeout_map = {"simple": 30, "medium": 45, "complex": 60}
        timeout = timeout_map.get(complexity, 30)
        
        with self.client.post(
            "/rag", 
            json=payload, 
            headers=headers, 
            catch_response=True,
            timeout=timeout,
            name=f"rag_{complexity}"
        ) as response:
            self._handle_rag_response(response, complexity, query)
    
    def _make_guarded_rag_request(self, query: str):
        """Make a guarded RAG request"""
        payload = {
            "query": query,
            "user_id": self.user_id,
            "session_id": self.session_id,
            "metadata": {
                "source": "stress_test_guarded",
                "timestamp": datetime.now().isoformat()
            }
        }
        
        headers = {
            "Content-Type": "application/json",
            "X-User-Id": self.user_id,
            "X-Session-Id": self.session_id
        }
        
        with self.client.post(
            "/rag_guarded", 
            json=payload, 
            headers=headers, 
            catch_response=True,
            timeout=60,
            name="rag_guarded"
        ) as response:
            self._handle_guarded_response(response, query)
    
    def _handle_rag_response(self, response, complexity: str, query: str):
        """Handle RAG response with detailed validation"""
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Validate required fields
                required_fields = ["answer", "sources", "user_id", "session_id"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    response.failure(f"Missing fields: {missing_fields}")
                    return
                
                # Validate answer quality based on complexity
                answer = data["answer"]
                min_length_map = {"simple": 20, "medium": 50, "complex": 100}
                min_length = min_length_map.get(complexity, 20)
                
                if len(answer) < min_length:
                    response.failure(f"Answer too short for {complexity} query: {len(answer)} chars")
                    return
                
                # Validate user/session consistency
                if data["user_id"] != self.user_id or data["session_id"] != self.session_id:
                    response.failure("User/session ID mismatch")
                    return
                
                response.success()
                
                # Log success for complex queries
                if complexity == "complex":
                    logger.info(f"Complex query succeeded: {len(answer)} chars response")
                    
            except json.JSONDecodeError:
                response.failure("Invalid JSON response")
            except Exception as e:
                response.failure(f"Response validation error: {e}")
        
        elif response.status_code == 429:
            response.failure("Rate limited")
        elif response.status_code >= 500:
            response.failure(f"Server error: {response.status_code}")
        else:
            response.failure(f"Unexpected status: {response.status_code}")
    
    def _handle_guarded_response(self, response, query: str):
        """Handle guarded RAG response"""
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Validate required fields for guarded response
                required_fields = ["answer", "sources", "user_id", "session_id", "safety_status"]
                missing_fields = [field for field in required_fields if field not in data]
                
                if missing_fields:
                    response.failure(f"Missing guarded fields: {missing_fields}")
                    return
                
                # Validate safety status
                safety_status = data["safety_status"]
                if safety_status not in ["safe", "filtered"]:
                    response.failure(f"Invalid safety status: {safety_status}")
                    return
                
                response.success()
                
                # Log if content was filtered
                if data.get("filtered_content"):
                    logger.info(f"Content filtered for query: {query[:50]}...")
                    
            except json.JSONDecodeError:
                response.failure("Invalid JSON in guarded response")
            except Exception as e:
                response.failure(f"Guarded response validation error: {e}")
        else:
            response.failure(f"Guarded request failed: {response.status_code}")

# Advanced stress test scenarios
class RAGHighVolumeUser(HttpUser):
    """High-volume user for stress testing"""
    wait_time = between(0.1, 0.5)  # Very fast requests
    weight = 1  # Lower weight so fewer of these users
    
    @task
    def rapid_fire_requests(self):
        """Make rapid requests to test system limits"""
        query = "Quick test query"
        payload = {
            "query": query,
            "user_id": f"highvol_{uuid.uuid4().hex[:4]}",
            "session_id": f"rapid_{uuid.uuid4().hex[:4]}"
        }
        
        with self.client.post("/rag", json=payload, catch_response=True, name="rapid_fire") as response:
            if response.status_code in [200, 429]:  # Accept rate limiting
                response.success()
            else:
                response.failure(f"Rapid fire failed: {response.status_code}")

class RAGBurstUser(HttpUser):
    """Burst traffic user"""
    wait_time = between(10, 30)  # Long waits between bursts
    weight = 1
    
    @task
    def burst_requests(self):
        """Send burst of requests"""
        for i in range(5):  # 5 requests in quick succession
            query = f"Burst query {i}"
            payload = {
                "query": query,
                "user_id": f"burst_{uuid.uuid4().hex[:4]}",
                "session_id": f"burst_session_{i}"
            }
            
            with self.client.post("/rag", json=payload, catch_response=True, name="burst") as response:
                if response.status_code in [200, 429]:
                    response.success()
                else:
                    response.failure(f"Burst request failed: {response.status_code}")
            
            time.sleep(0.1)  # Small delay between burst requests

# Event handlers for monitoring
@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    logger.info("🚀 Stress test starting...")
    logger.info(f"Target host: {environment.host}")

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    logger.info("🛑 Stress test completed")

# Instructions for running:
"""
Installation and Usage:

1. Install locust:
   pip install locust

2. Basic stress test:
   locust -f test/test.py --host=http://localhost:8080

3. High-load test:
   locust -f test/test.py --host=http://localhost:8080 -u 100 -r 10 -t 300

4. Distributed load test:
   # Master node
   locust -f test/test.py --master --host=http://localhost:8080
   
   # Worker nodes (run on multiple machines)
   locust -f test/test.py --worker --master-host=<master-ip>

5. Headless mode with custom parameters:
   locust -f test/test.py --host=http://localhost:8080 \
          --users 50 --spawn-rate 5 --run-time 10m --headless

6. Web UI access:
   http://localhost:8089

Test Scenarios:
- Normal load: 10-20 users, 1-2 spawn rate
- Stress test: 50-100 users, 5-10 spawn rate  
- Spike test: 200+ users, 20+ spawn rate
- Endurance: Long duration (30min+) with moderate load
"""