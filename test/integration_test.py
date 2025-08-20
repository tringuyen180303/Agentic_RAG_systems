import pytest
import requests
import asyncio
import time
import json
from typing import Dict, Any
import os
from unittest.mock import patch, MagicMock

# Test configuration
TEST_BASE_URL = os.getenv("TEST_BASE_URL", "http://localhost:8080")
TEST_TIMEOUT = 60

class TestRAGIntegration:
    """Integration tests for RAG API endpoints"""
    
    @pytest.fixture(scope="class")
    def test_session(self):
        """Create a session for testing"""
        session = requests.Session()
        session.headers.update({"Content-Type": "application/json"})
        yield session
        session.close()
    
    @pytest.fixture
    def sample_queries(self):
        """Sample queries for testing"""
        return [
            {
                "query": "What is artificial intelligence?",
                "expected_keywords": ["artificial", "intelligence", "AI", "machine", "learning"]
            },
            {
                "query": "Explain machine learning algorithms",
                "expected_keywords": ["machine", "learning", "algorithm", "model", "data"]
            },
            {
                "query": "How does deep learning work?",
                "expected_keywords": ["deep", "learning", "neural", "network", "layer"]
            }
        ]
    
    def test_health_endpoint_integration(self, test_session):
        """Test health endpoint returns proper structure"""
        response = test_session.get(f"{TEST_BASE_URL}/health", timeout=10)
        
        assert response.status_code == 200
        data = response.json()
        
        # Verify required fields
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert data["status"] == "healthy"
        
        # Verify timestamp format
        from datetime import datetime
        timestamp = datetime.fromisoformat(data["timestamp"].replace('Z', '+00:00'))
        assert timestamp is not None
    
    def test_metrics_endpoint_integration(self, test_session):
        """Test metrics endpoint returns Prometheus format"""
        response = test_session.get(f"{TEST_BASE_URL}/metrics", timeout=10)
        
        assert response.status_code == 200
        content = response.text
        
        # Should contain Prometheus metrics or be empty initially
        if content:
            # Basic Prometheus format validation
            assert "# HELP" in content or "rag_requests_total" in content
    
    def test_rag_endpoint_integration(self, test_session, sample_queries):
        """Test RAG endpoint with real queries"""
        for query_data in sample_queries:
            test_payload = {
                "query": query_data["query"],
                "user_id": f"integration_test_{int(time.time())}",
                "session_id": f"integration_session_{int(time.time())}",
                "metadata": {"test_type": "integration"}
            }
            
            response = test_session.post(
                f"{TEST_BASE_URL}/rag",
                json=test_payload,
                timeout=TEST_TIMEOUT
            )
            
            # Check response status
            assert response.status_code == 200, f"Failed for query: {query_data['query']}"
            
            # Validate response structure
            data = response.json()
            assert "answer" in data
            assert "sources" in data
            assert "user_id" in data
            assert "session_id" in data
            
            # Validate response content
            assert len(data["answer"]) > 10, "Answer too short"
            assert data["user_id"] == test_payload["user_id"]
            assert data["session_id"] == test_payload["session_id"]
            assert isinstance(data["sources"], list)
            
            # Check if response contains expected keywords (loose validation)
            answer_lower = data["answer"].lower()
            found_keywords = sum(1 for keyword in query_data["expected_keywords"] 
                               if keyword.lower() in answer_lower)
            assert found_keywords > 0, f"No expected keywords found in answer for query: {query_data['query']}"
    
    def test_rag_guarded_endpoint_integration(self, test_session):
        """Test guarded RAG endpoint with various inputs"""
        test_cases = [
            {
                "query": "What is machine learning and how does it work?",
                "expected_safety": "safe",
                "description": "Safe query"
            },
            {
                "query": "Tell me about AI safety and my email is test@example.com",
                "expected_safety": "filtered",
                "description": "Query with PII"
            },
            {
                "query": "Explain neural networks in simple terms",
                "expected_safety": "safe", 
                "description": "Technical query"
            }
        ]
        
        for test_case in test_cases:
            test_payload = {
                "query": test_case["query"],
                "user_id": f"guarded_test_{int(time.time())}",
                "session_id": f"guarded_session_{int(time.time())}",
                "metadata": {"test_type": "guarded_integration"}
            }
            
            response = test_session.post(
                f"{TEST_BASE_URL}/rag_guarded",
                json=test_payload,
                timeout=TEST_TIMEOUT
            )
            
            assert response.status_code == 200, f"Failed for: {test_case['description']}"
            
            data = response.json()
            
            # Validate response structure
            required_fields = ["answer", "sources", "user_id", "session_id", "safety_status"]
            for field in required_fields:
                assert field in data, f"Missing field {field} in response"
            
            # Validate safety status
            assert data["safety_status"] in ["safe", "filtered"], "Invalid safety status"
            
            # Check for warnings if content was filtered
            if data.get("filtered_content"):
                assert "warnings" in data
    
    def test_concurrent_requests_integration(self, test_session):
        """Test handling of concurrent requests"""
        import concurrent.futures
        import threading
        
        def make_request(query_id):
            payload = {
                "query": f"Test concurrent query {query_id}",
                "user_id": f"concurrent_user_{query_id}",
                "session_id": f"concurrent_session_{query_id}",
                "metadata": {"test_type": "concurrent"}
            }
            
            response = test_session.post(
                f"{TEST_BASE_URL}/rag",
                json=payload,
                timeout=TEST_TIMEOUT
            )
            return response.status_code, query_id
        
        # Test with 5 concurrent requests
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            futures = [executor.submit(make_request, i) for i in range(5)]
            results = [future.result() for future in concurrent.futures.as_completed(futures)]
        
        # All requests should succeed
        for status_code, query_id in results:
            assert status_code == 200, f"Concurrent request {query_id} failed"
    
    def test_error_handling_integration(self, test_session):
        """Test error handling for various scenarios"""
        
        # Test invalid JSON
        response = test_session.post(
            f"{TEST_BASE_URL}/rag",
            data="invalid json",
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        assert response.status_code in [400, 422]
        
        # Test missing required fields
        response = test_session.post(
            f"{TEST_BASE_URL}/rag",
            json={"user_id": "test"},  # Missing query
            timeout=10
        )
        assert response.status_code == 422
        
        # Test empty query
        response = test_session.post(
            f"{TEST_BASE_URL}/rag",
            json={"query": ""},
            timeout=10
        )
        assert response.status_code in [400, 422]
        
        # Test very long query
        long_query = "A" * 10000
        response = test_session.post(
            f"{TEST_BASE_URL}/rag",
            json={"query": long_query},
            timeout=TEST_TIMEOUT
        )
        # Should either process or reject gracefully
        assert response.status_code in [200, 400, 413, 422]
    
    def test_session_tracking_integration(self, test_session):
        """Test session tracking across multiple requests"""
        session_id = f"tracking_session_{int(time.time())}"
        user_id = f"tracking_user_{int(time.time())}"
        
        # Make multiple requests with same session
        for i in range(3):
            payload = {
                "query": f"Session tracking test query {i}",
                "user_id": user_id,
                "session_id": session_id,
                "metadata": {"request_number": i}
            }
            
            response = test_session.post(
                f"{TEST_BASE_URL}/rag",
                json=payload,
                timeout=TEST_TIMEOUT
            )
            
            assert response.status_code == 200
            data = response.json()
            assert data["user_id"] == user_id
            assert data["session_id"] == session_id
    
    @pytest.mark.slow
    def test_performance_integration(self, test_session):
        """Test performance characteristics"""
        query = "What is the difference between supervised and unsupervised learning?"
        payload = {
            "query": query,
            "user_id": "performance_test",
            "session_id": "performance_session"
        }
        
        start_time = time.time()
        response = test_session.post(
            f"{TEST_BASE_URL}/rag",
            json=payload,
            timeout=TEST_TIMEOUT
        )
        end_time = time.time()
        
        assert response.status_code == 200
        
        # Response should be within reasonable time
        response_time = end_time - start_time
        assert response_time < 30, f"Response too slow: {response_time}s"
        
        # Response should be of reasonable quality
        data = response.json()
        assert len(data["answer"]) > 50, "Answer too short for complex query"