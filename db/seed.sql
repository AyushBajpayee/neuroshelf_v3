-- Pricing Intelligence Database Seed Data
-- Version: 1.0.0
-- Description: Sample data for testing and demonstration

-- ============================================================================
-- STORES / LOCATIONS
-- ============================================================================

INSERT INTO stores (store_code, name, address, city, state, zip_code, latitude, longitude) VALUES
('STORE-001', 'Downtown Market', '123 Main St', 'Springfield', 'IL', '62701', 39.7817, -89.6501),
('STORE-002', 'Northside Grocery', '456 Oak Ave', 'Springfield', 'IL', '62702', 39.8317, -89.6301),
('STORE-003', 'Westend Supermart', '789 Pine Rd', 'Springfield', 'IL', '62704', 39.7717, -89.7001),
('STORE-004', 'Eastside Market', '321 Elm St', 'Springfield', 'IL', '62703', 39.7917, -89.6001),
('STORE-005', 'Southgate Plaza', '654 Maple Dr', 'Springfield', 'IL', '62705', 39.7417, -89.6601);

-- ============================================================================
-- PRODUCT CATALOG (SKUs)
-- ============================================================================

INSERT INTO skus (sku_code, name, category, subcategory, base_cost, base_price, target_margin_percent, min_margin_percent, unit) VALUES
-- Ice Cream & Frozen
('ICECREAM-VANILLA-001', 'Premium Vanilla Ice Cream 1L', 'Frozen', 'Ice Cream', 3.50, 6.99, 25.00, 12.00, 'unit'),
('ICECREAM-CHOC-001', 'Chocolate Fudge Ice Cream 1L', 'Frozen', 'Ice Cream', 3.75, 7.49, 25.00, 12.00, 'unit'),
('ICECREAM-STRAW-001', 'Strawberry Swirl Ice Cream 1L', 'Frozen', 'Ice Cream', 3.60, 7.29, 25.00, 12.00, 'unit'),
('POPSICLE-MULTI-001', 'Fruit Popsicles 12-Pack', 'Frozen', 'Frozen Treats', 2.80, 5.99, 28.00, 15.00, 'pack'),

-- Beverages
('SODA-COLA-001', 'Cola 2L Bottle', 'Beverages', 'Soft Drinks', 1.20, 2.99, 30.00, 15.00, 'bottle'),
('SODA-LEMON-001', 'Lemon-Lime Soda 2L', 'Beverages', 'Soft Drinks', 1.15, 2.89, 30.00, 15.00, 'bottle'),
('WATER-SPRING-001', 'Spring Water 24-Pack', 'Beverages', 'Water', 3.00, 5.99, 25.00, 12.00, 'pack'),
('JUICE-ORANGE-001', 'Fresh Orange Juice 1L', 'Beverages', 'Juice', 2.50, 4.99, 25.00, 12.00, 'bottle'),

-- Snacks
('CHIPS-SALT-001', 'Salted Potato Chips 200g', 'Snacks', 'Chips', 1.50, 3.49, 28.00, 15.00, 'bag'),
('CHIPS-BBQ-001', 'BBQ Flavored Chips 200g', 'Snacks', 'Chips', 1.55, 3.49, 27.00, 15.00, 'bag'),
('POPCORN-BUTTER-001', 'Butter Popcorn 3-Pack', 'Snacks', 'Popcorn', 2.00, 4.29, 27.00, 14.00, 'pack'),
('NUTS-MIXED-001', 'Mixed Nuts 300g', 'Snacks', 'Nuts', 4.00, 7.99, 25.00, 12.00, 'bag'),

-- Bakery
('BREAD-WHITE-001', 'White Sandwich Bread', 'Bakery', 'Bread', 1.20, 2.99, 30.00, 15.00, 'loaf'),
('BREAD-WHEAT-001', 'Whole Wheat Bread', 'Bakery', 'Bread', 1.40, 3.49, 30.00, 15.00, 'loaf'),
('COOKIES-CHOC-001', 'Chocolate Chip Cookies 12-Pack', 'Bakery', 'Cookies', 2.50, 5.49, 27.00, 14.00, 'pack'),
('MUFFIN-BLUE-001', 'Blueberry Muffins 4-Pack', 'Bakery', 'Muffins', 2.00, 4.49, 28.00, 15.00, 'pack'),

