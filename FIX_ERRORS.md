# Fix Instructions

## Errors Found

1. **v_pending_promotions view doesn't exist** - Database was created before we added the pending_promotions table to init.sql
2. **Streamlit "connection already closed" errors** - Cached database connections being reused after closing
3. **LangGraph not making LLM calls** - Agent can't get SKUs because query_inventory_levels missing sku_id/store_id fields

## Fixes Applied

1. ✅ Removed `@st.cache_resource` from `streamlit/app.py` to prevent connection caching
2. ✅ Fixed `query_inventory_levels` in `mcp-servers/postgres/server.py` to include `sku_id` and `store_id` fields
3. ✅ Added `WHERE s.is_active = true` filter to only query active SKUs

## Steps to Apply Fixes

Run these commands in order:

### 1. Stop all containers
```bash
docker-compose down
```

### 2. Remove the old database volume (this will recreate from init.sql)
```bash
docker volume rm neuroshelf_v3_postgres_data
```

### 3. Rebuild and start all containers
```bash
docker-compose up --build -d
```

### 4. Wait for initialization (2-3 minutes)
Watch the logs to ensure database initializes:
```bash
docker-compose logs -f postgres
```

Wait until you see:
```
PostgreSQL init process complete; ready for start up.
database system is ready to accept connections
```

Then press Ctrl+C to stop watching logs.

### 5. Verify database tables and views
```bash
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence -c "\dt"
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence -c "\dv"
```

You should see `pending_promotions` table and `v_pending_promotions` view.

### 6. Check that SKUs exist
```bash
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence -c "SELECT COUNT(*) FROM skus WHERE is_active = true;"
```

Should show a count > 0 (e.g., 12 SKUs from seed data).

### 7. Monitor LangGraph agent
```bash
docker-compose logs -f langgraph-core
```

You should see:
- "Analyzing X SKU/store combinations..." (X should be > 0)
- Agent logs showing data collection, market analysis, etc.
- LLM calls being made

### 8. Test Streamlit UI
Open http://localhost:8501

- **Dashboard**: Should show metrics without "connection closed" errors
- **Approval Queue**: Should load without "v_pending_promotions does not exist" error
- Other pages should work normally

### 9. Verify OpenAI API calls
After a few agent cycles (wait 2-3 minutes), check:
- LangGraph logs should show agent decision-making
- OpenAI dashboard should show API usage increasing
- Token usage should appear in Streamlit "Token & Cost Tracker" page

## Troubleshooting

### If database doesn't initialize:
```bash
# Check postgres logs
docker-compose logs postgres

# Common issue: Volume not deleted
docker volume ls | grep postgres
docker volume rm neuroshelf_v3_postgres_data

# Retry
docker-compose up -d postgres
```

### If LangGraph still shows "Error getting SKUs":
```bash
# Check MCP postgres is healthy
docker-compose ps mcp-postgres

# Test MCP tool directly
curl -X POST http://localhost:3000/tool \
  -H "Content-Type: application/json" \
  -d '{"tool_name": "query_inventory_levels", "parameters": {}}'

# Should return JSON with sku_id and store_id fields
```

### If no LLM calls are happening:
```bash
# Verify OpenAI API key
docker-compose exec langgraph-core env | grep OPENAI_API_KEY

# Check config
docker-compose exec langgraph-core cat config.py
```

## Expected Behavior After Fixes

1. **Dashboard**: Shows 5 metrics including "Pending Approval" count
2. **Approval Queue**: Loads with empty state (no pending promotions yet)
3. **LangGraph Agent**:
   - Analyzes SKUs every 30 minutes (or 1 minute based on config)
   - Makes LLM calls to GPT-4o-mini
   - Creates promotions (or pending promotions if manual approval enabled)
4. **OpenAI Dashboard**: Shows increasing token usage
5. **Token Tracker**: Shows cost accumulation by agent

## Configuration Options

### To enable manual approval workflow:
Edit `langgraph/config.py`:
```python
AGENT_CONFIG = {
    "require_manual_approval": True,  # Change to True
    # ... other settings
}
```

Then restart:
```bash
docker-compose restart langgraph-core
```

Now agents will create pending promotions instead of auto-activating them.
