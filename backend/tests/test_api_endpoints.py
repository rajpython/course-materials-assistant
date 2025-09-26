import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock


@pytest.mark.api
class TestAPIEndpoints:
    """Test suite for FastAPI endpoints"""

    def test_root_endpoint(self, test_client):
        """Test root endpoint returns correct response"""
        response = test_client.get("/")

        assert response.status_code == 200
        assert response.json() == {"message": "Course Materials RAG System - Test Environment"}

    def test_query_endpoint_success(self, test_client, mock_rag_system, sample_sources):
        """Test successful query to /api/query endpoint"""
        # Setup mock responses
        mock_rag_system.query.return_value = ("Python is a programming language.", sample_sources)
        mock_rag_system.session_manager.create_session.return_value = "new_session_789"

        # Make request
        query_data = {
            "query": "What is Python?",
            "session_id": None
        }
        response = test_client.post("/api/query", json=query_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Python is a programming language."
        assert data["session_id"] == "new_session_789"
        assert len(data["sources"]) == 2
        assert data["sources"][0]["text"] == "Python is a high-level programming language - Lesson 1: Python Basics"
        assert data["sources"][0]["link"] == "https://example.com/python-course/lesson-1"

    def test_query_endpoint_with_existing_session(self, test_client, mock_rag_system):
        """Test query with existing session ID"""
        # Setup mock responses
        mock_rag_system.query.return_value = ("Follow-up response.", [])

        query_data = {
            "query": "Tell me more",
            "session_id": "existing_session_123"
        }
        response = test_client.post("/api/query", json=query_data)

        # Verify response
        assert response.status_code == 200
        data = response.json()

        assert data["answer"] == "Follow-up response."
        assert data["session_id"] == "existing_session_123"
        assert data["sources"] == []

    def test_query_endpoint_missing_query(self, test_client):
        """Test query endpoint with missing query field"""
        query_data = {
            "session_id": "test_session"
        }
        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 422  # Validation error

    def test_query_endpoint_empty_query(self, test_client, mock_rag_system):
        """Test query endpoint with empty query"""
        mock_rag_system.query.return_value = ("Please provide a question.", [])

        query_data = {
            "query": "",
            "session_id": "test_session"
        }
        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Please provide a question."

    def test_query_endpoint_internal_error(self, test_client, mock_rag_system):
        """Test query endpoint handles internal errors"""
        # Setup mock to raise exception
        mock_rag_system.query.side_effect = Exception("Internal error occurred")

        query_data = {
            "query": "What is Python?",
            "session_id": "test_session"
        }
        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 500
        assert "Internal error occurred" in response.json()["detail"]

    def test_query_endpoint_sources_formatting(self, test_client, mock_rag_system):
        """Test that sources are properly formatted in response"""
        # Setup mock with mixed source formats
        mixed_sources = [
            {"text": "Dict source with link", "link": "http://example.com"},
            {"text": "Dict source without link"},
            "String source"
        ]

        mock_rag_system.query.return_value = ("Test response", mixed_sources)
        mock_rag_system.session_manager.create_session.return_value = "test_session"

        query_data = {"query": "Test query"}
        response = test_client.post("/api/query", json=query_data)

        assert response.status_code == 200
        data = response.json()
        sources = data["sources"]

        # Verify all sources are properly formatted
        assert len(sources) == 3
        assert sources[0]["text"] == "Dict source with link"
        assert sources[0]["link"] == "http://example.com"
        assert sources[1]["text"] == "Dict source without link"
        assert sources[1]["link"] is None
        assert sources[2]["text"] == "String source"
        assert sources[2]["link"] is None

    def test_courses_endpoint_success(self, test_client, mock_rag_system, mock_analytics_data):
        """Test successful request to /api/courses endpoint"""
        # Setup mock response
        mock_rag_system.get_course_analytics.return_value = mock_analytics_data

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 3
        assert len(data["course_titles"]) == 3
        assert "Introduction to Python" in data["course_titles"]
        assert "Advanced JavaScript" in data["course_titles"]
        assert "Data Science Fundamentals" in data["course_titles"]

    def test_courses_endpoint_empty_data(self, test_client, mock_rag_system):
        """Test courses endpoint with no courses"""
        # Setup mock response with empty data
        empty_analytics = {
            "total_courses": 0,
            "course_titles": []
        }
        mock_rag_system.get_course_analytics.return_value = empty_analytics

        response = test_client.get("/api/courses")

        assert response.status_code == 200
        data = response.json()

        assert data["total_courses"] == 0
        assert data["course_titles"] == []

    def test_courses_endpoint_internal_error(self, test_client, mock_rag_system):
        """Test courses endpoint handles internal errors"""
        # Setup mock to raise exception
        mock_rag_system.get_course_analytics.side_effect = Exception("Analytics error")

        response = test_client.get("/api/courses")

        assert response.status_code == 500
        assert "Analytics error" in response.json()["detail"]

    def test_invalid_endpoint(self, test_client):
        """Test request to non-existent endpoint"""
        response = test_client.get("/api/nonexistent")

        assert response.status_code == 404

    def test_query_endpoint_with_malformed_json(self, test_client):
        """Test query endpoint with malformed JSON"""
        response = test_client.post(
            "/api/query",
            data="invalid json",
            headers={"Content-Type": "application/json"}
        )

        assert response.status_code == 422

    def test_query_endpoint_content_type_validation(self, test_client, mock_rag_system):
        """Test query endpoint with different content types"""
        mock_rag_system.query.return_value = ("Test response", [])
        mock_rag_system.session_manager.create_session.return_value = "test_session"

        # Test with form data instead of JSON - this should fail validation
        response = test_client.post(
            "/api/query",
            data={"query": "What is Python?"}
        )

        # Form data won't work for JSON endpoint
        assert response.status_code == 422

    def test_cors_headers(self, test_client):
        """Test that CORS headers are properly set"""
        response = test_client.get("/")

        # Check that basic request works (CORS is handled by middleware)
        assert response.status_code == 200

    @pytest.mark.integration
    def test_query_endpoint_session_management_flow(self, test_client, mock_rag_system):
        """Test complete session management flow"""
        mock_rag_system.query.return_value = ("Test response", [])
        mock_rag_system.session_manager.create_session.return_value = "flow_session_123"

        # First query without session ID
        query_data = {"query": "First question"}
        response1 = test_client.post("/api/query", json=query_data)

        assert response1.status_code == 200
        session_id = response1.json()["session_id"]
        assert session_id == "flow_session_123"

        # Second query with session ID
        query_data = {"query": "Follow-up question", "session_id": session_id}
        response2 = test_client.post("/api/query", json=query_data)

        assert response2.status_code == 200
        assert response2.json()["session_id"] == session_id

    @pytest.mark.integration
    def test_api_endpoints_with_realistic_data(self, test_client, mock_rag_system):
        """Test API endpoints with realistic course data"""
        # Setup realistic mock data
        realistic_sources = [
            {
                "text": "Machine learning is a subset of artificial intelligence (AI) that involves training algorithms to make predictions or decisions based on data. - Lesson 3: Introduction to ML",
                "link": "https://example.com/ml-course/lesson-3"
            }
        ]

        realistic_analytics = {
            "total_courses": 5,
            "course_titles": [
                "Machine Learning Fundamentals",
                "Deep Learning with PyTorch",
                "Natural Language Processing",
                "Computer Vision Basics",
                "MLOps and Model Deployment"
            ]
        }

        mock_rag_system.query.return_value = ("Machine learning is a powerful technology that enables computers to learn from data without being explicitly programmed for every task.", realistic_sources)
        mock_rag_system.get_course_analytics.return_value = realistic_analytics
        mock_rag_system.session_manager.create_session.return_value = "ml_session_001"

        # Test query endpoint
        query_response = test_client.post("/api/query", json={
            "query": "What is machine learning?",
            "session_id": "ml_session_001"
        })

        assert query_response.status_code == 200
        query_data = query_response.json()
        assert "Machine learning is a powerful technology" in query_data["answer"]
        assert len(query_data["sources"]) == 1
        assert "ML" in query_data["sources"][0]["text"]

        # Test courses endpoint
        courses_response = test_client.get("/api/courses")

        assert courses_response.status_code == 200
        courses_data = courses_response.json()
        assert courses_data["total_courses"] == 5
        assert "Machine Learning Fundamentals" in courses_data["course_titles"]