"""
Token Usage and Cost Tracking
"""

from typing import Dict, Any, Optional
import config
from mcp_client import mcp_client


class TokenTracker:
    def __init__(self):
        self.model = config.OPENAI_CONFIG["model"]
        self.costs = config.TOKEN_COSTS.get(self.model, config.TOKEN_COSTS["gpt-5-mini"])

    def calculate_cost(self, prompt_tokens: int, completion_tokens: int) -> float:
        """Calculate cost for token usage"""
        input_cost = (prompt_tokens / 1_000_000) * self.costs["input"]
        output_cost = (completion_tokens / 1_000_000) * self.costs["output"]
        return round(input_cost + output_cost, 6)

    def log_usage(
        self,
        agent_name: str,
        operation: str,
        prompt_tokens: int,
        completion_tokens: int,
        sku_id: Optional[int] = None,
        promotion_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Log token usage to database via MCP"""
        total_tokens = prompt_tokens + completion_tokens
        estimated_cost = self.calculate_cost(prompt_tokens, completion_tokens)

        try:
            mcp_client.call_tool(
                "postgres",
                "log_token_usage",
                {
                    "agent_name": agent_name,
                    "operation": operation,
                    "model": self.model,
                    "prompt_tokens": prompt_tokens,
                    "completion_tokens": completion_tokens,
                    "total_tokens": total_tokens,
                    "estimated_cost": estimated_cost,
                    "sku_id": sku_id,
                    "promotion_id": promotion_id,
                    "context": context or {},
                },
            )
        except Exception as e:
            print(f"Error logging token usage: {e}")

    def extract_and_log(
        self,
        response: Any,
        agent_name: str,
        operation: str,
        sku_id: Optional[int] = None,
        promotion_id: Optional[int] = None,
        context: Optional[Dict[str, Any]] = None,
    ):
        """Extract token usage from LLM response and log it"""
        try:
            prompt_tokens = 0
            completion_tokens = 0

            # Extract usage from OpenAI response - try multiple formats
            if hasattr(response, "usage_metadata"):
                # LangChain response format (newer)
                usage = response.usage_metadata
                prompt_tokens = usage.get("input_tokens", 0)
                completion_tokens = usage.get("output_tokens", 0)
            elif hasattr(response, "response_metadata") and "token_usage" in response.response_metadata:
                # LangChain AIMessage format with response_metadata
                usage = response.response_metadata["token_usage"]
                prompt_tokens = usage.get("prompt_tokens", 0)
                completion_tokens = usage.get("completion_tokens", 0)
            elif hasattr(response, "additional_kwargs") and response.additional_kwargs:
                # Check additional_kwargs for usage info
                kwargs = response.additional_kwargs
                if "usage" in kwargs:
                    usage = kwargs["usage"]
                    prompt_tokens = usage.get("prompt_tokens", 0)
                    completion_tokens = usage.get("completion_tokens", 0)
                else:
                    print(f"[Token Tracker] Warning: No usage info in additional_kwargs: {kwargs}")
                    return
            elif hasattr(response, "usage"):
                # OpenAI direct response format
                usage = response.usage
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens
            else:
                print(f"[Token Tracker] Warning: Could not extract token usage from response type {type(response)}")
                return

            if prompt_tokens == 0 and completion_tokens == 0:
                print(f"[Token Tracker] Warning: Token counts are zero")
                return

            print(f"[Token Tracker] Logging: {prompt_tokens} prompt + {completion_tokens} completion tokens")

            self.log_usage(
                agent_name=agent_name,
                operation=operation,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                sku_id=sku_id,
                promotion_id=promotion_id,
                context=context,
            )
        except Exception as e:
            print(f"[Token Tracker] Error extracting token usage: {e}")
            import traceback
            traceback.print_exc()


# Global token tracker instance
token_tracker = TokenTracker()
