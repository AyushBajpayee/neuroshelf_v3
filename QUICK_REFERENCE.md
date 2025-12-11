# Quick Reference Guide

## Essential Commands

### Start System
```bash
docker-compose up
```

### Start in Background
```bash
docker-compose up -d
```

### Stop System
```bash
docker-compose down
```

### Rebuild After Code Changes
```bash
docker-compose up --build
```

### View Logs
```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f langgraph-core
```

### Restart Single Service
```bash
docker-compose restart streamlit
```

## Access Points

| Service | URL | Purpose |
|---------|-----|---------|
| Streamlit UI | http://localhost:8501 | Main dashboard and control |
| LangGraph Studio | http://localhost:8080 | Agent workflow visualization |
| LangGraph API | http://localhost:8000 | Agent API endpoints |
| PostgreSQL | localhost:5432 | Database access |
| MCP Postgres | http://localhost:3000 | Database operations API |
| MCP Weather | http://localhost:3001 | Weather simulator API |
| MCP Competitor | http://localhost:3002 | Competitor simulator API |
| MCP Social | http://localhost:3003 | Social trends simulator API |

## Database Credentials

```
Host: localhost
Port: 5432
Database: pricing_intelligence
User: pricing_user
Password: pricing_pass
```

## API Endpoints

### LangGraph Core API

```bash
# Health check
curl http://localhost:8000/health

# Get agent status
curl http://localhost:8000/status

# Manually trigger analysis
curl -X POST "http://localhost:8000/trigger?sku_id=1&store_id=1"
```

### MCP Server Health Checks

```bash
curl http://localhost:3000/health  # Postgres
curl http://localhost:3001/health  # Weather
curl http://localhost:3002/health  # Competitor
curl http://localhost:3003/health  # Social
```

## Common Database Queries

### Connect to Database
```bash
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence
```

### Useful Queries (run in psql)

```sql
-- View active promotions
SELECT * FROM v_active_promotions;

-- View inventory status
SELECT * FROM v_inventory_status;

-- View recent agent decisions
SELECT agent_name, decision_type, reasoning, created_at
FROM agent_decisions
ORDER BY created_at DESC
LIMIT 10;

-- View token costs
SELECT * FROM v_cost_by_agent;

-- View promotion ROI
SELECT * FROM v_promotion_roi
ORDER BY roi_ratio DESC
LIMIT 10;

-- Count promotions by status
SELECT status, COUNT(*) as count
FROM promotions
GROUP BY status;

-- View sell-through rates
SELECT * FROM v_sell_through_rate
WHERE avg_daily_sales > 0
ORDER BY avg_daily_sales DESC;
```

## Configuration Quick Changes

### Edit .env File
```bash
notepad .env  # Windows
nano .env     # Linux/Mac
```

### Key Configuration Variables

```bash
# Agent runs every X minutes
AGENT_MONITORING_INTERVAL_MINUTES=30

# Minimum profit margin (%)
AGENT_MIN_MARGIN_PERCENT=10

# Maximum discount allowed (%)
AGENT_MAX_DISCOUNT_PERCENT=40

# Auto-retract threshold (0.0-1.0)
# 0.5 means retract if performance < 50% of expected
AGENT_AUTO_RETRACT_THRESHOLD=0.5

# Require manual approval
AGENT_REQUIRE_MANUAL_APPROVAL=false
```

## Simulator API Examples

### Weather Simulator

```bash
# Get current weather
curl http://localhost:3001/weather/1

# Get forecast
curl http://localhost:3001/forecast/1?hours=24

# Set heatwave scenario
curl -X POST "http://localhost:3001/scenario?location_id=1&scenario=heatwave&duration_hours=48"
```

### Competitor Simulator

```bash
# Get competitor prices
curl http://localhost:3002/prices/1

# Trigger competitor promotion
curl -X POST "http://localhost:3002/promotion/trigger?competitor_name=Competitor%20A%20-%20MegaMart&sku_id=1&discount_percent=25"

# End promotion
curl -X POST "http://localhost:3002/promotion/end?competitor_name=Competitor%20A%20-%20MegaMart&sku_id=1"
```

### Social Trends Simulator