-- Dairy
('MILK-WHOLE-001', 'Whole Milk 1 Gallon', 'Dairy', 'Milk', 2.50, 4.99, 25.00, 12.00, 'gallon'),
('MILK-SKIM-001', 'Skim Milk 1 Gallon', 'Dairy', 'Milk', 2.40, 4.89, 25.00, 12.00, 'gallon'),
('YOGURT-VANILLA-001', 'Vanilla Yogurt 6-Pack', 'Dairy', 'Yogurt', 2.80, 5.49, 24.00, 12.00, 'pack'),
('CHEESE-CHEDDAR-001', 'Cheddar Cheese Block 500g', 'Dairy', 'Cheese', 4.50, 8.99, 25.00, 12.00, 'block');

-- ============================================================================
-- INVENTORY LEVELS
-- ============================================================================

-- Generate inventory for all SKUs across all stores with varying levels
INSERT INTO inventory (sku_id, store_id, quantity, reorder_point, max_capacity)
SELECT
    s.id AS sku_id,
    st.id AS store_id,
    -- Random quantity between 50 and 800
    FLOOR(50 + RANDOM() * 750)::INTEGER AS quantity,
    100 AS reorder_point,
    1000 AS max_capacity
FROM skus s
CROSS JOIN stores st;

-- Create some excess inventory scenarios (for testing promotion triggers)
UPDATE inventory SET quantity = 850 WHERE sku_id = (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001') AND store_id = 1;
UPDATE inventory SET quantity = 920 WHERE sku_id = (SELECT id FROM skus WHERE sku_code = 'ICECREAM-CHOC-001') AND store_id = 2;
UPDATE inventory SET quantity = 780 WHERE sku_id = (SELECT id FROM skus WHERE sku_code = 'SODA-COLA-001') AND store_id = 3;

-- Create some low inventory scenarios
UPDATE inventory SET quantity = 45 WHERE sku_id = (SELECT id FROM skus WHERE sku_code = 'MILK-WHOLE-001') AND store_id = 4;
UPDATE inventory SET quantity = 38 WHERE sku_id = (SELECT id FROM skus WHERE sku_code = 'BREAD-WHITE-001') AND store_id = 5;

-- ============================================================================
-- HISTORICAL SALES TRANSACTIONS (Last 30 Days)
-- ============================================================================

-- Generate realistic sales data
DO $$
DECLARE
    sku_rec RECORD;
    store_rec RECORD;
    days_back INTEGER;
    daily_sales INTEGER;
    transaction_counter INTEGER := 1;
BEGIN
    FOR sku_rec IN SELECT id, base_price FROM skus LOOP
        FOR store_rec IN SELECT id FROM stores LOOP
            FOR days_back IN 1..30 LOOP
                -- Random sales per day between 5 and 50 units
                daily_sales := FLOOR(5 + RANDOM() * 45)::INTEGER;

                INSERT INTO sales_transactions (
                    transaction_id,
                    sku_id,
                    store_id,
                    quantity_sold,
                    unit_price,
                    total_amount,
                    transaction_date
                ) VALUES (
                    'TXN-' || LPAD(transaction_counter::TEXT, 10, '0'),
                    sku_rec.id,
                    store_rec.id,
                    daily_sales,
                    sku_rec.base_price,
                    daily_sales * sku_rec.base_price,
                    CURRENT_TIMESTAMP - (days_back || ' days')::INTERVAL - (RANDOM() * INTERVAL '23 hours')
                );

                transaction_counter := transaction_counter + 1;
            END LOOP;
        END LOOP;
    END LOOP;
END $$;

-- Add some spike sales for ice cream on hot days (simulated)
INSERT INTO sales_transactions (
    transaction_id, sku_id, store_id, quantity_sold, unit_price, total_amount, transaction_date
)
SELECT
    'TXN-SPIKE-' || generate_series,
    (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001'),
    (SELECT id FROM stores WHERE store_code = 'STORE-001'),
    FLOOR(80 + RANDOM() * 40)::INTEGER,
    6.99,
    (FLOOR(80 + RANDOM() * 40)::INTEGER) * 6.99,
    CURRENT_TIMESTAMP - (generate_series || ' days')::INTERVAL
FROM generate_series(5, 8);

-- ============================================================================
-- PRICING HISTORY
-- ============================================================================

-- Sample pricing changes
INSERT INTO pricing_history (sku_id, store_id, old_price, new_price, margin_percent, reason, changed_by, effective_date) VALUES
((SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001'), 1, 7.49, 6.99, 25.00, 'Initial pricing adjustment', 'system', CURRENT_TIMESTAMP - INTERVAL '25 days'),
((SELECT id FROM skus WHERE sku_code = 'SODA-COLA-001'), 2, 3.29, 2.99, 30.00, 'Competitive pricing', 'system', CURRENT_TIMESTAMP - INTERVAL '20 days'),
((SELECT id FROM skus WHERE sku_code = 'CHIPS-SALT-001'), 3, 3.99, 3.49, 28.00, 'Promotional pricing', 'agent', CURRENT_TIMESTAMP - INTERVAL '15 days');

-- ============================================================================
-- COMPETITOR PRICES (Current State)
-- ============================================================================

-- Competitor A: Aggressive Pricing Strategy (10-15% below our prices)
INSERT INTO competitor_prices (competitor_name, sku_id, store_id, competitor_price, competitor_promotion, observed_date)
SELECT
    'Competitor A - MegaMart',
    s.id,
    st.id,
    ROUND((s.base_price * 0.85)::NUMERIC, 2),
    FALSE,
    CURRENT_TIMESTAMP - INTERVAL '2 hours'
FROM skus s
CROSS JOIN (SELECT id FROM stores LIMIT 3) st;

-- Competitor B: Premium Pricing Strategy (10-20% above our prices)
INSERT INTO competitor_prices (competitor_name, sku_id, store_id, competitor_price, competitor_promotion, observed_date)
SELECT
    'Competitor B - Premium Foods',
    s.id,
    st.id,
    ROUND((s.base_price * 1.15)::NUMERIC, 2),
    FALSE,
    CURRENT_TIMESTAMP - INTERVAL '3 hours'
FROM skus s
CROSS JOIN (SELECT id FROM stores LIMIT 3) st;

-- Competitor C: Follower Strategy (matches lowest in market)
INSERT INTO competitor_prices (competitor_name, sku_id, store_id, competitor_price, competitor_promotion, observed_date)
SELECT
    'Competitor C - QuickStop',
    s.id,
    st.id,
    ROUND((s.base_price * 0.88)::NUMERIC, 2),
    FALSE,
    CURRENT_TIMESTAMP - INTERVAL '1 hour'
FROM skus s
CROSS JOIN (SELECT id FROM stores LIMIT 3) st;

-- Some competitors running promotions
UPDATE competitor_prices
SET competitor_promotion = TRUE,
    competitor_price = competitor_price * 0.80
WHERE competitor_name = 'Competitor A - MegaMart'
  AND sku_id IN (SELECT id FROM skus WHERE category = 'Frozen')
  AND observed_date >= CURRENT_TIMESTAMP - INTERVAL '3 hours';

-- ============================================================================
-- EXTERNAL FACTORS (Sample Events/Conditions)
-- ============================================================================

-- Weather Events
INSERT INTO external_factors (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date) VALUES
('weather', 'Hot Temperature', NULL, '{"temperature_celsius": 32, "condition": "sunny", "humidity": 45}', 75, CURRENT_TIMESTAMP - INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '2 days'),
('weather', 'Rainy Day', NULL, '{"temperature_celsius": 18, "condition": "rain", "humidity": 85}', 60, CURRENT_TIMESTAMP - INTERVAL '5 days', CURRENT_TIMESTAMP - INTERVAL '4 days');

-- Social Events
INSERT INTO external_factors (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date) VALUES
('event', 'Local Music Festival', 1, '{"event_type": "festival", "expected_attendance": 5000, "location": "downtown"}', 85, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP + INTERVAL '3 days'),
('event', 'High School Sports Game', 2, '{"event_type": "sports", "expected_attendance": 2000, "location": "north_stadium"}', 65, CURRENT_TIMESTAMP + INTERVAL '1 day', CURRENT_TIMESTAMP + INTERVAL '1 day'),
('event', 'Community Picnic', 3, '{"event_type": "community", "expected_attendance": 1500, "location": "west_park"}', 55, CURRENT_TIMESTAMP + INTERVAL '2 days', CURRENT_TIMESTAMP + INTERVAL '2 days');

-- Social Media Trends
INSERT INTO external_factors (factor_type, factor_name, store_id, factor_value, intensity, start_date, end_date) VALUES
('trend', 'Ice Cream Challenge', NULL, '{"platform": "social_media", "category": "food", "sentiment": "positive", "mentions": 15000}', 80, CURRENT_TIMESTAMP - INTERVAL '12 hours', CURRENT_TIMESTAMP + INTERVAL '36 hours'),
('trend', 'Healthy Eating', NULL, '{"platform": "social_media", "category": "lifestyle", "sentiment": "positive", "mentions": 8000}', 60, CURRENT_TIMESTAMP - INTERVAL '3 days', CURRENT_TIMESTAMP + INTERVAL '4 days');

-- ============================================================================
-- HISTORICAL PROMOTIONS (For Learning/Training)
-- ============================================================================

-- Successful Flash Sale Example
INSERT INTO promotions (
    promotion_code, sku_id, store_id, promotion_type, discount_type, discount_value,
    original_price, promotional_price, margin_percent, target_radius_km,
    valid_from, valid_until, status, expected_units_sold, expected_revenue,
    actual_units_sold, actual_revenue, created_by, reason
) VALUES (
    'PROMO-FLASH-001',
    (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001'),
    1,
    'flash_sale',
    'percentage',
    30.00,
    6.99,
    4.89,
    18.50,
    5.0,
    CURRENT_TIMESTAMP - INTERVAL '10 days',
    CURRENT_TIMESTAMP - INTERVAL '10 days' + INTERVAL '2 hours',
    'completed',
    80,
    391.20,
    95,
    464.55,
    'agent',
    'High temperature forecasted, excess inventory, competitive pricing pressure'
);

-- Moderately Successful Coupon
INSERT INTO promotions (
    promotion_code, sku_id, store_id, promotion_type, discount_type, discount_value,
    original_price, promotional_price, margin_percent, target_radius_km,
    valid_from, valid_until, status, expected_units_sold, expected_revenue,
    actual_units_sold, actual_revenue, created_by, reason
) VALUES (
    'PROMO-COUPON-001',
    (SELECT id FROM skus WHERE sku_code = 'SODA-COLA-001'),
    2,
    'coupon',
    'percentage',
    20.00,
    2.99,
    2.39,
    20.00,
    10.0,
    CURRENT_TIMESTAMP - INTERVAL '7 days',
    CURRENT_TIMESTAMP - INTERVAL '7 days' + INTERVAL '4 hours',
    'completed',
    120,
    286.80,
    98,
    234.22,
    'agent',
    'Moderate inventory, local event nearby, competitor promotion active'
);

-- Retracted Promotion (Margin Too Low)
INSERT INTO promotions (
    promotion_code, sku_id, store_id, promotion_type, discount_type, discount_value,
    original_price, promotional_price, margin_percent, target_radius_km,
    valid_from, valid_until, status, expected_units_sold, expected_revenue,
    actual_units_sold, actual_revenue, created_by, reason, retraction_reason, retracted_at
) VALUES (
    'PROMO-RETRACT-001',
    (SELECT id FROM skus WHERE sku_code = 'CHIPS-SALT-001'),
    3,
    'discount',
    'percentage',
    40.00,
    3.49,
    2.09,
    8.50,
    3.0,
    CURRENT_TIMESTAMP - INTERVAL '5 days',
    CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '6 hours',
    'retracted',
    150,
    313.50,
    15,
    31.35,
    'agent',
    'Testing aggressive discount strategy',
    'Performance below threshold (10% of expected), margin dangerously low',
    CURRENT_TIMESTAMP - INTERVAL '5 days' + INTERVAL '1 hour'
);

-- ============================================================================
-- PROMOTION PERFORMANCE LOGS
-- ============================================================================

INSERT INTO promotion_performance (promotion_id, check_time, units_sold_so_far, revenue_so_far, performance_ratio, is_profitable, margin_maintained, notes)
SELECT
    id,
    valid_from + INTERVAL '30 minutes',
    FLOOR(actual_units_sold * 0.3),
    ROUND((actual_revenue * 0.3)::NUMERIC, 2),
    0.30,
    TRUE,
    TRUE,
    'First check - 30 minutes in'
FROM promotions WHERE status = 'completed' AND promotion_code = 'PROMO-FLASH-001';

INSERT INTO promotion_performance (promotion_id, check_time, units_sold_so_far, revenue_so_far, performance_ratio, is_profitable, margin_maintained, notes)
SELECT
    id,
    valid_from + INTERVAL '1 hour',
    FLOOR(actual_units_sold * 0.65),
    ROUND((actual_revenue * 0.65)::NUMERIC, 2),
    0.65,
    TRUE,
    TRUE,
    'Second check - 1 hour in, exceeding expectations'
FROM promotions WHERE status = 'completed' AND promotion_code = 'PROMO-FLASH-001';

-- ============================================================================
-- AGENT DECISION LOG (Sample Historical Decisions)
-- ============================================================================

INSERT INTO agent_decisions (agent_name, sku_id, store_id, decision_type, reasoning, data_used, decision_outcome, promotion_id)
VALUES
(
    'Market Analysis Agent',
    (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001'),
    1,
    'create_promotion',
    'Detected strong opportunity: High temperature (32°C), excess inventory (850 units vs 600 capacity target), competitor running promotion, trending social topic related to ice cream. Recommend aggressive 2-hour flash sale to capitalize on demand spike.',
    '{"inventory": 850, "sell_through_7d": 45, "weather_temp": 32, "competitor_lowest_price": 5.95, "trend_intensity": 80}',
    'executed',
    (SELECT id FROM promotions WHERE promotion_code = 'PROMO-FLASH-001')
),
(
    'Monitoring Agent',
    (SELECT id FROM skus WHERE sku_code = 'CHIPS-SALT-001'),
    3,
    'retract_promotion',
    'Promotion underperforming significantly. After 1 hour, only 10% of expected sales achieved. Margin has dropped to 8.5%, below minimum threshold of 10%. Recommend immediate retraction to prevent losses.',
    '{"expected_units": 150, "actual_units": 15, "performance_ratio": 0.10, "current_margin": 8.5, "min_margin": 10.0}',
    'executed',
    (SELECT id FROM promotions WHERE promotion_code = 'PROMO-RETRACT-001')
);

-- ============================================================================
-- TOKEN USAGE (Sample for Cost Tracking)
-- ============================================================================

-- Simulate some historical token usage
INSERT INTO token_usage (timestamp, agent_name, operation, model, prompt_tokens, completion_tokens, total_tokens, estimated_cost, sku_id)
VALUES
(CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Data Collection Agent', 'collect_sku_data', 'gpt-4o-mini', 450, 120, 570, 0.000140, (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001')),
(CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Market Analysis Agent', 'analyze_opportunity', 'gpt-4o-mini', 680, 280, 960, 0.000270, (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001')),
(CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Pricing Strategy Agent', 'calculate_optimal_price', 'gpt-4o-mini', 520, 180, 700, 0.000186, (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001')),
(CURRENT_TIMESTAMP - INTERVAL '2 hours', 'Promotion Design Agent', 'design_promotion', 'gpt-4o-mini', 890, 340, 1230, 0.000338, (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001')),
(CURRENT_TIMESTAMP - INTERVAL '1 hour', 'Monitoring Agent', 'check_promotion_performance', 'gpt-4o-mini', 380, 95, 475, 0.000114, (SELECT id FROM skus WHERE sku_code = 'ICECREAM-VANILLA-001'));

-- ============================================================================
-- SIMULATOR STATE INITIALIZATION
-- ============================================================================

INSERT INTO simulator_state (simulator_type, state_data) VALUES
('weather', jsonb_build_object('initialized', true, 'base_temperature', 25, 'season', 'summer', 'last_update', CURRENT_TIMESTAMP)),
('competitor', jsonb_build_object('initialized', true, 'competitors_count', 3, 'last_price_update', CURRENT_TIMESTAMP)),
('social', jsonb_build_object('initialized', true, 'active_trends', 2, 'upcoming_events', 3, 'last_update', CURRENT_TIMESTAMP));

-- ============================================================================
-- DATA QUALITY CHECKS
-- ============================================================================

-- Verify row counts
DO $$
DECLARE
    store_count INTEGER;
    sku_count INTEGER;
    inventory_count INTEGER;
    sales_count INTEGER;
BEGIN
    SELECT COUNT(*) INTO store_count FROM stores;
    SELECT COUNT(*) INTO sku_count FROM skus;
    SELECT COUNT(*) INTO inventory_count FROM inventory;
    SELECT COUNT(*) INTO sales_count FROM sales_transactions;

    RAISE NOTICE '=== Seed Data Summary ===';
    RAISE NOTICE 'Stores: %', store_count;
    RAISE NOTICE 'SKUs: %', sku_count;
    RAISE NOTICE 'Inventory Records: %', inventory_count;
    RAISE NOTICE 'Sales Transactions: %', sales_count;
    RAISE NOTICE 'Seed data loaded successfully!';
END $$;
