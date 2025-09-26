import pytest
import sys
import os
from unittest.mock import Mock, MagicMock

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager
from vector_store import SearchResults


class TestCourseSearchTool:
    """Test suite for CourseSearchTool.execute() method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.search_tool = CourseSearchTool(self.mock_vector_store)

    def test_execute_query_only_success(self):
        """Test execute with query only - successful results"""
        # Mock successful search results
        mock_results = SearchResults(
            documents=["Document 1 content", "Document 2 content"],
            metadata=[
                {"course_title": "Test Course", "lesson_number": 1},
                {"course_title": "Test Course", "lesson_number": 2}
            ],
            distances=[0.1, 0.2]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query")

        # Verify search was called correctly
        self.mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=None
        )

        # Verify result formatting
        assert "[Test Course - Lesson 1]" in result
        assert "[Test Course - Lesson 2]" in result
        assert "Document 1 content" in result
        assert "Document 2 content" in result

    def test_execute_with_course_name_success(self):
        """Test execute with query and course name"""
        mock_results = SearchResults(
            documents=["Course specific content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 3}],
            distances=[0.1]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query", course_name="MCP")

        self.mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="MCP",
            lesson_number=None
        )

        assert "[MCP Course - Lesson 3]" in result
        assert "Course specific content" in result

    def test_execute_with_lesson_number_success(self):
        """Test execute with query and lesson number"""
        mock_results = SearchResults(
            documents=["Lesson specific content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 5}],
            distances=[0.1]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query", lesson_number=5)

        self.mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name=None,
            lesson_number=5
        )

        assert "[Test Course - Lesson 5]" in result
        assert "Lesson specific content" in result

    def test_execute_with_all_parameters(self):
        """Test execute with all parameters"""
        mock_results = SearchResults(
            documents=["Specific content"],
            metadata=[{"course_title": "MCP Course", "lesson_number": 2}],
            distances=[0.1]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query", course_name="MCP", lesson_number=2)

        self.mock_vector_store.search.assert_called_once_with(
            query="test query",
            course_name="MCP",
            lesson_number=2
        )

        assert "[MCP Course - Lesson 2]" in result
        assert "Specific content" in result

    def test_execute_error_handling(self):
        """Test execute with error from vector store"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[],
            error="Database connection failed"
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query")

        assert result == "Database connection failed"

    def test_execute_empty_results(self):
        """Test execute with no search results"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("nonexistent query")

        assert result == "No relevant content found."

    def test_execute_empty_results_with_filters(self):
        """Test execute with no results but with filters"""
        mock_results = SearchResults(
            documents=[],
            metadata=[],
            distances=[]
        )
        self.mock_vector_store.search.return_value = mock_results

        result = self.search_tool.execute("test query", course_name="Nonexistent", lesson_number=99)

        assert "No relevant content found in course 'Nonexistent' in lesson 99." in result

    def test_sources_tracking(self):
        """Test that sources are properly tracked"""
        # Mock get_lesson_link method
        self.mock_vector_store.get_lesson_link.return_value = "http://example.com/lesson1"

        mock_results = SearchResults(
            documents=["Document content"],
            metadata=[{"course_title": "Test Course", "lesson_number": 1}],
            distances=[0.1]
        )
        self.mock_vector_store.search.return_value = mock_results

        self.search_tool.execute("test query")

        # Check that sources were tracked
        assert len(self.search_tool.last_sources) == 1
        source = self.search_tool.last_sources[0]
        assert source["text"] == "Test Course - Lesson 1"
        assert source["link"] == "http://example.com/lesson1"

    def test_get_tool_definition(self):
        """Test tool definition structure"""
        definition = self.search_tool.get_tool_definition()

        assert definition["name"] == "search_course_content"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["type"] == "object"
        assert "query" in definition["input_schema"]["properties"]
        assert "course_name" in definition["input_schema"]["properties"]
        assert "lesson_number" in definition["input_schema"]["properties"]
        assert definition["input_schema"]["required"] == ["query"]


class TestCourseOutlineTool:
    """Test suite for CourseOutlineTool.execute() method"""

    def setup_method(self):
        """Set up test fixtures"""
        self.mock_vector_store = Mock()
        self.outline_tool = CourseOutlineTool(self.mock_vector_store)

    def test_execute_success(self):
        """Test execute with successful outline retrieval"""
        mock_outline = {
            "title": "MCP: Build Rich-Context AI Apps",
            "course_link": "https://example.com/course",
            "instructor": "John Doe",
            "lessons": [
                {"lesson_number": 1, "lesson_title": "Introduction"},
                {"lesson_number": 2, "lesson_title": "Getting Started"}
            ]
        }
        self.mock_vector_store.get_course_outline.return_value = mock_outline

        result = self.outline_tool.execute("MCP course")

        self.mock_vector_store.get_course_outline.assert_called_once_with("MCP course")

        assert "**Course Title:** **[MCP: Build Rich-Context AI Apps](https://example.com/course)**" in result
        assert "**👨‍🏫 Instructor:** John Doe" in result
        assert "**📚 Lessons:**" in result
        assert "- Lesson 1: Introduction" in result
        assert "- Lesson 2: Getting Started" in result

    def test_execute_no_course_found(self):
        """Test execute when course is not found"""
        self.mock_vector_store.get_course_outline.return_value = None

        result = self.outline_tool.execute("Nonexistent course")

        assert result == "No course found matching 'Nonexistent course'"

    def test_execute_without_course_link(self):
        """Test execute with course that has no link"""
        mock_outline = {
            "title": "Test Course",
            "instructor": "Jane Doe",
            "lessons": []
        }
        self.mock_vector_store.get_course_outline.return_value = mock_outline

        result = self.outline_tool.execute("test")

        assert "**Course Title:** Test Course" in result
        assert "**👨‍🏫 Instructor:** Jane Doe" in result
        assert "No lessons available" in result

    def test_get_tool_definition(self):
        """Test tool definition structure"""
        definition = self.outline_tool.get_tool_definition()

        assert definition["name"] == "get_course_outline"
        assert "description" in definition
        assert "input_schema" in definition
        assert definition["input_schema"]["required"] == ["course_name"]


class TestToolManager:
    """Test suite for ToolManager"""

    def setup_method(self):
        """Set up test fixtures"""
        self.tool_manager = ToolManager()
        self.mock_tool = Mock()
        self.mock_tool.get_tool_definition.return_value = {
            "name": "test_tool",
            "description": "Test tool"
        }

    def test_register_tool(self):
        """Test tool registration"""
        self.tool_manager.register_tool(self.mock_tool)

        assert "test_tool" in self.tool_manager.tools
        assert self.tool_manager.tools["test_tool"] == self.mock_tool

    def test_register_tool_without_name(self):
        """Test registering tool without name raises error"""
        bad_tool = Mock()
        bad_tool.get_tool_definition.return_value = {"description": "No name"}

        with pytest.raises(ValueError, match="Tool must have a 'name' in its definition"):
            self.tool_manager.register_tool(bad_tool)

    def test_get_tool_definitions(self):
        """Test getting all tool definitions"""
        self.tool_manager.register_tool(self.mock_tool)

        definitions = self.tool_manager.get_tool_definitions()

        assert len(definitions) == 1
        assert definitions[0]["name"] == "test_tool"

    def test_execute_tool(self):
        """Test tool execution"""
        self.mock_tool.execute.return_value = "Tool executed successfully"
        self.tool_manager.register_tool(self.mock_tool)

        result = self.tool_manager.execute_tool("test_tool", param1="value1")

        self.mock_tool.execute.assert_called_once_with(param1="value1")
        assert result == "Tool executed successfully"

    def test_execute_nonexistent_tool(self):
        """Test executing tool that doesn't exist"""
        result = self.tool_manager.execute_tool("nonexistent_tool")

        assert result == "Tool 'nonexistent_tool' not found"

    def test_get_last_sources(self):
        """Test getting last sources from tools"""
        mock_search_tool = Mock()
        mock_search_tool.get_tool_definition.return_value = {"name": "search_tool"}
        mock_search_tool.last_sources = [{"text": "Test Source", "link": "http://test.com"}]

        self.tool_manager.register_tool(mock_search_tool)

        sources = self.tool_manager.get_last_sources()

        assert len(sources) == 1
        assert sources[0]["text"] == "Test Source"

    def test_reset_sources(self):
        """Test resetting sources from all tools"""
        mock_search_tool = Mock()
        mock_search_tool.get_tool_definition.return_value = {"name": "search_tool"}
        mock_search_tool.last_sources = [{"text": "Test Source"}]

        self.tool_manager.register_tool(mock_search_tool)
        self.tool_manager.reset_sources()

        assert mock_search_tool.last_sources == []


if __name__ == "__main__":
    pytest.main([__file__])