```bash
# Get trending topics
curl http://localhost:3003/trending

# Get upcoming events
curl http://localhost:3003/events?days_ahead=7

# Inject viral moment
curl -X POST "http://localhost:3003/viral?topic=Ice%20Cream%20Festival&intensity=85"
```

## Troubleshooting Quick Fixes

### Port Already in Use
```bash
# Find and kill process using port (example: 5432)
netstat -ano | findstr :5432     # Windows
lsof -ti:5432 | xargs kill -9    # Linux/Mac

# Or change port in docker-compose.yml
```

### Database Not Ready
```bash
# Wait for postgres to be ready
docker-compose logs postgres | grep "ready to accept connections"

# Should see this message twice, then services can connect
```

### Agent Not Running
```bash
# Check logs
docker-compose logs langgraph-core

# Verify OpenAI key is set
docker-compose exec langgraph-core printenv OPENAI_API_KEY

# Restart agent
docker-compose restart langgraph-core
```

### Streamlit Connection Error
```bash
# Restart streamlit
docker-compose restart streamlit

# Check if database is accessible
docker-compose exec streamlit ping postgres -c 3

# View streamlit logs
docker-compose logs streamlit --tail=50
```

### Out of Memory
```bash
# Check Docker resource usage
docker stats

# Increase Docker memory limit
# Docker Desktop → Settings → Resources → Memory → Increase to 8GB+
```

### Clear All Data and Restart Fresh
```bash
# WARNING: This deletes all data!
docker-compose down -v
docker-compose up --build
```

## Monitoring & Debugging

### Watch Agent Decisions in Real-Time
```bash
docker-compose logs -f langgraph-core | grep "\[.*Agent\]"
```

### Monitor Database Activity
```sql
-- In psql, show recent activity
SELECT COUNT(*) as active_connections
FROM pg_stat_activity
WHERE datname = 'pricing_intelligence';

-- Show table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
```

### Check Container Resource Usage
```bash
docker stats --no-stream
```

## File Structure Quick Reference

```
neuroshelf_v3/
├── db/                      # Database initialization
│   ├── init.sql            # Schema
│   └── seed.sql            # Sample data
├── mcp-servers/            # MCP server implementations
│   ├── postgres/           # Database operations
│   ├── weather-simulator/  # Weather simulation
│   ├── competitor-simulator/  # Competitor pricing
│   └── social-simulator/   # Social trends
├── langgraph/              # Agent system
│   ├── agents/             # Individual agent implementations
│   ├── graph.py            # Workflow definition
│   ├── main.py             # Entry point
│   └── config.py           # Configuration
├── langgraph-studio/       # Visualization server
├── streamlit/              # UI application
│   ├── pages/              # Dashboard pages
│   └── app.py              # Main app
├── docker-compose.yml      # Container orchestration
├── .env                    # Environment variables (SECRET!)
├── README.md               # Full documentation
├── STARTUP_GUIDE.md        # Detailed startup instructions
└── QUICK_REFERENCE.md      # This file
```

## Performance Tips

### Reduce Costs
- Increase `AGENT_MONITORING_INTERVAL_MINUTES` to 60 or higher
- Reduce number of SKUs in `db/seed.sql` before first run
- Set `AGENT_REQUIRE_MANUAL_APPROVAL=true` to prevent auto-execution

### Faster Response
- Decrease `AGENT_MONITORING_INTERVAL_MINUTES` to 15
- Note: Increases token usage and costs

### Better Performance
- Ensure Docker has at least 8GB RAM
- Use SSD for Docker volumes
- Close unnecessary applications

## Backup & Restore

### Backup Database
```bash
docker-compose exec postgres pg_dump -U pricing_user pricing_intelligence > backup.sql
```

### Restore Database
```bash
cat backup.sql | docker-compose exec -T postgres psql -U pricing_user pricing_intelligence
```

## Getting Help

1. Check main README.md
2. Review STARTUP_GUIDE.md
3. Check Docker logs: `docker-compose logs [service]`
4. Verify .env file has correct API keys
5. Check LangSmith traces (if enabled)

---

**For full documentation, see README.md**
**For detailed setup, see STARTUP_GUIDE.md**
