import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from models import Course, Lesson
from rag_system import RAGSystem
from vector_store import SearchResults


class TestRAGSystem:
    """Test suite for RAG System content-query handling"""

    def setup_method(self):
        """Set up test fixtures"""
        # Mock config
        self.mock_config = Mock()
        self.mock_config.CHUNK_SIZE = 800
        self.mock_config.CHUNK_OVERLAP = 100
        self.mock_config.CHROMA_PATH = "./test_chroma"
        self.mock_config.EMBEDDING_MODEL = "test-model"
        self.mock_config.MAX_RESULTS = 5
        self.mock_config.ANTHROPIC_API_KEY = "test_key"
        self.mock_config.ANTHROPIC_MODEL = "test_model"
        self.mock_config.MAX_HISTORY = 2

        # Patch all dependencies
        with (
            patch("rag_system.DocumentProcessor") as mock_doc_proc,
            patch("rag_system.VectorStore") as mock_vector_store,
            patch("rag_system.AIGenerator") as mock_ai_gen,
            patch("rag_system.SessionManager") as mock_session_mgr,
        ):

            self.mock_document_processor = Mock()
            self.mock_vector_store = Mock()
            self.mock_ai_generator = Mock()
            self.mock_session_manager = Mock()

            mock_doc_proc.return_value = self.mock_document_processor
            mock_vector_store.return_value = self.mock_vector_store
            mock_ai_gen.return_value = self.mock_ai_generator
            mock_session_mgr.return_value = self.mock_session_manager

            self.rag_system = RAGSystem(self.mock_config)

    def test_initialization(self):
        """Test RAG system initialization"""
        assert self.rag_system.config == self.mock_config
        assert hasattr(self.rag_system, "tool_manager")
        assert hasattr(self.rag_system, "search_tool")
        assert hasattr(self.rag_system, "outline_tool")

        # Verify tools are registered
        assert "search_course_content" in self.rag_system.tool_manager.tools
        assert "get_course_outline" in self.rag_system.tool_manager.tools

    def test_query_content_search_success(self):
        """Test successful content search query"""
        # Mock search tool results
        self.rag_system.search_tool.last_sources = [
            {"text": "Test Course - Lesson 1", "link": "http://test.com"}
        ]

        # Mock AI generator response
        self.mock_ai_generator.generate_response.return_value = "AI generated response"

        # Mock session manager
        self.mock_session_manager.get_conversation_history.return_value = None

        result_response, result_sources = self.rag_system.query(
            "What is MCP?", "session_123"
        )

        # Verify AI generator was called with correct parameters
        self.mock_ai_generator.generate_response.assert_called_once()
        call_args = self.mock_ai_generator.generate_response.call_args

        assert (
            call_args[1]["query"]
            == "Answer this question about course materials: What is MCP?"
        )
        assert call_args[1]["conversation_history"] is None
        assert "tools" in call_args[1]
        assert "tool_manager" in call_args[1]

        # Verify session management
        self.mock_session_manager.get_conversation_history.assert_called_once_with(
            "session_123"
        )
        self.mock_session_manager.add_exchange.assert_called_once_with(
            "session_123", "What is MCP?", "AI generated response"
        )

        # Check results
        assert result_response == "AI generated response"
        assert len(result_sources) == 1
        assert result_sources[0]["text"] == "Test Course - Lesson 1"

    def test_query_with_conversation_history(self):
        """Test query with existing conversation history"""
        # Mock conversation history
        mock_history = "Previous conversation context"
        self.mock_session_manager.get_conversation_history.return_value = mock_history

        self.mock_ai_generator.generate_response.return_value = "Response with context"

        result_response, result_sources = self.rag_system.query(
            "Follow-up question", "session_123"
        )

        # Verify history was passed to AI generator
        call_args = self.mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] == mock_history

    def test_query_without_session(self):
        """Test query without session ID"""
        self.mock_ai_generator.generate_response.return_value = (
            "Response without session"
        )

        result_response, result_sources = self.rag_system.query("What is Python?")

        # Verify no session operations
        self.mock_session_manager.get_conversation_history.assert_not_called()
        self.mock_session_manager.add_exchange.assert_not_called()

        # Verify AI generator called without history
        call_args = self.mock_ai_generator.generate_response.call_args
        assert call_args[1]["conversation_history"] is None

    def test_query_outline_request(self):
        """Test query that should trigger outline tool"""
        self.mock_ai_generator.generate_response.return_value = (
            "Course outline response"
        )

        result_response, result_sources = self.rag_system.query(
            "What is the outline of MCP course?"
        )

        # Verify tools are available for outline queries
        call_args = self.mock_ai_generator.generate_response.call_args
        tools = call_args[1]["tools"]

        # Should have both search and outline tools
        tool_names = [tool["name"] for tool in tools]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

    def test_sources_reset_after_query(self):
        """Test that sources are reset after each query"""
        # Set up initial sources
        self.rag_system.search_tool.last_sources = [
            {"text": "Test", "link": "http://test.com"}
        ]
        self.rag_system.outline_tool.last_sources = []

        self.mock_ai_generator.generate_response.return_value = "Test response"

        # Execute query
        self.rag_system.query("Test query")

        # Verify sources were reset
        assert self.rag_system.search_tool.last_sources == []

    def test_add_course_document_success(self):
        """Test successful course document addition"""
        # Mock course and chunks
        mock_course = Course(
            title="Test Course",
            instructor="Test Instructor",
            course_link="http://test.com",
            lessons=[
                Lesson(
                    lesson_number=1, title="Lesson 1", lesson_link="http://test.com/1"
                )
            ],
        )
        mock_chunks = [Mock(), Mock()]

        self.mock_document_processor.process_course_document.return_value = (
            mock_course,
            mock_chunks,
        )

        course, chunk_count = self.rag_system.add_course_document("test_file.pdf")

        # Verify document processing
        self.mock_document_processor.process_course_document.assert_called_once_with(
            "test_file.pdf"
        )

        # Verify vector store operations
        self.mock_vector_store.add_course_metadata.assert_called_once_with(mock_course)
        self.mock_vector_store.add_course_content.assert_called_once_with(mock_chunks)

        # Check results
        assert course == mock_course
        assert chunk_count == 2

    def test_add_course_document_error(self):
        """Test error handling in course document addition"""
        self.mock_document_processor.process_course_document.side_effect = Exception(
            "Processing failed"
        )

        course, chunk_count = self.rag_system.add_course_document("bad_file.pdf")

        assert course is None
        assert chunk_count == 0

    def test_add_course_folder_success(self):
        """Test successful course folder processing"""
        # Mock file system
        with (
            patch("rag_system.os.path.exists") as mock_exists,
            patch("rag_system.os.path.isfile") as mock_isfile,
            patch("rag_system.os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.pdf", "course2.txt", "ignore.jpg"]
            mock_isfile.side_effect = lambda x: x.endswith((".pdf", ".txt"))

            # Mock existing courses
            self.mock_vector_store.get_existing_course_titles.return_value = []

            # Mock course processing
            mock_course1 = Course(
                title="Course 1", instructor="Instructor 1", course_link="", lessons=[]
            )
            mock_course2 = Course(
                title="Course 2", instructor="Instructor 2", course_link="", lessons=[]
            )

            self.mock_document_processor.process_course_document.side_effect = [
                (mock_course1, [Mock(), Mock()]),  # 2 chunks
                (mock_course2, [Mock()]),  # 1 chunk
            ]

            total_courses, total_chunks = self.rag_system.add_course_folder(
                "test_folder"
            )

            # Verify processing
            assert self.mock_document_processor.process_course_document.call_count == 2
            assert total_courses == 2
            assert total_chunks == 3

    def test_add_course_folder_skip_existing(self):
        """Test skipping existing courses in folder processing"""
        with (
            patch("rag_system.os.path.exists") as mock_exists,
            patch("rag_system.os.path.isfile") as mock_isfile,
            patch("rag_system.os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.pdf"]
            mock_isfile.return_value = True

            # Mock existing course
            self.mock_vector_store.get_existing_course_titles.return_value = [
                "Existing Course"
            ]

            mock_course = Course(
                title="Existing Course", instructor="Test", course_link="", lessons=[]
            )
            self.mock_document_processor.process_course_document.return_value = (
                mock_course,
                [Mock()],
            )

            total_courses, total_chunks = self.rag_system.add_course_folder(
                "test_folder"
            )

            # Should skip existing course
            assert total_courses == 0
            assert total_chunks == 0
            self.mock_vector_store.add_course_metadata.assert_not_called()

    def test_add_course_folder_clear_existing(self):
        """Test clearing existing data before folder processing"""
        with (
            patch("rag_system.os.path.exists") as mock_exists,
            patch("rag_system.os.path.isfile") as mock_isfile,
            patch("rag_system.os.listdir") as mock_listdir,
        ):

            mock_exists.return_value = True
            mock_listdir.return_value = ["course1.pdf"]
            mock_isfile.return_value = True

            mock_course = Course(
                title="Course 1", instructor="Test", course_link="", lessons=[]
            )
            self.mock_document_processor.process_course_document.return_value = (
                mock_course,
                [Mock()],
            )
            self.mock_vector_store.get_existing_course_titles.return_value = []

            self.rag_system.add_course_folder("test_folder", clear_existing=True)

            # Verify data was cleared
            self.mock_vector_store.clear_all_data.assert_called_once()

    def test_add_course_folder_nonexistent(self):
        """Test handling nonexistent folder"""
        with patch("rag_system.os.path.exists") as mock_exists:
            mock_exists.return_value = False

            total_courses, total_chunks = self.rag_system.add_course_folder(
                "nonexistent_folder"
            )

            assert total_courses == 0
            assert total_chunks == 0

    def test_get_course_analytics(self):
        """Test course analytics retrieval"""
        self.mock_vector_store.get_course_count.return_value = 3
        self.mock_vector_store.get_existing_course_titles.return_value = [
            "Course A",
            "Course B",
            "Course C",
        ]

        analytics = self.rag_system.get_course_analytics()

        assert analytics["total_courses"] == 3
        assert len(analytics["course_titles"]) == 3
        assert "Course A" in analytics["course_titles"]

    def test_tool_integration_in_query(self):
        """Test that tools are properly integrated in query processing"""
        self.mock_ai_generator.generate_response.return_value = "Tool-enhanced response"

        self.rag_system.query("Test query")

        # Verify tools were passed to AI generator
        call_args = self.mock_ai_generator.generate_response.call_args
        tools = call_args[1]["tools"]

        # Should have exactly 2 tools
        assert len(tools) == 2

        # Check tool names
        tool_names = [tool["name"] for tool in tools]
        assert "search_course_content" in tool_names
        assert "get_course_outline" in tool_names

        # Verify tool manager was passed
        assert call_args[1]["tool_manager"] == self.rag_system.tool_manager

    def test_error_handling_in_query(self):
        """Test error handling during query processing"""
        self.mock_ai_generator.generate_response.side_effect = Exception(
            "AI API failed"
        )

        # Should not raise exception, should handle gracefully
        with pytest.raises(Exception):
            self.rag_system.query("Test query")

    def test_prompt_formatting(self):
        """Test that prompts are properly formatted"""
        self.mock_ai_generator.generate_response.return_value = "Test response"

        self.rag_system.query("What is Python?")

        call_args = self.mock_ai_generator.generate_response.call_args
        query_param = call_args[1]["query"]

        # Should format query with instruction
        assert (
            query_param
            == "Answer this question about course materials: What is Python?"
        )


if __name__ == "__main__":
    pytest.main([__file__])
