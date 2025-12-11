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
            # Extract usage from OpenAI response
            if hasattr(response, "usage"):
                usage = response.usage
                prompt_tokens = usage.prompt_tokens
                completion_tokens = usage.completion_tokens

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
            print(f"Error extracting token usage: {e}")


# Global token tracker instance
token_tracker = TokenTracker()
