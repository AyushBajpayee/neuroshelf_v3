# Manual Approval Workflow

## Overview

The Manual Approval Workflow allows human operators to review and approve agent-recommended promotions before they go live. This provides an extra layer of control and oversight for high-stakes pricing decisions.

## When to Use Manual Approval

Enable manual approval mode when:
- Testing new agent strategies in production
- Operating in regulated industries requiring human oversight
- Managing high-value products where errors are costly
- Training new agents and validating their decision-making
- Compliance requirements mandate human-in-the-loop processes

## Configuration

### Enable Manual Approval

Edit `langgraph/config.py`:

```python
AGENT_CONFIG = {
    "monitoring_interval_minutes": 30,
    "min_margin_percent": 10,
    "max_discount_percent": 40,
    "auto_retract_threshold": 0.5,
    "require_manual_approval": True,  # Enable manual approval workflow
}
```

Then restart the LangGraph container:
```bash
docker-compose restart langgraph-core
```

To persist approval/rejection decisions as learning signals, enable:

```bash
ENABLE_APPROVAL_LEARNING=true
```

## How It Works

### 1. Agent Creates Promotion Recommendation

When the agent determines a promotion should be created:

**Auto Mode** (`require_manual_approval=False`):
- Promotion is written directly to `promotions` table
- Status is set to `active` immediately
- Promotion goes live at `valid_from` timestamp

**Manual Approval Mode** (`require_manual_approval=True`):
- Promotion is saved to `pending_promotions` table
- Status is set to `pending`
- Agent includes full reasoning and market data
- Promotion does NOT activate automatically

### 2. Review in Approval Queue

Access the Approval Queue UI:
- Navigate to **Streamlit UI** → **Approval Queue** page
- View all pending promotions with detailed information

Each pending promotion shows:
- **Product & Store Details**: SKU name, category, store location
- **Pricing Information**: Original price, promotional price, discount amount, margin %
- **Timing**: Proposed start/end timestamps
- **Expected Performance**: Estimated units sold and revenue
- **Agent Reasoning**: Full explanation of why this promotion was recommended
- **Market Data**: External factors (weather, competitors, social trends) that influenced the decision

### 3. Make Approval Decision

For each pending promotion, you can:

#### Approve
- Enter your name as reviewer
- Add optional approval notes
- Click **Approve** button
- System creates an active promotion in `promotions` table
- Generates promotion code (e.g., `PROMO-20251211153045-SKU-STORE`)
- Links approved promotion back to pending record
- Updates pending status to `approved`
- If approval learning is enabled, writes a structured signal to `approval_feedback`

#### Reject
- Enter your name as reviewer
- **Required**: Enter rejection reason/notes
- Click **Reject** button
- Pending promotion status updated to `rejected`
- If approval learning is enabled, writes a structured signal to `approval_feedback`
- Agent can learn from rejection patterns over time

### 4. Tracking & Analytics

The Approval Queue page provides:
- **Pending Count**: How many promotions await review
- **Approved Count**: How many have been activated
- **Rejected Count**: How many were declined
- **Approval Rate**: Percentage of approvals (approved / total)

## Database Schema

### `pending_promotions` Table

