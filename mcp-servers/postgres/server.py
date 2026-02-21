"""
MCP Server for PostgreSQL Database Operations
Provides structured access to the pricing intelligence database
"""

import os
import json
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import psycopg2
from psycopg2.extras import RealDictCursor
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn

# Initialize FastAPI app
app = FastAPI(title="MCP Postgres Server", version="1.0.0")

# Database configuration
DB_CONFIG = {
    "host": os.getenv("DB_HOST", os.getenv("POSTGRES_HOST", "postgres")),
    "port": int(os.getenv("DB_PORT", os.getenv("POSTGRES_PORT", 5432))),
    "user": os.getenv("DB_USER", os.getenv("POSTGRES_USER", "pricing_user")),
    "password": os.getenv("DB_PASSWORD", os.getenv("POSTGRES_PASSWORD", "pricing_pass")),
    "database": os.getenv("DB_NAME", os.getenv("POSTGRES_DB", "pricing_intelligence")),
}
FEATURE_FLAGS = {
    "enable_approval_learning": os.getenv("ENABLE_APPROVAL_LEARNING", "false").lower() == "true",
}


# Pydantic models
class ToolRequest(BaseModel):
    tool_name: str
    parameters: Dict[str, Any]


class ToolResponse(BaseModel):
    success: bool
    data: Any
    error: Optional[str] = None


