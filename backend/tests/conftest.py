import pytest
import sys
import os
from unittest.mock import Mock, patch
from fastapi.testclient import TestClient

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config
from rag_system import RAGSystem
from vector_store import VectorStore
from models import Course, Lesson


@pytest.fixture
def mock_config():
    """Mock configuration for testing"""
    config = Mock(spec=Config)
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.CHROMA_PATH = "./test_chroma"
    config.EMBEDDING_MODEL = "test-model"
    config.MAX_RESULTS = 5
    config.ANTHROPIC_API_KEY = "test_key"
    config.ANTHROPIC_MODEL = "claude-sonnet-4-20250514"
    config.MAX_HISTORY = 2
    config.AI_TEMPERATURE = 0
    config.AI_MAX_TOKENS = 800
    return config


@pytest.fixture
def mock_rag_system(mock_config):
    """Mock RAG system for testing"""
    with patch('rag_system.DocumentProcessor') as mock_doc_proc, \
         patch('rag_system.VectorStore') as mock_vector_store, \
         patch('rag_system.AIGenerator') as mock_ai_gen, \
         patch('rag_system.SessionManager') as mock_session_mgr:

        mock_document_processor = Mock()
        mock_vector_store_instance = Mock()
        mock_ai_generator = Mock()
        mock_session_manager = Mock()

        mock_doc_proc.return_value = mock_document_processor
        mock_vector_store.return_value = mock_vector_store_instance
        mock_ai_gen.return_value = mock_ai_generator
        mock_session_mgr.return_value = mock_session_manager

        rag_system = RAGSystem(mock_config)

        # Store mocks as attributes for easy access in tests
        rag_system._mock_document_processor = mock_document_processor
        rag_system._mock_vector_store = mock_vector_store_instance
        rag_system._mock_ai_generator = mock_ai_generator
        rag_system._mock_session_manager = mock_session_manager

        # Mock the query and get_course_analytics methods directly
        rag_system.query = Mock(return_value=("Test response", []))
        rag_system.get_course_analytics = Mock(return_value={"total_courses": 0, "course_titles": []})

        return rag_system


@pytest.fixture
def test_app(mock_rag_system):
    """Create test FastAPI app without static file mounting"""
    from fastapi import FastAPI, HTTPException
    from fastapi.middleware.cors import CORSMiddleware
    from fastapi.middleware.trustedhost import TrustedHostMiddleware
    from pydantic import BaseModel
    from typing import List, Optional

    # Create test app without static file mounting
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add middleware
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*"]
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
    )

    # Pydantic models
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class SourceData(BaseModel):
        text: str
        link: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[SourceData]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    # API Endpoints
    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request: QueryRequest):
        try:
            session_id = request.session_id
            if not session_id:
                session_id = mock_rag_system.session_manager.create_session()

            answer, sources = mock_rag_system.query(request.query, session_id)

            formatted_sources = []
            for source in sources:
                if isinstance(source, dict):
                    formatted_sources.append(SourceData(
                        text=source.get("text", str(source)),
                        link=source.get("link")
                    ))
                else:
                    formatted_sources.append(SourceData(text=str(source)))

            return QueryResponse(
                answer=answer,
                sources=formatted_sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats():
        try:
            analytics = mock_rag_system.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def read_root():
        return {"message": "Course Materials RAG System - Test Environment"}

    return app


@pytest.fixture
def test_client(test_app):
    """Create test client for FastAPI app"""
    return TestClient(test_app)


@pytest.fixture
def sample_course():
    """Sample course data for testing"""
    return Course(
        title="Introduction to Python",
        instructor="John Doe",
        course_link="https://example.com/python-course",
        lessons=[
            Lesson(
                lesson_number=1,
                title="Python Basics",
                lesson_link="https://example.com/python-course/lesson-1"
            ),
            Lesson(
                lesson_number=2,
                title="Data Types",
                lesson_link="https://example.com/python-course/lesson-2"
            )
        ]
    )


@pytest.fixture
def sample_query_request():
    """Sample query request data"""
    return {
        "query": "What is Python?",
        "session_id": "test_session_123"
    }


@pytest.fixture
def sample_sources():
    """Sample source data for testing"""
    return [
        {
            "text": "Python is a high-level programming language - Lesson 1: Python Basics",
            "link": "https://example.com/python-course/lesson-1"
        },
        {
            "text": "Python supports multiple programming paradigms - Lesson 2: Data Types",
            "link": "https://example.com/python-course/lesson-2"
        }
    ]


@pytest.fixture
def mock_analytics_data():
    """Mock course analytics data"""
    return {
        "total_courses": 3,
        "course_titles": [
            "Introduction to Python",
            "Advanced JavaScript",
            "Data Science Fundamentals"
        ]
    }


@pytest.fixture(autouse=True)
def cleanup_test_files():
    """Cleanup test files after each test"""
    yield
    # Cleanup any test files if needed
    test_paths = ["./test_chroma", "./test_docs"]
    for path in test_paths:
        if os.path.exists(path):
            import shutil
            shutil.rmtree(path, ignore_errors=True)


@pytest.fixture
def mock_session_manager():
    """Mock session manager for testing"""
    manager = Mock()
    manager.create_session.return_value = "test_session_456"
    manager.get_conversation_history.return_value = None
    manager.add_exchange.return_value = None
    return manager


@pytest.fixture
def mock_vector_store():
    """Mock vector store for testing"""
    store = Mock()
    store.search.return_value = []
    store.add_course_metadata.return_value = None
    store.add_course_content.return_value = None
    store.get_course_count.return_value = 0
    store.get_existing_course_titles.return_value = []
    store.clear_all_data.return_value = None
    return store


@pytest.fixture
def mock_ai_generator():
    """Mock AI generator for testing"""
    generator = Mock()
    generator.generate_response.return_value = "This is a test AI response."
    return generator