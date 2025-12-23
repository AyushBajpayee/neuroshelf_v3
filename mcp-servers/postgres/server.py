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
    "host": os.getenv("POSTGRES_HOST", "postgres"),
    "port": int(os.getenv("POSTGRES_PORT", 5432)),
    "user": os.getenv("POSTGRES_USER", "pricing_user"),
    "password": os.getenv("POSTGRES_PASSWORD", "pricing_pass"),
    "database": os.getenv("POSTGRES_DB", "pricing_intelligence"),
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
    conn.commit()

    cursor.close()
    conn.close()

    return {
        "pending_promotion_id": pending_result["id"],
        "pending_status": pending_result["status"],
        "promotion_id": promotion_result["id"],
        "promotion_code": promotion_result["promotion_code"],
        "promotion_status": promotion_result["status"],
    }


def reject_promotion(
    pending_promotion_id: int,
    reviewed_by: str,
    reviewer_notes: str,
) -> Dict:
    """Reject a pending promotion"""
    conn = get_db_connection()
    cursor = conn.cursor(cursor_factory=RealDictCursor)

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

    conn.commit()

    cursor.close()
    conn.close()

    return dict(result) if result else {}


# ============================================================================
# SERVER STARTUP
# ============================================================================

if __name__ == "__main__":
    print("Starting MCP Postgres Server...")
    print(f"Database: {DB_CONFIG['host']}:{DB_CONFIG['port']}/{DB_CONFIG['database']}")
    uvicorn.run(app, host="0.0.0.0", port=3000)