# Database connection helper
def get_db_connection():
    """Create and return a database connection"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        return conn
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database connection failed: {str(e)}")


def _json_dumps_if_present(payload: Optional[Dict[str, Any]]) -> Optional[str]:
    """Serialize dict payloads for JSONB columns."""
    if payload is None:
        return None
    return json.dumps(payload)


def _get_recent_decision_id_for_pending(cursor, pending_promotion_id: int) -> Optional[int]:
    """
    Best-effort link between pending promotion and decision log.
    Uses latest create_promotion/promotion_design decision for same SKU/store.
    """
    cursor.execute(
        """
        SELECT ad.id
        FROM agent_decisions ad
        JOIN pending_promotions pp ON pp.sku_id = ad.sku_id AND pp.store_id = ad.store_id
        WHERE pp.id = %s
          AND ad.decision_type IN ('create_promotion', 'promotion_design')
        ORDER BY ad.created_at DESC
        LIMIT 1
        """,
        (pending_promotion_id,),
    )
    row = cursor.fetchone()
    return row["id"] if row else None


# Health check endpoint
@app.get("/health")
def health_check():
    """Health check endpoint"""
    try:
        conn = get_db_connection()
        conn.close()
        return {"status": "healthy", "service": "mcp-postgres"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Service unhealthy: {str(e)}")


# MCP Tool endpoint
@app.post("/tool", response_model=ToolResponse)
def execute_tool(request: ToolRequest):
    """Execute an MCP tool"""
    tool_name = request.tool_name
    parameters = request.parameters

    try:
        if tool_name == "query_inventory_levels":
            result = query_inventory_levels(**parameters)
        elif tool_name == "calculate_sell_through_rate":
            result = calculate_sell_through_rate(**parameters)
        elif tool_name == "get_pricing_history":
            result = get_pricing_history(**parameters)
        elif tool_name == "create_promotion":
            result = create_promotion(**parameters)
        elif tool_name == "retract_promotion":
            result = retract_promotion(**parameters)
        elif tool_name == "log_performance_metric":
            result = log_performance_metric(**parameters)
        elif tool_name == "log_token_usage":
            result = log_token_usage(**parameters)
        elif tool_name == "get_cost_summary":
            result = get_cost_summary(**parameters)
        elif tool_name == "get_competitor_prices":
            result = get_competitor_prices(**parameters)
        elif tool_name == "log_agent_decision":
            result = log_agent_decision(**parameters)
        elif tool_name == "get_active_promotions":
            result = get_active_promotions(**parameters)
        elif tool_name == "update_promotion_performance":
            result = update_promotion_performance(**parameters)
        elif tool_name == "create_pending_promotion":
            result = create_pending_promotion(**parameters)
        elif tool_name == "get_pending_promotions":
            result = get_pending_promotions(**parameters)
        elif tool_name == "approve_promotion":
            result = approve_promotion(**parameters)
        elif tool_name == "reject_promotion":
            result = reject_promotion(**parameters)
        elif tool_name == "create_decision_prior":
            result = create_decision_prior(**parameters)
        elif tool_name == "get_latest_decision_prior":
            result = get_latest_decision_prior(**parameters)
        elif tool_name == "list_decision_priors":
            result = list_decision_priors(**parameters)
        elif tool_name == "create_approval_feedback":
            result = create_approval_feedback(**parameters)
        elif tool_name == "get_approval_feedback":
            result = get_approval_feedback(**parameters)
        elif tool_name == "log_optimization_iteration":
            result = log_optimization_iteration(**parameters)
        elif tool_name == "get_optimization_iterations":
            result = get_optimization_iterations(**parameters)
        elif tool_name == "log_evaluator_score":
            result = log_evaluator_score(**parameters)
        elif tool_name == "get_evaluator_scores":
            result = get_evaluator_scores(**parameters)
        elif tool_name == "upsert_embedding_metadata":
            result = upsert_embedding_metadata(**parameters)
        elif tool_name == "get_embedding_metadata":
            result = get_embedding_metadata(**parameters)
        elif tool_name == "get_historical_promotion_cases":
            result = get_historical_promotion_cases(**parameters)
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

        return ToolResponse(success=True, data=result)

    except Exception as e:
        return ToolResponse(success=False, data=None, error=str(e))


# ============================================================================
# TOOL IMPLEMENTATIONS
# ============================================================================

def query_inventory_levels(sku_id: int = None, store_id: int = None) -> List[Dict]:
    """Query current inventory levels"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            i.id,
            i.sku_id,
            i.store_id,
            s.sku_code,
            s.name AS sku_name,
            s.category,
            st.store_code,
            st.name AS store_name,
            i.quantity,
            i.reorder_point,
            i.max_capacity,
            CASE
                WHEN i.quantity <= i.reorder_point THEN 'low'
                WHEN i.quantity >= i.max_capacity * 0.8 THEN 'excess'
                ELSE 'normal'
            END AS stock_status
        FROM inventory i
        JOIN skus s ON i.sku_id = s.id
        JOIN stores st ON i.store_id = st.id
        WHERE s.is_active = true
    """

    params = []
    if sku_id:
        query += " AND i.sku_id = %s"
        params.append(sku_id)
    if store_id:
        query += " AND i.store_id = %s"
        params.append(store_id)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in results]


def calculate_sell_through_rate(sku_id: int, store_id: int, days: int = 7) -> Dict:
    """Calculate sell-through rate for a SKU at a store"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            %s AS sku_id,
            %s AS store_id,
            COALESCE(SUM(quantity_sold), 0) AS total_sold,
            COALESCE(ROUND(SUM(quantity_sold)::NUMERIC / %s, 2), 0) AS avg_daily_sales,
            COUNT(DISTINCT DATE(transaction_date)) AS days_with_sales
        FROM sales_transactions
        WHERE sku_id = %s
          AND store_id = %s
          AND transaction_date >= NOW() - INTERVAL '%s days'
    """

    cursor.execute(query, (sku_id, store_id, days, sku_id, store_id, days))
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def get_pricing_history(sku_id: int, store_id: int = None, limit: int = 10) -> List[Dict]:
    """Get pricing history for a SKU"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            ph.id,
            ph.sku_id,
            ph.store_id,
            st.store_code,
            ph.old_price,
            ph.new_price,
            ph.margin_percent,
            ph.reason,
            ph.changed_by,
            ph.effective_date
        FROM pricing_history ph
        LEFT JOIN stores st ON ph.store_id = st.id
        WHERE ph.sku_id = %s
    """

    params = [sku_id]
    if store_id:
        query += " AND ph.store_id = %s"
        params.append(store_id)

    query += " ORDER BY ph.effective_date DESC LIMIT %s"
    params.append(limit)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in results]


def create_promotion(
    sku_id: int,
    store_id: int,
    promotion_type: str,
    discount_type: str,
    discount_value: float,
    original_price: float,
    promotional_price: float,
    margin_percent: float,
    valid_from: str,
    valid_until: str,
    target_radius_km: float = None,
    target_customer_segment: str = None,
    expected_units_sold: int = None,
    expected_revenue: float = None,
    reason: str = None,
) -> Dict:
    """Create a new promotion"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Generate promotion code
    promotion_code = f"PROMO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{sku_id}-{store_id}"

    query = """
        INSERT INTO promotions (
            promotion_code, sku_id, store_id, promotion_type, discount_type, discount_value,
            original_price, promotional_price, margin_percent, target_radius_km,
            target_customer_segment, valid_from, valid_until, status,
            expected_units_sold, expected_revenue, reason, created_by
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, promotion_code, status
    """

    cursor.execute(
        query,
        (
            promotion_code,
            sku_id,
            store_id,
            promotion_type,
            discount_type,
            discount_value,
            original_price,
            promotional_price,
            margin_percent,
            target_radius_km,
            target_customer_segment,
            valid_from,
            valid_until,
            "active",
            expected_units_sold,
            expected_revenue,
            reason,
            "agent",
        ),
    )

    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def retract_promotion(promotion_id: int, reason: str) -> Dict:
    """Retract an active promotion"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        UPDATE promotions
        SET status = 'retracted',
            retraction_reason = %s,
            retracted_at = NOW()
        WHERE id = %s
        RETURNING id, promotion_code, status, retracted_at
    """

    cursor.execute(query, (reason, promotion_id))
    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def log_performance_metric(
    promotion_id: int,
    units_sold_so_far: int,
    revenue_so_far: float,
    performance_ratio: float,
    is_profitable: bool,
    margin_maintained: bool,
    notes: str = None,
) -> Dict:
    """Log promotion performance metric"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        INSERT INTO promotion_performance (
            promotion_id, units_sold_so_far, revenue_so_far,
            performance_ratio, is_profitable, margin_maintained, notes
        ) VALUES (%s, %s, %s, %s, %s, %s, %s)
        RETURNING id, check_time
    """

    cursor.execute(
        query,
        (
            promotion_id,
            units_sold_so_far,
            revenue_so_far,
            performance_ratio,
            is_profitable,
            margin_maintained,
            notes,
        ),
    )

    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def log_token_usage(
    agent_name: str,
    operation: str,
    prompt_tokens: int,
    completion_tokens: int,
    total_tokens: int,
    estimated_cost: float,
    sku_id: int = None,
    context: Dict = None,
) -> Dict:
    """Log token usage and cost"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        INSERT INTO token_usage (
            agent_name, operation, prompt_tokens, completion_tokens,
            total_tokens, estimated_cost, sku_id, context
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, timestamp
    """

    cursor.execute(
        query,
        (
            agent_name,
            operation,
            prompt_tokens,
            completion_tokens,
            total_tokens,
            estimated_cost,
            sku_id,
            json.dumps(context) if context else None,
        ),
    )

    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def get_cost_summary(
    agent_name: str = None, sku_id: int = None, days: int = 7
) -> Dict:
    """Get cost summary"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT
            COUNT(*) AS operation_count,
            SUM(total_tokens) AS total_tokens,
            SUM(estimated_cost) AS total_cost,
            AVG(estimated_cost) AS avg_cost_per_operation,
            MAX(timestamp) AS last_operation
        FROM token_usage
        WHERE timestamp >= NOW() - INTERVAL '%s days'
    """

    params = [days]
    if agent_name:
        query += " AND agent_name = %s"
        params.append(agent_name)
    if sku_id:
        query += " AND sku_id = %s"
        params.append(sku_id)

    cursor.execute(query, params)
    result = cursor.fetchone()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def get_competitor_prices(sku_id: int, store_id: int = None) -> List[Dict]:
    """Get latest competitor prices for a SKU"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT DISTINCT ON (competitor_name)
            competitor_name,
            sku_id,
            store_id,
            competitor_price,
            competitor_promotion,
            observed_date
        FROM competitor_prices
        WHERE sku_id = %s
    """

    params = [sku_id]
    if store_id:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY competitor_name, observed_date DESC"

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in results]