```sql
CREATE TABLE pending_promotions (
    id SERIAL PRIMARY KEY,

    -- Promotion Details
    sku_id INTEGER NOT NULL REFERENCES skus(id),
    store_id INTEGER NOT NULL REFERENCES stores(id),
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

    -- Expectations
    expected_units_sold INTEGER,
    expected_revenue DECIMAL(10, 2),

    -- Agent Context
    agent_reasoning TEXT NOT NULL,
    market_data JSONB,

    -- Approval Status
    status VARCHAR(50) DEFAULT 'pending',  -- pending, approved, rejected
    reviewed_by VARCHAR(100),
    reviewed_at TIMESTAMP,
    reviewer_notes TEXT,
    approved_promotion_id INTEGER REFERENCES promotions(id),

    -- Metadata
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `approval_feedback` Table

```sql
CREATE TABLE approval_feedback (
    id SERIAL PRIMARY KEY,
    pending_promotion_id INTEGER REFERENCES pending_promotions(id),
    promotion_id INTEGER REFERENCES promotions(id),
    decision_id INTEGER REFERENCES agent_decisions(id),
    sku_id INTEGER REFERENCES skus(id),
    store_id INTEGER REFERENCES stores(id),
    reviewer_outcome VARCHAR(50) NOT NULL, -- approved | rejected
    reviewed_by VARCHAR(100) NOT NULL,
    reviewer_notes TEXT,
    decision_context JSONB,
    feedback_payload JSONB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### `v_pending_promotions` View

Joins `pending_promotions` with `skus` and `stores` for easy querying:
```sql
CREATE VIEW v_pending_promotions AS
SELECT
    pp.*,
    s.sku_code,
    s.name as sku_name,
    s.category,
    st.store_code,
    st.name as store_name,
    st.city,
    st.state
FROM pending_promotions pp
JOIN skus s ON pp.sku_id = s.id
JOIN stores st ON pp.store_id = st.id;
```

## MCP Tools

Four new MCP tools support the approval workflow:

### 1. `create_pending_promotion`
Creates a new pending promotion record.

**Parameters:**
- `sku_id`, `store_id`, `promotion_type`, `discount_type`, `discount_value`
- `original_price`, `promotional_price`, `margin_percent`
- `proposed_valid_from`, `proposed_valid_until`
- `agent_reasoning` (required)
- `target_radius_km`, `target_customer_segment` (optional)
- `expected_units_sold`, `expected_revenue` (optional)
- `market_data` (optional JSONB)

**Returns:** `{id, status, created_at}`

### 2. `get_pending_promotions`
Retrieves pending promotions.

**Parameters:**
- `status` (default: "pending") - Filter by status
- `store_id` (optional) - Filter by store

**Returns:** Array of pending promotion objects with joined SKU/store data

### 3. `approve_promotion`
Approves a pending promotion and activates it.

**Parameters:**
- `pending_promotion_id` (required)
- `reviewed_by` (required) - Reviewer name
- `reviewer_notes` (optional)

**Returns:**
```json
{
    "pending_promotion_id": 123,
    "pending_status": "approved",
    "promotion_id": 456,
    "promotion_code": "PROMO-20251211153045-1-5",
    "promotion_status": "active"
}
```

### 4. `reject_promotion`
Rejects a pending promotion.

**Parameters:**
- `pending_promotion_id` (required)
- `reviewed_by` (required) - Reviewer name
- `reviewer_notes` (required) - Rejection reason

**Returns:** `{id, status, reviewed_by, reviewed_at}`

## UI Components

### Main Dashboard
- **Pending Approval** metric card shows count of pending promotions
- Delta indicator displays "Action Required" when count > 0
- Provides quick visibility into approval queue status

### Approval Queue Page (`7_approval_queue.py`)

Features:
- **Status Filter**: View pending, approved, or rejected promotions
- **Expandable Cards**: Each promotion in an accordion-style expander
- **Detailed Information**: All promotion parameters, reasoning, and market data
- **Inline Forms**: Approve/reject actions directly within each card
- **Real-time Statistics**: Approval rate, counts by status
- **Auto-refresh**: Updates immediately after approve/reject action

## Best Practices

### For Reviewers

1. **Review Agent Reasoning**: Understand why the agent made this recommendation
2. **Validate Margins**: Ensure profitability meets business requirements
3. **Check Market Context**: Review weather, competitor, and social data for relevance
4. **Consider Timing**: Verify promotion window makes sense for the product
5. **Provide Detailed Rejection Notes**: Help the agent learn from mistakes

### For System Administrators

1. **Monitor Approval Rate**: Low approval rates may indicate agent misconfiguration
2. **Analyze Rejection Patterns**: Common rejection reasons suggest needed agent improvements
3. **Set SLAs**: Define maximum time for pending approvals (e.g., 2 hours)
4. **Backup Reviewers**: Ensure multiple people can access approval queue
5. **Audit Trail**: Regularly export approval history for compliance

## Troubleshooting

### Promotions Not Appearing in Queue

**Check agent logs:**
```bash
docker-compose logs langgraph-core | grep "Manual approval"
```

**Verify configuration:**
```bash
docker-compose exec langgraph-core cat config.py | grep require_manual_approval
```

### Cannot Approve/Reject Promotions

**Check MCP postgres logs:**
```bash
docker-compose logs mcp-postgres
```

**Test MCP tool directly:**
```bash
curl -X POST http://localhost:3000/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool_name": "get_pending_promotions",
    "parameters": {"status": "pending"}
  }'
```

### Approved Promotions Not Activating

**Verify promotion was created:**
```sql
SELECT * FROM promotions
WHERE id = (SELECT approved_promotion_id FROM pending_promotions WHERE id = <pending_id>);
```

**Check promotion status:**
```sql
SELECT status, valid_from, valid_until FROM promotions WHERE id = <promotion_id>;
```

## Example Workflow

### Scenario: Ice Cream Promotion During Heatwave

**1. Agent Detects Opportunity** (10:00 AM)
- Inventory: 500 units of vanilla ice cream at Store A
- Weather: 38°C heatwave forecasted for today
- Competitor: Dropped price to $3.99 (we're at $4.99)
- Social: Local music festival trending

**2. Agent Creates Recommendation**
```
Agent: "High demand opportunity due to extreme heat and local event.
Recommend 2-hour flash sale (12:00-14:00) at $3.49 to capture impulse buyers
within 5km radius. Maintains 12% margin, expect 300 units sold, $1,047 revenue."
```

Saved to `pending_promotions` with status `pending`

**3. Manager Reviews** (10:15 AM)
- Opens Approval Queue in Streamlit
- Reviews promotion details:
  - Original: $4.99 → Promo: $3.49 (30% discount)
  - Margin: 12% (above 10% minimum)
  - Window: 12:00-14:00 (2 hours)
  - Target: 5km radius, mobile app users
- Checks market data:
  - Weather: 38°C confirmed
  - Competitor: $3.99 confirmed
  - Social: Festival at 3:00 PM (4,500 attendees)
- Decision: **Approve** (timing is perfect before festival starts)

**4. System Activates** (10:16 AM)
- Creates promotion: `PROMO-20251211101600-15-3`
- Status: `active`
- Will go live at 12:00 PM

**5. Outcome** (14:00 PM)
- Actual: 285 units sold, $995 revenue
- Performance: 95% of expected (excellent)
- Margin maintained: 12.1%
- Manager's decision validated

## Future Enhancements

Potential improvements to approval workflow:

- [ ] Bulk approval for similar promotions
- [ ] Auto-approval rules based on criteria (e.g., margin > 15%, discount < 20%)
- [ ] Mobile notifications for pending approvals
- [ ] Approval authority levels (junior vs senior manager)
- [ ] Time-based auto-rejection (e.g., reject if not reviewed within 2 hours)
- [ ] Agent learning from rejection patterns (reinforcement learning)
- [ ] A/B testing framework (approve 50% of similar promotions for comparison)
- [ ] Integration with calendar systems for reviewer schedules
- [ ] Slack/Teams notifications for new pending promotions
- [ ] Conditional approval (approve with modified parameters)

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Status**: Production Ready
