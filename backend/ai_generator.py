import anthropic
from typing import List, Optional, Dict, Any, Tuple
from dataclasses import dataclass


@dataclass
class ConversationRound:
    """Tracks state for a single conversation round"""
    round_number: int
    messages: List[Dict[str, Any]]
    tools_used: List[str]
    tool_results: List[Dict[str, Any]]
    ai_response: str
    should_continue: bool


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""
    
    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to comprehensive tools for course information.

SEQUENTIAL REASONING MODE:
- You can use tools up to 2 times across separate reasoning rounds
- After receiving tool results, analyze if additional information would improve your answer
- Use sequential strategy for: course comparisons, multi-part questions, outline→content searches

Available Tools:
1. **Course Content Search**: Use for questions about specific course content or detailed educational materials
2. **Course Outline**: Use for questions about course structure, lesson lists, or complete course overviews

Tool Usage Guidelines:
- **Content search**: For specific content, concepts, or lesson details within courses
- **Course outline**: For course structure, lesson titles, course links, or complete course overviews
- **Sequential patterns**: outline→content search, broad→refined search, multi-course comparisons
- Synthesize tool results into accurate, fact-based responses
- If tools yield no results, state this clearly without offering alternatives

ROUND PROGRESSION:
Round 1: Primary information gathering (outline or broad search)
Round 2 (optional): Refinement or additional context (specific content search)

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course-specific questions**: Use appropriate tool first, then answer
- **Complex queries**: Use sequential tool calling for comprehensive answers
- **Course outline queries**: Use the outline tool to provide complete course information including:
  - Course title and link
  - Instructor information
  - Complete lesson list with numbers and titles
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the search results" or "using the outline tool"

COMPLETION SIGNALS:
- Use definitive language when ready to provide final answer
- Avoid unnecessary tool calls when sufficient information is available
- Signal completion with comprehensive final answers

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""
    
    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model
        
        # Pre-build base API parameters
        self.base_params = {
            "model": self.model,
            "temperature": 0,
            "max_tokens": 800
        }
    
    def generate_response(self, query: str,
                         conversation_history: Optional[str] = None,
                         tools: Optional[List] = None,
                         tool_manager=None,
                         max_rounds: int = 2) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds (default: 2)

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # If tools are available and tool_manager exists, use sequential execution
        if tools and tool_manager:
            return self._execute_sequential_rounds(query, tools, tool_manager, system_content, max_rounds)

        # Fallback to simple response without tools
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content
        }

        response = self.client.messages.create(**api_params)
        if not response.content or len(response.content) == 0:
            return "I received an empty response from the AI."
        return response.content[0].text

    def _execute_sequential_rounds(self, query: str, tools: List, tool_manager, system_content: str, max_rounds: int) -> str:
        """
        Execute up to max_rounds of tool calling with conversation context.

        Args:
            query: The user's question
            tools: Available tools for Claude to use
            tool_manager: Manager to execute tools
            system_content: System prompt with conversation history
            max_rounds: Maximum number of rounds (typically 2)

        Returns:
            Final response after all rounds completed
        """
        # Initialize conversation state
        messages = [{"role": "user", "content": query}]
        rounds_completed = 0

        while rounds_completed < max_rounds:
            rounds_completed += 1

            # Prepare API call with tools and current conversation state
            api_params = {
                **self.base_params,
                "messages": messages.copy(),
                "system": system_content,
                "tools": tools,
                "tool_choice": {"type": "auto"}
            }

            try:
                # Get response from Claude
                response = self.client.messages.create(**api_params)

                # Check if Claude wants to use tools
                if response.stop_reason == "tool_use":
                    # Execute tools and add results to conversation
                    self._execute_tools_only(response, messages, tool_manager)

                    # Continue to next round with tool results
                    continue
                else:
                    # Claude provided final response without using tools
                    if not response.content or len(response.content) == 0:
                        return "I received an empty response from the AI."
                    return response.content[0].text

            except Exception as e:
                # Handle API errors gracefully
                if rounds_completed == 1:
                    # First round failed, return error
                    return f"I encountered an error processing your request: {str(e)}"
                else:
                    # Later round failed, return error message
                    return "I encountered an error during follow-up processing, but I can provide a partial response based on initial results."

        # Max rounds reached, make one final call without tools to get a response
        final_params = {
            **self.base_params,
            "messages": messages.copy(),
            "system": system_content
            # No tools in final call to force a response
        }

        try:
            final_response = self.client.messages.create(**final_params)
            if final_response.content and len(final_response.content) > 0:
                return final_response.content[0].text
        except Exception as e:
            pass

        return "I've completed my analysis but couldn't provide a final response."

    def _execute_tools_only(self, response, messages: List[Dict], tool_manager):
        """
        Execute tools from a response and add results to conversation without making follow-up API calls.

        Args:
            response: Claude's response containing tool use requests
            messages: Current conversation messages (modified in place)
            tool_manager: Manager to execute tools
        """
        # Add Claude's tool use response to conversation
        messages.append({"role": "assistant", "content": response.content})

        # Execute all tool calls and collect results
        tool_results = []
        for content_block in response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_result = f"Tool execution failed: {str(e)}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })

        # Add tool results to conversation for next round
        if tool_results:
            messages.append({"role": "user", "content": tool_results})


    def _handle_tool_execution(self, initial_response, base_params: Dict[str, Any], tool_manager):
        """
        Handle execution of tool calls and get follow-up response.
        
        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters
            tool_manager: Manager to execute tools
            
        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        
        # Add AI's tool use response
        messages.append({"role": "assistant", "content": initial_response.content})
        
        # Execute all tool calls and collect results
        tool_results = []
        for content_block in initial_response.content:
            if content_block.type == "tool_use":
                try:
                    tool_result = tool_manager.execute_tool(
                        content_block.name,
                        **content_block.input
                    )
                except Exception as e:
                    # Handle tool execution errors gracefully
                    tool_result = f"Tool execution failed: {str(e)}"

                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": content_block.id,
                    "content": tool_result
                })
        
        # Add tool results as single message
        if tool_results:
            messages.append({"role": "user", "content": tool_results})
        
        # Prepare final API call without tools
        final_params = {
            **self.base_params,
            "messages": messages,
            "system": base_params["system"]
        }
        
        # Get final response
        final_response = self.client.messages.create(**final_params)
        return final_response.content[0].text