def log_agent_decision(
    agent_name: str,
    sku_id: int,
    store_id: int,
    decision_type: str,
    prompt_fed: str,
    reasoning: str,
    data_used: Dict,
    decision_outcome: str,
    promotion_id: int = None,
) -> Dict:
    """Log agent decision"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        INSERT INTO agent_decisions (
            agent_name, sku_id, store_id, decision_type, prompt_fed, reasoning,
            data_used, decision_outcome, promotion_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id, decision_id, created_at
    """

    cursor.execute(
        query,
        (
            agent_name,
            sku_id,
            store_id,
            decision_type,
            prompt_fed,
            reasoning,
            json.dumps(data_used),
            decision_outcome,
            promotion_id,
        ),
    )

    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def get_active_promotions(store_id: int = None) -> List[Dict]:
    """Get all active promotions"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT * FROM v_active_promotions
        WHERE 1=1
    """

    params = []
    if store_id:
        query += " AND store_id = %s"
        params.append(store_id)

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in results]


def update_promotion_performance(
    promotion_id: int, units_sold: int, revenue: float
) -> Dict:
    """Update promotion actual performance"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        UPDATE promotions
        SET actual_units_sold = actual_units_sold + %s,
            actual_revenue = actual_revenue + %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, actual_units_sold, actual_revenue
    """

    cursor.execute(query, (units_sold, revenue, promotion_id))
    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def create_pending_promotion(
    sku_id: int,
    store_id: int,
    promotion_type: str,
    discount_type: str,
    discount_value: float,
    original_price: float,
    promotional_price: float,
    margin_percent: float,
    proposed_valid_from: str,
    proposed_valid_until: str,
    agent_reasoning: str,
    target_radius_km: float = None,
    target_customer_segment: str = None,
    expected_units_sold: int = None,
    expected_revenue: float = None,
    market_data: Dict = None,
) -> Dict:
    """Create a pending promotion awaiting manual approval"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        INSERT INTO pending_promotions (
            sku_id, store_id, promotion_type, discount_type, discount_value,
            original_price, promotional_price, margin_percent,
            target_radius_km, target_customer_segment,
            proposed_valid_from, proposed_valid_until,
            expected_units_sold, expected_revenue,
            agent_reasoning, market_data, status
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, status, created_at
    """

    cursor.execute(
        query,
        (
            sku_id,
            store_id,
            promotion_type,
            discount_type,
            discount_value,
            original_price,
            promotional_price,
            margin_percent,
            target_radius_km,
            target_customer_segment,
            proposed_valid_from,
            proposed_valid_until,
            expected_units_sold,
            expected_revenue,
            agent_reasoning,
            json.dumps(market_data) if market_data else None,
            "pending",
        ),
    )

    result = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


