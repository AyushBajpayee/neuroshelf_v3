-- Pricing Intelligence Database Schema
-- Version: 1.0.0
-- Description: Core schema for autonomous pricing and promotion management

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ============================================================================
-- CORE TABLES
-- ============================================================================

-- Stores/Locations
CREATE TABLE stores (
    id SERIAL PRIMARY KEY,
    store_code VARCHAR(50) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    state VARCHAR(50),
    zip_code VARCHAR(20),
    latitude DECIMAL(10, 7),
    longitude DECIMAL(10, 7),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Product Catalog
CREATE TABLE skus (
    id SERIAL PRIMARY KEY,
    sku_code VARCHAR(100) UNIQUE NOT NULL,
    name VARCHAR(200) NOT NULL,
    category VARCHAR(100) NOT NULL,
    subcategory VARCHAR(100),
    base_cost DECIMAL(10, 2) NOT NULL,
    base_price DECIMAL(10, 2) NOT NULL,
    target_margin_percent DECIMAL(5, 2) NOT NULL DEFAULT 20.00,
    min_margin_percent DECIMAL(5, 2) NOT NULL DEFAULT 10.00,
    unit VARCHAR(50) DEFAULT 'unit',
    is_active BOOLEAN DEFAULT TRUE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Inventory Levels
CREATE TABLE inventory (
    id SERIAL PRIMARY KEY,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
    quantity INTEGER NOT NULL DEFAULT 0,
    reorder_point INTEGER DEFAULT 50,
    max_capacity INTEGER DEFAULT 1000,
    last_restock_date TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(sku_id, store_id)
);

-- Sales Transactions
CREATE TABLE sales_transactions (
    id SERIAL PRIMARY KEY,
    transaction_id VARCHAR(100) UNIQUE NOT NULL,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
    quantity_sold INTEGER NOT NULL,
    unit_price DECIMAL(10, 2) NOT NULL,
    total_amount DECIMAL(10, 2) NOT NULL,
    promotion_id INTEGER,
    transaction_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pricing History
CREATE TABLE pricing_history (
    id SERIAL PRIMARY KEY,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
    old_price DECIMAL(10, 2),
    new_price DECIMAL(10, 2) NOT NULL,
    margin_percent DECIMAL(5, 2),
    reason VARCHAR(200),
    changed_by VARCHAR(100) DEFAULT 'system',
    effective_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- PROMOTION TABLES
-- ============================================================================

-- Promotions
CREATE TABLE promotions (
    id SERIAL PRIMARY KEY,
    promotion_code VARCHAR(100) UNIQUE NOT NULL,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
    promotion_type VARCHAR(50) NOT NULL, -- 'flash_sale', 'coupon', 'discount'
    discount_type VARCHAR(20) NOT NULL, -- 'percentage', 'fixed_amount'
    discount_value DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    promotional_price DECIMAL(10, 2) NOT NULL,
    margin_percent DECIMAL(5, 2) NOT NULL,

    -- Targeting
    target_radius_km DECIMAL(5, 2),
    target_customer_segment VARCHAR(100),

    -- Timing
    valid_from TIMESTAMP NOT NULL,
    valid_until TIMESTAMP NOT NULL,

    -- Status
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'active', 'completed', 'retracted'

    -- Performance Targets
    expected_units_sold INTEGER,
    expected_revenue DECIMAL(10, 2),

    -- Actual Performance
    actual_units_sold INTEGER DEFAULT 0,
    actual_revenue DECIMAL(10, 2) DEFAULT 0.00,

    -- Metadata
    created_by VARCHAR(100) DEFAULT 'agent',
    reason TEXT,
    retraction_reason TEXT,

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    retracted_at TIMESTAMP
);

-- Promotion Performance Tracking
CREATE TABLE promotion_performance (
    id SERIAL PRIMARY KEY,
    promotion_id INTEGER NOT NULL REFERENCES promotions(id),
    check_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    units_sold_so_far INTEGER DEFAULT 0,
    revenue_so_far DECIMAL(10, 2) DEFAULT 0.00,
    performance_ratio DECIMAL(5, 2), -- actual vs expected
    is_profitable BOOLEAN,
    margin_maintained BOOLEAN,
    notes TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- EXTERNAL FACTOR TABLES
-- ============================================================================

-- Competitor Prices
CREATE TABLE competitor_prices (
    id SERIAL PRIMARY KEY,
    competitor_name VARCHAR(100) NOT NULL,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER REFERENCES stores(id),
    competitor_price DECIMAL(10, 2) NOT NULL,
    competitor_promotion BOOLEAN DEFAULT FALSE,
    observed_date TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- External Factors (Weather, Events, Trends)
CREATE TABLE external_factors (
    id SERIAL PRIMARY KEY,
    factor_type VARCHAR(50) NOT NULL, -- 'weather', 'event', 'trend'
    factor_name VARCHAR(200) NOT NULL,
    store_id INTEGER REFERENCES stores(id),
    factor_value JSONB NOT NULL, -- Flexible storage for different factor types
    intensity DECIMAL(5, 2), -- 0-100 scale
    start_date TIMESTAMP NOT NULL,
    end_date TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- AGENT & OBSERVABILITY TABLES
-- ============================================================================

-- Token Usage & Cost Tracking
CREATE TABLE token_usage (
    id SERIAL PRIMARY KEY,
    timestamp TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    agent_name VARCHAR(100) NOT NULL,
    operation VARCHAR(200) NOT NULL,
    prompt_tokens INTEGER NOT NULL,
    completion_tokens INTEGER NOT NULL,
    total_tokens INTEGER NOT NULL,
    estimated_cost DECIMAL(10, 6) NOT NULL,
    sku_id INTEGER REFERENCES skus(id),
    context JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Agent Decision Log
CREATE TABLE agent_decisions (
    id SERIAL PRIMARY KEY,
    decision_id UUID DEFAULT uuid_generate_v4(),
    agent_name VARCHAR(100) NOT NULL,
    sku_id INTEGER REFERENCES skus(id),
    store_id INTEGER REFERENCES stores(id),
    decision_type VARCHAR(100) NOT NULL, -- 'create_promotion', 'retract_promotion', 'no_action'
    reasoning TEXT NOT NULL,
    data_used JSONB,
    decision_outcome VARCHAR(50), -- 'executed', 'rejected', 'pending'
    promotion_id INTEGER REFERENCES promotions(id),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Pending Promotions (for manual approval workflow)
CREATE TABLE pending_promotions (
    id SERIAL PRIMARY KEY,
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),

    -- Promotion details (from agent design)
    promotion_type VARCHAR(50) NOT NULL,
    discount_type VARCHAR(20) NOT NULL,
    discount_value DECIMAL(10, 2) NOT NULL,
    original_price DECIMAL(10, 2) NOT NULL,
    promotional_price DECIMAL(10, 2) NOT NULL,
    margin_percent DECIMAL(5, 2) NOT NULL,

    -- Targeting
    target_radius_km DECIMAL(5, 2),
    target_customer_segment VARCHAR(100),

    -- Timing
    proposed_valid_from TIMESTAMP NOT NULL,
    proposed_valid_until TIMESTAMP NOT NULL,

    -- Performance expectations
    expected_units_sold INTEGER,
    expected_revenue DECIMAL(10, 2),

    -- Agent reasoning
    agent_reasoning TEXT NOT NULL,
    market_data JSONB,

    -- Approval workflow
    status VARCHAR(50) DEFAULT 'pending', -- 'pending', 'approved', 'rejected'
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT,

    -- Link to executed promotion (if approved)
    approved_promotion_id INTEGER REFERENCES promotions(id),

    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Simulator State (for persistence)
CREATE TABLE simulator_state (
    id SERIAL PRIMARY KEY,
    simulator_type VARCHAR(50) UNIQUE NOT NULL, -- 'weather', 'competitor', 'social'
    state_data JSONB NOT NULL,
    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ============================================================================
-- INDEXES FOR PERFORMANCE
-- ============================================================================

CREATE INDEX idx_inventory_sku_store ON inventory(sku_id, store_id);
CREATE INDEX idx_sales_sku_store_date ON sales_transactions(sku_id, store_id, transaction_date);
CREATE INDEX idx_sales_transaction_date ON sales_transactions(transaction_date);
CREATE INDEX idx_promotions_sku_store ON promotions(sku_id, store_id);
CREATE INDEX idx_promotions_status ON promotions(status);
CREATE INDEX idx_promotions_dates ON promotions(valid_from, valid_until);
CREATE INDEX idx_competitor_prices_sku ON competitor_prices(sku_id, observed_date);
CREATE INDEX idx_external_factors_type ON external_factors(factor_type, start_date);
CREATE INDEX idx_token_usage_agent ON token_usage(agent_name, timestamp);
CREATE INDEX idx_token_usage_sku ON token_usage(sku_id, timestamp);
CREATE INDEX idx_agent_decisions_sku ON agent_decisions(sku_id, created_at);
CREATE INDEX idx_pending_promotions_status ON pending_promotions(status, created_at);
CREATE INDEX idx_pending_promotions_sku ON pending_promotions(sku_id, store_id);

-- ============================================================================
-- VIEWS FOR COMMON QUERIES
-- ============================================================================

-- Current Inventory Status
CREATE VIEW v_inventory_status AS
SELECT
    s.sku_code,
    s.name AS sku_name,
    s.category,
    st.store_code,
    st.name AS store_name,
    i.quantity,
    i.reorder_point,
    CASE
        WHEN i.quantity <= i.reorder_point THEN 'low'
        WHEN i.quantity >= i.max_capacity * 0.8 THEN 'excess'
        ELSE 'normal'
    END AS stock_status
FROM inventory i
JOIN skus s ON i.sku_id = s.id
JOIN stores st ON i.store_id = st.id;

-- Active Promotions
CREATE VIEW v_active_promotions AS
SELECT
    p.*,
    s.sku_code,
    s.name AS sku_name,
    st.store_code,
    st.name AS store_name,
    EXTRACT(EPOCH FROM (p.valid_until - CURRENT_TIMESTAMP))/3600 AS hours_remaining
FROM promotions p
JOIN skus s ON p.sku_id = s.id
JOIN stores st ON p.store_id = st.id
WHERE p.status = 'active'
  AND p.valid_from <= CURRENT_TIMESTAMP
  AND p.valid_until >= CURRENT_TIMESTAMP;

-- Sell-Through Rate (Last 7 Days)
CREATE VIEW v_sell_through_rate AS
SELECT
    s.id AS sku_id,
    s.sku_code,
    s.name AS sku_name,
    st.id AS store_id,
    st.store_code,
    COUNT(DISTINCT DATE(sales.transaction_date)) AS days_with_sales,
    COALESCE(SUM(sales.quantity_sold), 0) AS total_sold_7d,
    COALESCE(ROUND(SUM(sales.quantity_sold) / 7.0, 2), 0) AS avg_daily_sales
FROM skus s
CROSS JOIN stores st
LEFT JOIN sales_transactions sales ON s.id = sales.sku_id
    AND st.id = sales.store_id
    AND sales.transaction_date >= CURRENT_TIMESTAMP - INTERVAL '7 days'
GROUP BY s.id, s.sku_code, s.name, st.id, st.store_code;

-- Cost Summary by Agent
CREATE VIEW v_cost_by_agent AS
SELECT
    agent_name,
    COUNT(*) AS operation_count,
    SUM(total_tokens) AS total_tokens,
    SUM(estimated_cost) AS total_cost,
    AVG(estimated_cost) AS avg_cost_per_operation,
    MAX(timestamp) AS last_operation
FROM token_usage
GROUP BY agent_name
ORDER BY total_cost DESC;

-- Promotion ROI
-- CREATE VIEW v_promotion_roi AS
-- SELECT
--     p.id,
--     p.promotion_code,
--     p.sku_id,
--     p.store_id,
--     p.actual_revenue,
--     p.actual_units_sold,
--     p.margin_percent,
--     COALESCE(SUM(tu.estimated_cost), 0) AS agent_cost,
--     p.actual_revenue - COALESCE(SUM(tu.estimated_cost), 0) AS net_revenue,
--     CASE
--         WHEN COALESCE(SUM(tu.estimated_cost), 0) > 0
--         THEN (p.actual_revenue - COALESCE(SUM(tu.estimated_cost), 0)) / SUM(tu.estimated_cost)
--         ELSE 0
--     END AS roi_ratio
-- FROM promotions p
-- LEFT JOIN token_usage tu ON p.id = tu.promotion_id
-- WHERE p.status IN ('completed', 'retracted')
-- GROUP BY p.id, p.promotion_code, p.sku_id, p.store_id, p.actual_revenue, p.actual_units_sold, p.margin_percent;

-- Pending Promotions Awaiting Approval
CREATE VIEW v_pending_promotions AS
SELECT
    pp.id,
    pp.sku_id,
    s.sku_code,
    s.name AS sku_name,
    s.category,
    pp.store_id,
    st.store_code,
    st.name AS store_name,
    pp.promotion_type,
    pp.discount_type,
    pp.promotional_price,
    pp.original_price,
    pp.discount_value,
    pp.margin_percent,
    pp.expected_units_sold,
    pp.expected_revenue,
    pp.proposed_valid_from,
    pp.proposed_valid_until,
    pp.agent_reasoning,
    pp.market_data,
    pp.status,
    pp.reviewed_by,
    pp.reviewed_at,
    pp.reviewer_notes,
    pp.created_at,
    EXTRACT(EPOCH FROM (NOW() - pp.created_at))/3600 AS hours_pending
FROM pending_promotions pp
JOIN skus s ON pp.sku_id = s.id
JOIN stores st ON pp.store_id = st.id
ORDER BY pp.created_at DESC;

-- ============================================================================
-- FUNCTIONS & TRIGGERS
-- ============================================================================

-- Update timestamp trigger function
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply update trigger to relevant tables
CREATE TRIGGER update_stores_updated_at BEFORE UPDATE ON stores
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_skus_updated_at BEFORE UPDATE ON skus
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_inventory_updated_at BEFORE UPDATE ON inventory
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_promotions_updated_at BEFORE UPDATE ON promotions
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Function to calculate sell-through rate
CREATE OR REPLACE FUNCTION calculate_sell_through_rate(
    p_sku_id INTEGER,
    p_store_id INTEGER,
    p_days INTEGER DEFAULT 7
)
RETURNS DECIMAL AS $$
DECLARE
    total_sold INTEGER;
    avg_daily DECIMAL;
BEGIN
    SELECT COALESCE(SUM(quantity_sold), 0)
    INTO total_sold
    FROM sales_transactions
    WHERE sku_id = p_sku_id
      AND store_id = p_store_id
      AND transaction_date >= CURRENT_TIMESTAMP - (p_days || ' days')::INTERVAL;

    avg_daily := total_sold::DECIMAL / p_days;
    RETURN avg_daily;
END;
$$ LANGUAGE plpgsql;

-- Function to get current margin for SKU at store
CREATE OR REPLACE FUNCTION get_current_margin(
    p_sku_id INTEGER,
    p_current_price DECIMAL
)
RETURNS DECIMAL AS $$
DECLARE
    base_cost DECIMAL;
    margin DECIMAL;
BEGIN
    SELECT s.base_cost INTO base_cost
    FROM skus s
    WHERE s.id = p_sku_id;

    IF base_cost IS NULL OR base_cost = 0 THEN
        RETURN 0;
    END IF;

    margin := ((p_current_price - base_cost) / p_current_price) * 100;
    RETURN ROUND(margin, 2);
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- INITIAL DATA SETUP
-- ============================================================================

-- Grant permissions
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO pricing_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO pricing_user;
GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO pricing_user;

-- Log schema initialization
INSERT INTO simulator_state (simulator_type, state_data)
VALUES ('schema_version', jsonb_build_object('version', '1.0.0', 'initialized_at', CURRENT_TIMESTAMP));

COMMENT ON DATABASE pricing_intelligence IS 'Autonomous Pricing Intelligence and Promotion Management System';
