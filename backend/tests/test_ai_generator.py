import os
import sys
from unittest.mock import MagicMock, Mock, patch

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ai_generator import AIGenerator


class TestAIGenerator:
    """Test suite for AI Generator tool calling functionality"""

    def setup_method(self):
        """Set up test fixtures"""
        self.api_key = "test_api_key"
        self.model = "claude-sonnet-4-20250514"

        # Mock anthropic client
        with patch("ai_generator.anthropic.Anthropic") as mock_anthropic:
            self.mock_client = Mock()
            mock_anthropic.return_value = self.mock_client
            self.ai_generator = AIGenerator(self.api_key, self.model)

    def test_initialization(self):
        """Test AI generator initialization"""
        assert self.ai_generator.model == self.model
        assert self.ai_generator.base_params["model"] == self.model
        assert self.ai_generator.base_params["temperature"] == 0
        assert self.ai_generator.base_params["max_tokens"] == 800

    def test_generate_response_without_tools(self):
        """Test response generation without tools"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        result = self.ai_generator.generate_response("Test query")

        # Verify API call
        self.mock_client.messages.create.assert_called_once()
        call_args = self.mock_client.messages.create.call_args[1]

        assert call_args["model"] == self.model
        assert call_args["temperature"] == 0
        assert call_args["max_tokens"] == 800
        assert call_args["messages"][0]["role"] == "user"
        assert call_args["messages"][0]["content"] == "Test query"
        assert "tools" not in call_args

        assert result == "Test response"

    def test_generate_response_with_conversation_history(self):
        """Test response generation with conversation history"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Test response with history")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        history = "Previous conversation context"
        result = self.ai_generator.generate_response(
            "Test query", conversation_history=history
        )

        call_args = self.mock_client.messages.create.call_args[1]
        expected_system = (
            f"{self.ai_generator.SYSTEM_PROMPT}\n\nPrevious conversation:\n{history}"
        )
        assert call_args["system"] == expected_system

    def test_generate_response_with_tools_no_tool_use(self):
        """Test response generation with tools available but not used"""
        mock_response = Mock()
        mock_response.content = [Mock(text="Direct response")]
        mock_response.stop_reason = "end_turn"
        self.mock_client.messages.create.return_value = mock_response

        tools = [{"name": "test_tool", "description": "Test tool"}]
        mock_tool_manager = Mock()

        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        call_args = self.mock_client.messages.create.call_args[1]
        assert call_args["tools"] == tools
        assert call_args["tool_choice"] == {"type": "auto"}
        assert result == "Direct response"

    def test_generate_response_with_tool_use(self):
        """Test response generation with tool use"""
        # First response with tool use
        mock_tool_use_content = Mock()
        mock_tool_use_content.type = "tool_use"
        mock_tool_use_content.name = "search_course_content"
        mock_tool_use_content.input = {"query": "test search"}
        mock_tool_use_content.id = "tool_123"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_content]
        mock_initial_response.stop_reason = "tool_use"

        # Final response after tool execution
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Final response with tool results")]

        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool execution result"

        tools = [{"name": "search_course_content", "description": "Search tool"}]

        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Verify tool was executed
        mock_tool_manager.execute_tool.assert_called_once_with(
            "search_course_content", query="test search"
        )

        # Verify two API calls were made
        assert self.mock_client.messages.create.call_count == 2

        # Check final response
        assert result == "Final response with tool results"

    def test_tool_execution_handling(self):
        """Test the _handle_tool_execution method directly"""
        # Mock tool use content
        mock_tool_use_content = Mock()
        mock_tool_use_content.type = "tool_use"
        mock_tool_use_content.name = "test_tool"
        mock_tool_use_content.input = {"param": "value"}
        mock_tool_use_content.id = "tool_456"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_content]

        # Mock final response
        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Tool execution complete")]
        self.mock_client.messages.create.return_value = mock_final_response

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": self.ai_generator.SYSTEM_PROMPT,
        }

        result = self.ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Verify tool execution
        mock_tool_manager.execute_tool.assert_called_once_with(
            "test_tool", param="value"
        )

        # Verify final API call structure
        final_call_args = self.mock_client.messages.create.call_args[1]

        # Should have 3 messages: original user, assistant tool use, user tool result
        assert len(final_call_args["messages"]) == 3
        assert final_call_args["messages"][0]["role"] == "user"
        assert final_call_args["messages"][1]["role"] == "assistant"
        assert final_call_args["messages"][2]["role"] == "user"

        # Tool result should be properly formatted
        tool_result = final_call_args["messages"][2]["content"][0]
        assert tool_result["type"] == "tool_result"
        assert tool_result["tool_use_id"] == "tool_456"
        assert tool_result["content"] == "Tool result"

        assert result == "Tool execution complete"

    def test_multiple_tool_calls_in_single_response(self):
        """Test handling multiple tool calls in one response"""
        # Mock multiple tool use contents
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "tool_1"
        tool_use_1.input = {"param1": "value1"}
        tool_use_1.id = "tool_1_id"

        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "tool_2"
        tool_use_2.input = {"param2": "value2"}
        tool_use_2.id = "tool_2_id"

        mock_initial_response = Mock()
        mock_initial_response.content = [tool_use_1, tool_use_2]

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Multiple tools executed")]
        self.mock_client.messages.create.return_value = mock_final_response

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": self.ai_generator.SYSTEM_PROMPT,
        }

        result = self.ai_generator._handle_tool_execution(
            mock_initial_response, base_params, mock_tool_manager
        )

        # Verify both tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call("tool_1", param1="value1")
        mock_tool_manager.execute_tool.assert_any_call("tool_2", param2="value2")

        # Verify tool results structure
        final_call_args = self.mock_client.messages.create.call_args[1]
        tool_results = final_call_args["messages"][2]["content"]
        assert len(tool_results) == 2

    def test_system_prompt_content(self):
        """Test that system prompt contains expected content"""
        system_prompt = self.ai_generator.SYSTEM_PROMPT

        # Check for key components
        assert "course materials and educational content" in system_prompt
        assert "Course Content Search" in system_prompt
        assert "Course Outline" in system_prompt
        assert "up to 2 times across separate reasoning rounds" in system_prompt
        assert "Course outline queries" in system_prompt

    def test_api_error_handling(self):
        """Test handling of API errors"""
        self.mock_client.messages.create.side_effect = Exception("API Error")

        with pytest.raises(Exception, match="API Error"):
            self.ai_generator.generate_response("Test query")

    def test_tool_manager_error_handling(self):
        """Test handling of tool manager errors"""
        mock_tool_use_content = Mock()
        mock_tool_use_content.type = "tool_use"
        mock_tool_use_content.name = "failing_tool"
        mock_tool_use_content.input = {}
        mock_tool_use_content.id = "tool_123"

        mock_initial_response = Mock()
        mock_initial_response.content = [mock_tool_use_content]
        mock_initial_response.stop_reason = "tool_use"

        mock_final_response = Mock()
        mock_final_response.content = [Mock(text="Error handled")]
        self.mock_client.messages.create.side_effect = [
            mock_initial_response,
            mock_final_response,
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = Exception("Tool execution failed")

        tools = [{"name": "failing_tool"}]

        # Should not raise exception, should handle gracefully
        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager
        )

        # Tool should have been attempted
        mock_tool_manager.execute_tool.assert_called_once()

        # Should return a response even when tool fails
        assert result == "Error handled"

    def test_sequential_tool_calling_two_rounds(self):
        """Test sequential tool calling across 2 rounds"""
        # Round 1: Tool use
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "get_course_outline"
        tool_use_1.input = {"course_name": "MCP"}
        tool_use_1.id = "tool_1"

        response_1 = Mock()
        response_1.content = [tool_use_1]
        response_1.stop_reason = "tool_use"

        # Round 1 follow-up response (indicates need for more info)
        follow_up_1 = Mock()
        follow_up_1.content = [
            Mock(text="I need to search for more details about lesson 4")
        ]

        # Round 2: Second tool use
        tool_use_2 = Mock()
        tool_use_2.type = "tool_use"
        tool_use_2.name = "search_course_content"
        tool_use_2.input = {"query": "lesson 4 content", "course_name": "MCP"}
        tool_use_2.id = "tool_2"

        response_2 = Mock()
        response_2.content = [tool_use_2]
        response_2.stop_reason = "tool_use"

        # Final response
        final_response = Mock()
        final_response.content = [
            Mock(text="Based on the information gathered, here is the complete answer")
        ]

        # Setup API responses
        self.mock_client.messages.create.side_effect = [
            response_1,
            follow_up_1,
            response_2,
            final_response,
        ]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.side_effect = [
            "Course outline results",
            "Specific lesson content",
        ]

        tools = [{"name": "get_course_outline"}, {"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "What does lesson 4 of MCP course cover?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify two tools were executed
        assert mock_tool_manager.execute_tool.call_count == 2
        mock_tool_manager.execute_tool.assert_any_call(
            "get_course_outline", course_name="MCP"
        )
        mock_tool_manager.execute_tool.assert_any_call(
            "search_course_content", query="lesson 4 content", course_name="MCP"
        )

        # Verify final response
        assert (
            result == "Based on the information gathered, here is the complete answer"
        )

        # Verify 4 API calls were made (2 rounds × 2 calls each)
        assert self.mock_client.messages.create.call_count == 4

    def test_sequential_tool_calling_early_termination(self):
        """Test sequential tool calling that terminates after round 1"""
        # Round 1: Tool use
        tool_use_1 = Mock()
        tool_use_1.type = "tool_use"
        tool_use_1.name = "search_course_content"
        tool_use_1.input = {"query": "chatbots"}
        tool_use_1.id = "tool_1"

        response_1 = Mock()
        response_1.content = [tool_use_1]
        response_1.stop_reason = "tool_use"

        # Round 1 follow-up response (indicates completion)
        follow_up_1 = Mock()
        follow_up_1.content = [
            Mock(
                text="Based on the information gathered, chatbots are covered in the MCP course"
            )
        ]

        # Setup API responses
        self.mock_client.messages.create.side_effect = [response_1, follow_up_1]

        # Mock tool manager
        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Chatbot course content found"

        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "Which courses cover chatbots?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify only one tool was executed
        assert mock_tool_manager.execute_tool.call_count == 1

        # Verify early termination due to completion signal
        assert (
            result
            == "Based on the information gathered, chatbots are covered in the MCP course"
        )

        # Verify only 2 API calls were made (single round)
        assert self.mock_client.messages.create.call_count == 2

    def test_sequential_tool_calling_no_tools_first_round(self):
        """Test when Claude doesn't use tools in first round"""
        # Direct response without tools
        direct_response = Mock()
        direct_response.content = [
            Mock(text="This is a general knowledge question I can answer directly")
        ]
        direct_response.stop_reason = "end_turn"

        self.mock_client.messages.create.return_value = direct_response

        mock_tool_manager = Mock()
        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "What is artificial intelligence?",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=2,
        )

        # Verify no tools were executed
        mock_tool_manager.execute_tool.assert_not_called()

        # Verify only one API call was made
        assert self.mock_client.messages.create.call_count == 1

        assert result == "This is a general knowledge question I can answer directly"

    def test_sequential_tool_calling_max_rounds_enforcement(self):
        """Test that max_rounds is enforced"""
        # Mock responses that would continue indefinitely
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.input = {"query": "test"}
        tool_use.id = "tool_1"

        tool_response = Mock()
        tool_response.content = [tool_use]
        tool_response.stop_reason = "tool_use"

        follow_up = Mock()
        follow_up.content = [Mock(text="I need more information")]

        # Setup to return same pattern repeatedly
        self.mock_client.messages.create.side_effect = [
            tool_response,
            follow_up,  # Round 1
            tool_response,
            follow_up,  # Round 2
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager, max_rounds=2
        )

        # Should stop after 2 rounds
        assert mock_tool_manager.execute_tool.call_count == 2
        assert self.mock_client.messages.create.call_count == 4  # 2 rounds × 2 calls

    def test_sequential_tool_calling_with_max_rounds_parameter(self):
        """Test custom max_rounds parameter"""
        # Tool response
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.input = {"query": "test"}
        tool_use.id = "tool_1"

        tool_response = Mock()
        tool_response.content = [tool_use]
        tool_response.stop_reason = "tool_use"

        follow_up = Mock()
        follow_up.content = [Mock(text="Final answer")]

        self.mock_client.messages.create.side_effect = [tool_response, follow_up]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "Test query",
            tools=tools,
            tool_manager=mock_tool_manager,
            max_rounds=1,  # Custom limit
        )

        # Should stop after 1 round due to custom limit
        assert mock_tool_manager.execute_tool.call_count == 1
        assert result == "Final answer"

    def test_sequential_error_handling_first_round(self):
        """Test error handling in first round"""
        self.mock_client.messages.create.side_effect = Exception("API Error in round 1")

        mock_tool_manager = Mock()
        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager, max_rounds=2
        )

        assert "I encountered an error processing your request" in result

    def test_sequential_error_handling_second_round(self):
        """Test error handling in second round"""
        # First round succeeds
        tool_use = Mock()
        tool_use.type = "tool_use"
        tool_use.name = "search_course_content"
        tool_use.input = {"query": "test"}
        tool_use.id = "tool_1"

        response_1 = Mock()
        response_1.content = [tool_use]
        response_1.stop_reason = "tool_use"

        follow_up_1 = Mock()
        follow_up_1.content = [Mock(text="I need more information")]

        # Second round fails
        self.mock_client.messages.create.side_effect = [
            response_1,
            follow_up_1,
            Exception("API Error in round 2"),
        ]

        mock_tool_manager = Mock()
        mock_tool_manager.execute_tool.return_value = "Tool result"

        tools = [{"name": "search_course_content"}]

        result = self.ai_generator.generate_response(
            "Test query", tools=tools, tool_manager=mock_tool_manager, max_rounds=2
        )

        # Should handle second round error gracefully
        assert "error during follow-up processing" in result


if __name__ == "__main__":
    pytest.main([__file__])