def get_pending_promotions(status: str = "pending", store_id: int = None) -> List[Dict]:
    """Get pending promotions awaiting approval"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT * FROM v_pending_promotions
        WHERE status = %s
    """

    params = [status]
    if store_id:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY created_at DESC"

    cursor.execute(query, params)
    results = cursor.fetchall()

    cursor.close()
    conn.close()

    return [dict(row) for row in results]


def approve_promotion(
    pending_promotion_id: int,
    reviewed_by: str,
    reviewer_notes: str = None,
) -> Dict:
    """Approve a pending promotion and create an active promotion"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    # Get pending promotion details
    cursor.execute(
        "SELECT * FROM pending_promotions WHERE id = %s AND status = 'pending'",
        (pending_promotion_id,),
    )
    pending = cursor.fetchone()

    if not pending:
        cursor.close()
        conn.close()
        raise ValueError(f"Pending promotion {pending_promotion_id} not found or already processed")

    # Generate promotion code
    promotion_code = f"PROMO-{datetime.now().strftime('%Y%m%d%H%M%S')}-{pending['sku_id']}-{pending['store_id']}"

    # Create active promotion
    create_query = """
        INSERT INTO promotions (
            promotion_code, sku_id, store_id, promotion_type, discount_type, discount_value,
            original_price, promotional_price, margin_percent, target_radius_km,
            target_customer_segment, valid_from, valid_until, status,
            expected_units_sold, expected_revenue, reason, created_by
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, promotion_code, status
    """

    cursor.execute(
        create_query,
        (
            promotion_code,
            pending["sku_id"],
            pending["store_id"],
            pending["promotion_type"],
            pending["discount_type"],
            pending["discount_value"],
            pending["original_price"],
            pending["promotional_price"],
            pending["margin_percent"],
            pending["target_radius_km"],
            pending["target_customer_segment"],
            pending["proposed_valid_from"],
            pending["proposed_valid_until"],
            "active",
            pending["expected_units_sold"],
            pending["expected_revenue"],
            pending["agent_reasoning"],
            reviewed_by,
        ),
    )

    promotion_result = cursor.fetchone()

    # Update pending promotion status
    update_query = """
        UPDATE pending_promotions
        SET status = 'approved',
            reviewed_by = %s,
            reviewed_at = NOW(),
            reviewer_notes = %s,
            approved_promotion_id = %s,
            updated_at = NOW()
        WHERE id = %s
        RETURNING id, status, reviewed_at
    """

    cursor.execute(
        update_query,
        (reviewed_by, reviewer_notes, promotion_result["id"], pending_promotion_id),
    )

    pending_result = cursor.fetchone()
    feedback_id = None
    if FEATURE_FLAGS["enable_approval_learning"]:
        decision_id = _get_recent_decision_id_for_pending(cursor, pending_promotion_id)
        context_payload = {
            "promotion_type": pending["promotion_type"],
            "discount_type": pending["discount_type"],
            "discount_value": float(pending["discount_value"]),
            "original_price": float(pending["original_price"]),
            "promotional_price": float(pending["promotional_price"]),
            "margin_percent": float(pending["margin_percent"]),
            "expected_units_sold": pending.get("expected_units_sold"),
            "expected_revenue": float(pending["expected_revenue"]) if pending.get("expected_revenue") is not None else None,
            "agent_reasoning": pending.get("agent_reasoning"),
            "market_data": pending.get("market_data"),
        }

        cursor.execute(
            """
            INSERT INTO approval_feedback (
                pending_promotion_id, promotion_id, decision_id,
                sku_id, store_id, reviewer_outcome, reviewed_by,
                reviewer_notes, decision_context, feedback_payload
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                pending_promotion_id,
                promotion_result["id"],
                decision_id,
                pending["sku_id"],
                pending["store_id"],
                "approved",
                reviewed_by,
                reviewer_notes,
                _json_dumps_if_present(context_payload),
                _json_dumps_if_present(
                    {
                        "outcome": "approved",
                        "approved_promotion_id": promotion_result["id"],
                        "approved_promotion_code": promotion_result["promotion_code"],
                    }
                ),
            ),
        )
        feedback_row = cursor.fetchone()
        feedback_id = feedback_row["id"] if feedback_row else None

    conn.commit()

    cursor.close()
    conn.close()

    return {
        "pending_promotion_id": pending_result["id"],
        "pending_status": pending_result["status"],
        "promotion_id": promotion_result["id"],
        "promotion_code": promotion_result["promotion_code"],
        "promotion_status": promotion_result["status"],
        "approval_feedback_id": feedback_id,
    }


