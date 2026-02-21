"""
LangGraph Agent Configuration
"""

import os


def _env_bool(name: str, default: str = "false") -> bool:
    return os.getenv(name, default).lower() == "true"


# Agent Behavior Configuration
AGENT_CONFIG = {
    "monitoring_interval_minutes": int(os.getenv("AGENT_MONITORING_INTERVAL_MINUTES", 30)),
    "min_margin_percent": float(os.getenv("AGENT_MIN_MARGIN_PERCENT", 10)),
    "max_discount_percent": float(os.getenv("AGENT_MAX_DISCOUNT_PERCENT", 40)),
    "auto_retract_threshold": float(os.getenv("AGENT_AUTO_RETRACT_THRESHOLD", 0.5)),
    "require_manual_approval": _env_bool("AGENT_REQUIRE_MANUAL_APPROVAL", "false"),
    "optimization_max_iterations": int(os.getenv("OPTIMIZATION_MAX_ITERATIONS", 3)),
    "optimization_objective": os.getenv("OPTIMIZATION_OBJECTIVE", "profit_maximization"),
}

# Feature Flags (default to legacy behavior)
FEATURE_FLAGS = {
    "enable_decision_learning": _env_bool("ENABLE_DECISION_LEARNING", "false"),
    "enable_optimization_loop": _env_bool("ENABLE_OPTIMIZATION_LOOP", "false"),
    "enable_multi_critic": _env_bool("ENABLE_MULTI_CRITIC", "false"),
    "enable_approval_learning": _env_bool("ENABLE_APPROVAL_LEARNING", "false"),
    "enable_rag_similarity": _env_bool("ENABLE_RAG_SIMILARITY", "false"),
}

# OpenAI Configuration
OPENAI_CONFIG = {
    "api_key": os.getenv("OPENAI_API_KEY"),
    "model": os.getenv("OPENAI_MODEL", "gpt-5-mini"),
    # Note: gpt-5-mini only supports temperature=1.0 (default)
    "max_tokens": 1500,
}

# LangSmith Configuration
LANGSMITH_CONFIG = {
    "api_key": os.getenv("LANGSMITH_API_KEY"),
    "project": os.getenv("LANGSMITH_PROJECT", "pricing-intelligence-agent"),
    "tracing": os.getenv("LANGSMITH_TRACING", "true").lower() == "true",
}

# MCP Server URLs
MCP_SERVERS = {
    "postgres": os.getenv("MCP_POSTGRES_URL", "http://mcp-postgres:3000"),
    "weather": os.getenv("MCP_WEATHER_URL", "http://mcp-weather:3001"),
    "competitor": os.getenv("MCP_COMPETITOR_URL", "http://mcp-competitor:3002"),
    "social": os.getenv("MCP_SOCIAL_URL", "http://mcp-social:3003"),
}

# Token Cost Configuration (per 1M tokens)
TOKEN_COSTS = {
    "gpt-5-mini": {
        "input": float(os.getenv("INPUT_COST_PER_1M", 0.150)),
        "output": float(os.getenv("OUTPUT_COST_PER_1M", 0.600)),
    }
}

# Promotion Design Defaults
PROMOTION_DEFAULTS = {
    "flash_sale_duration_hours": 2,
    "coupon_duration_hours": 4,
    "discount_duration_hours": 24,
    "target_radius_km": 5.0,
}

# Performance Thresholds
PERFORMANCE_THRESHOLDS = {
    "excellent": 1.5,  # 150% of expected
    "good": 1.0,  # 100% of expected
    "acceptable": 0.7,  # 70% of expected
    "poor": 0.5,  # Below 50% triggers retraction
}

CRITIC_CONFIG = {
    "revise_threshold": float(os.getenv("CRITIC_REVISE_THRESHOLD", 65)),
    "reject_threshold": float(os.getenv("CRITIC_REJECT_THRESHOLD", 45)),
}

RAG_CONFIG = {
    "chroma_host": os.getenv("CHROMA_HOST", "chroma-db"),
    "chroma_port": int(os.getenv("CHROMA_PORT", 8000)),
    "chroma_collection": os.getenv("CHROMA_COLLECTION", "promotion_similarity"),
    "retrieval_k": int(os.getenv("RAG_RETRIEVAL_K", 5)),
}

SKUS_CONSIDERED = os.getenv("skus_considered", "")
STORES_CONSIDERED = os.getenv("stores_considered", "")