def reject_promotion(
    pending_promotion_id: int,
    reviewed_by: str,
    reviewer_notes: str,
) -> Dict:
    """Reject a pending promotion"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        "SELECT * FROM pending_promotions WHERE id = %s AND status = 'pending'",
        (pending_promotion_id,),
    )
    pending = cursor.fetchone()
    if not pending:
        cursor.close()
        conn.close()
        raise ValueError(f"Pending promotion {pending_promotion_id} not found or already processed")

    query = """
        UPDATE pending_promotions
        SET status = 'rejected',
            reviewed_by = %s,
            reviewed_at = NOW(),
            reviewer_notes = %s,
            updated_at = NOW()
        WHERE id = %s AND status = 'pending'
        RETURNING id, status, reviewed_by, reviewed_at
    """

    cursor.execute(query, (reviewed_by, reviewer_notes, pending_promotion_id))
    result = cursor.fetchone()

    if not result:
        cursor.close()
        conn.close()
        raise ValueError(f"Pending promotion {pending_promotion_id} not found or already processed")

    feedback_id = None
    if FEATURE_FLAGS["enable_approval_learning"]:
        decision_id = _get_recent_decision_id_for_pending(cursor, pending_promotion_id)
        context_payload = {
            "promotion_type": pending["promotion_type"],
            "discount_type": pending["discount_type"],
            "discount_value": float(pending["discount_value"]),
            "original_price": float(pending["original_price"]),
            "promotional_price": float(pending["promotional_price"]),
            "margin_percent": float(pending["margin_percent"]),
            "expected_units_sold": pending.get("expected_units_sold"),
            "expected_revenue": float(pending["expected_revenue"]) if pending.get("expected_revenue") is not None else None,
            "agent_reasoning": pending.get("agent_reasoning"),
            "market_data": pending.get("market_data"),
        }

        cursor.execute(
            """
            INSERT INTO approval_feedback (
                pending_promotion_id, promotion_id, decision_id,
                sku_id, store_id, reviewer_outcome, reviewed_by,
                reviewer_notes, decision_context, feedback_payload
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
            )
            RETURNING id
            """,
            (
                pending_promotion_id,
                None,
                decision_id,
                pending["sku_id"],
                pending["store_id"],
                "rejected",
                reviewed_by,
                reviewer_notes,
                _json_dumps_if_present(context_payload),
                _json_dumps_if_present(
                    {
                        "outcome": "rejected",
                        "rejection_reason": reviewer_notes,
                    }
                ),
            ),
        )
        feedback_row = cursor.fetchone()
        feedback_id = feedback_row["id"] if feedback_row else None

    conn.commit()

    cursor.close()
    conn.close()

    result_payload = dict(result) if result else {}
    if feedback_id is not None:
        result_payload["approval_feedback_id"] = feedback_id
    return result_payload


def create_decision_prior(
    prior_payload: Dict,
    sku_id: int = None,
    store_id: int = None,
    source_decision_id: int = None,
    source_promotion_id: int = None,
    prior_version: int = 1,
    success_probability: float = None,
    confidence_score: float = None,
    expected_roi_band: str = None,
    risk_flags: Dict = None,
    generated_by: str = "decision_learning_service",
) -> Dict:
    """Persist a learned decision prior."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        INSERT INTO decision_priors (
            sku_id, store_id, source_decision_id, source_promotion_id,
            prior_version, success_probability, confidence_score,
            expected_roi_band, risk_flags, prior_payload, generated_by
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, generated_at
        """,
        (
            sku_id,
            store_id,
            source_decision_id,
            source_promotion_id,
            prior_version,
            success_probability,
            confidence_score,
            expected_roi_band,
            _json_dumps_if_present(risk_flags),
            json.dumps(prior_payload),
            generated_by,
        ),
    )
    row = cursor.fetchone()
    conn.commit()

    cursor.close()
    conn.close()
    return dict(row) if row else {}


def get_latest_decision_prior(
    sku_id: int = None,
    store_id: int = None,
    max_age_hours: int = 720,
) -> Dict:
    """Get the most recent decision prior for a given scope."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM decision_priors
        WHERE generated_at >= NOW() - (%s * INTERVAL '1 hour')
    """
    params: List[Any] = [max_age_hours]

    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY generated_at DESC, id DESC LIMIT 1"
    cursor.execute(query, params)
    row = cursor.fetchone()

    cursor.close()
    conn.close()
    return dict(row) if row else {}


def list_decision_priors(
    sku_id: int = None,
    store_id: int = None,
    limit: int = 25,
) -> List[Dict]:
    """List decision priors for diagnostics and analysis."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM decision_priors
        WHERE 1=1
    """
    params: List[Any] = []

    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY generated_at DESC, id DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def create_approval_feedback(
    reviewer_outcome: str,
    reviewed_by: str,
    pending_promotion_id: int = None,
    promotion_id: int = None,
    decision_id: int = None,
    sku_id: int = None,
    store_id: int = None,
    reviewer_notes: str = None,
    decision_context: Dict = None,
    feedback_payload: Dict = None,
) -> Dict:
    """Insert an approval feedback signal."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        INSERT INTO approval_feedback (
            pending_promotion_id, promotion_id, decision_id, sku_id, store_id,
            reviewer_outcome, reviewed_by, reviewer_notes, decision_context, feedback_payload
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, created_at
        """,
        (
            pending_promotion_id,
            promotion_id,
            decision_id,
            sku_id,
            store_id,
            reviewer_outcome,
            reviewed_by,
            reviewer_notes,
            _json_dumps_if_present(decision_context),
            _json_dumps_if_present(feedback_payload),
        ),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return dict(row) if row else {}


def get_approval_feedback(
    reviewer_outcome: str = None,
    sku_id: int = None,
    store_id: int = None,
    days: int = 90,
    limit: int = 100,
) -> List[Dict]:
    """Retrieve approval feedback signals."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM approval_feedback
        WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
    """
    params: List[Any] = [days]

    if reviewer_outcome:
        query += " AND reviewer_outcome = %s"
        params.append(reviewer_outcome)
    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY created_at DESC, id DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def log_optimization_iteration(
    iteration_index: int,
    objective_name: str,
    candidate_offer: Dict,
    objective_score: float = None,
    sku_id: int = None,
    store_id: int = None,
    decision_id: int = None,
    promotion_id: int = None,
    constraints_checked: Dict = None,
    is_selected: bool = False,
) -> Dict:
    """Log one iteration from offer optimization."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        INSERT INTO optimization_iterations (
            decision_id, promotion_id, sku_id, store_id,
            iteration_index, objective_name, objective_score,
            candidate_offer, constraints_checked, is_selected
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, created_at
        """,
        (
            decision_id,
            promotion_id,
            sku_id,
            store_id,
            iteration_index,
            objective_name,
            objective_score,
            json.dumps(candidate_offer),
            _json_dumps_if_present(constraints_checked),
            is_selected,
        ),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return dict(row) if row else {}


def get_optimization_iterations(
    sku_id: int = None,
    store_id: int = None,
    decision_id: int = None,
    limit: int = 100,
) -> List[Dict]:
    """Get optimization loop history."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM optimization_iterations
        WHERE 1=1
    """
    params: List[Any] = []

    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)
    if decision_id is not None:
        query += " AND decision_id = %s"
        params.append(decision_id)

    query += " ORDER BY created_at DESC, iteration_index DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def log_evaluator_score(
    evaluator_name: str,
    score: float,
    rationale: str,
    sku_id: int = None,
    store_id: int = None,
    decision_id: int = None,
    promotion_id: int = None,
    risk_flags: Dict = None,
    recommendation: str = None,
    arbitration_decision: str = None,
) -> Dict:
    """Log evaluator output from multi-critic stage."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        INSERT INTO evaluator_scores (
            decision_id, promotion_id, sku_id, store_id,
            evaluator_name, score, rationale, risk_flags,
            recommendation, arbitration_decision
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, created_at
        """,
        (
            decision_id,
            promotion_id,
            sku_id,
            store_id,
            evaluator_name,
            score,
            rationale,
            _json_dumps_if_present(risk_flags),
            recommendation,
            arbitration_decision,
        ),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return dict(row) if row else {}


def get_evaluator_scores(
    sku_id: int = None,
    store_id: int = None,
    decision_id: int = None,
    evaluator_name: str = None,
    limit: int = 100,
) -> List[Dict]:
    """Fetch evaluator outputs for observability."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM evaluator_scores
        WHERE 1=1
    """
    params: List[Any] = []

    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)
    if decision_id is not None:
        query += " AND decision_id = %s"
        params.append(decision_id)
    if evaluator_name is not None:
        query += " AND evaluator_name = %s"
        params.append(evaluator_name)

    query += " ORDER BY created_at DESC, id DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def upsert_embedding_metadata(
    entity_type: str,
    entity_id: int,
    sku_id: int = None,
    store_id: int = None,
    decision_id: int = None,
    promotion_id: int = None,
    embedding_provider: str = None,
    collection_name: str = None,
    vector_key: str = None,
    source_payload: Dict = None,
    summary: str = None,
) -> Dict:
    """Persist metadata describing indexed vectors."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    cursor.execute(
        """
        INSERT INTO embeddings_index_metadata (
            entity_type, entity_id, sku_id, store_id, decision_id, promotion_id,
            embedding_provider, collection_name, vector_key, source_payload, summary
        ) VALUES (
            %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
        )
        RETURNING id, indexed_at
        """,
        (
            entity_type,
            entity_id,
            sku_id,
            store_id,
            decision_id,
            promotion_id,
            embedding_provider,
            collection_name,
            vector_key,
            _json_dumps_if_present(source_payload),
            summary,
        ),
    )

    row = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return dict(row) if row else {}


def get_embedding_metadata(
    entity_type: str = None,
    sku_id: int = None,
    store_id: int = None,
    limit: int = 100,
) -> List[Dict]:
    """Fetch embedding index metadata for diagnostics."""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        SELECT *
        FROM embeddings_index_metadata
        WHERE 1=1
    """
    params: List[Any] = []

    if entity_type is not None:
        query += " AND entity_type = %s"
        params.append(entity_type)
    if sku_id is not None:
        query += " AND sku_id = %s"
        params.append(sku_id)
    if store_id is not None:
        query += " AND store_id = %s"
        params.append(store_id)

    query += " ORDER BY indexed_at DESC, id DESC LIMIT %s"
    params.append(limit)
    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


def get_historical_promotion_cases(
    sku_id: int,
    store_id: int = None,
    limit: int = 5,
) -> List[Dict]:
    """
    Fetch historically similar cases (same SKU first, then same category).
    This provides a deterministic fallback when vector retrieval is unavailable.
    """
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

    query = """
        WITH target_sku AS (
            SELECT id, category
            FROM skus
            WHERE id = %s
        ),
        perf AS (
            SELECT
                promotion_id,
                AVG(COALESCE(performance_ratio, 0)) AS avg_performance_ratio,
                MAX(check_time) AS last_check_time
            FROM promotion_performance
            GROUP BY promotion_id
        )
        SELECT
            p.id AS promotion_id,
            p.sku_id,
            p.store_id,
            s.category,
            p.promotion_type,
            p.discount_type,
            p.discount_value,
            p.original_price,
            p.promotional_price,
            p.margin_percent,
            p.expected_units_sold,
            p.expected_revenue,
            p.actual_units_sold,
            p.actual_revenue,
            p.status,
            p.reason,
            p.created_at,
            COALESCE(perf.avg_performance_ratio, 0) AS avg_performance_ratio,
            CASE WHEN p.sku_id = %s THEN 1 ELSE 0 END AS sku_similarity,
            CASE WHEN s.category = (SELECT category FROM target_sku) THEN 1 ELSE 0 END AS category_similarity
        FROM promotions p
        JOIN skus s ON s.id = p.sku_id
        LEFT JOIN perf ON perf.promotion_id = p.id
        WHERE p.status IN ('active', 'completed', 'retracted')
          AND (
              p.sku_id = %s
              OR s.category = (SELECT category FROM target_sku)
          )
    """
    params: List[Any] = [sku_id, sku_id, sku_id]

    if store_id is not None:
        query += " AND p.store_id = %s"
        params.append(store_id)

    query += """
        ORDER BY sku_similarity DESC, category_similarity DESC, avg_performance_ratio DESC, p.created_at DESC
        LIMIT %s
    """
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()

    cursor.close()
    conn.close()
    return [dict(row) for row in rows]


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Postgres Server...")
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    uvicorn.run(app, host="0.0.0.0", port=3000)
