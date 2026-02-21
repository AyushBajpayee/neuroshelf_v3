# 🚀 Quick Start Guide

## Prerequisites Check

Before starting, ensure you have:

- ✅ Docker Desktop installed and running
- ✅ At least 8GB RAM available for Docker
- ✅ OpenAI API key with GPT-4o-mini access
- ✅ (Optional) LangSmith API key for observability

## Step-by-Step Startup

### 1. Configure Environment Variables

```bash
# Copy the example env file
cp .env.example .env

# Edit .env with your actual API keys
# Use notepad, vim, or any text editor
notepad .env
```

**Required settings in `.env`:**
```
OPENAI_API_KEY=sk-your-actual-openai-key-here
LANGSMITH_API_KEY=your-langsmith-key-here  # Optional
```

### 2. Build and Start All Containers

```bash
# Build all images (first time only, takes 3-5 minutes)
docker-compose build

# Start all services
docker-compose up
```

**What's happening:**
- PostgreSQL initializes database schema and seeds sample data (30-60 seconds)
- 4 MCP servers start and register their tools
- LangGraph agent system initializes and begins monitoring cycle
- LangGraph Studio starts visualization server
- Streamlit UI becomes available

### 3. Verify Everything is Running

Wait 2-3 minutes for all services to initialize, then check:

```bash
# Check container status
docker-compose ps

# All containers should show "Up" status:
# - pricing-postgres
# - pricing-mcp-postgres
# - pricing-mcp-weather
# - pricing-mcp-competitor
# - pricing-mcp-social
# - pricing-langgraph-core
# - pricing-langgraph-studio
# - pricing-streamlit
```

### 4. Access the Applications

Open your browser and navigate to:

- **Streamlit Dashboard**: http://localhost:8501
  - Main interface for monitoring and control
  - All pages accessible via sidebar

- **LangGraph Studio**: http://localhost:8080
  - Visual representation of agent workflow
  - Real-time agent status

- **PostgreSQL**: localhost:5432
  - Use any PostgreSQL client
  - Credentials: `pricing_user` / `pricing_pass`
  - Database: `pricing_intelligence`

### 5. Monitor the Agent Activity

The agent starts working automatically:

1. **Check Streamlit Dashboard** (http://localhost:8501)
   - View active promotions
   - Monitor cost accumulation
   - See system status

2. **Check Docker Logs**
   ```bash
   # Watch agent decisions in real-time
   docker-compose logs -f langgraph-core

   # You should see:
   # - "Agent Cycle Starting..."
   # - "[Data Collector] Gathering data..."
   # - "[Market Analyzer] Analyzing..."
   # - "[Executor] Deploying promotion..." (when opportunities found)
   ```

3. **Verify Database Activity**
   ```bash
   # Connect to postgres and check promotions
   docker-compose exec postgres psql -U pricing_user -d pricing_intelligence

   # Run in psql:
   SELECT COUNT(*) FROM promotions;
   SELECT * FROM promotions ORDER BY created_at DESC LIMIT 5;
   ```

## Troubleshooting

### Issue: Containers won't start

```bash
# Check Docker resources
# Docker Desktop → Settings → Resources
# Ensure at least 8GB RAM allocated

# Check logs
docker-compose logs [service-name]

# Restart specific service
docker-compose restart [service-name]
```

### Issue: "Database connection failed"

```bash
# Wait for postgres to fully initialize (60 seconds)
docker-compose logs postgres | grep "ready to accept connections"

# Restart dependent services
docker-compose restart mcp-postgres langgraph-core streamlit
```

### Issue: Agent not making decisions

```bash
# Check OpenAI API key
docker-compose exec langgraph-core printenv OPENAI_API_KEY

# Check agent logs
docker-compose logs langgraph-core | tail -50

# Manually trigger analysis (via Streamlit or API)
curl -X POST http://localhost:8000/trigger?sku_id=1&store_id=1
```

### Issue: Streamlit pages show errors

```bash
# Restart Streamlit
docker-compose restart streamlit

# Check database connectivity
docker-compose exec streamlit ping postgres

# View Streamlit logs
docker-compose logs streamlit
```

## Testing the System

### 1. Test Weather Simulator

Open Streamlit → Simulator Control → Weather Tab

```
1. Get current weather for Location 1
2. Set scenario "heatwave" for Location 1
3. Wait 30 seconds
4. Check if agent creates ice cream promotion
```

### 2. Test Competitor Reaction

Open Streamlit → Simulator Control → Competitors Tab

```
1. View competitor prices for SKU 1
2. Trigger competitor promotion (20% off)
3. Wait for next agent cycle (up to 30 minutes)
4. Check if agent responds with competitive offer
```

### 3. Test Social Trends

Open Streamlit → Simulator Control → Social Tab

```
1. Inject viral moment "Ice Cream Party" with intensity 90
2. Wait for agent cycle
3. Check Dashboard for new promotions on ice cream SKUs
```

## Configuration

### Adjust Agent Behavior

Edit `.env` file:

```bash
# How often agent checks each SKU (in minutes)
AGENT_MONITORING_INTERVAL_MINUTES=30

# Minimum margin to maintain (percent)
AGENT_MIN_MARGIN_PERCENT=10

# Maximum discount allowed (percent)
AGENT_MAX_DISCOUNT_PERCENT=40

# Performance threshold for auto-retraction (0.0-1.0)
AGENT_AUTO_RETRACT_THRESHOLD=0.5

# Require manual approval before executing promotions
AGENT_REQUIRE_MANUAL_APPROVAL=false
```

After changing, restart:
```bash
docker-compose restart langgraph-core
```

## Stopping the System

```bash
# Stop all containers (preserves data)
docker-compose stop

# Stop and remove containers (preserves database volume)
docker-compose down

# Stop, remove containers AND delete all data (fresh start)
docker-compose down -v
```

## Viewing Logs

```bash
# All services
docker-compose logs

# Specific service
docker-compose logs langgraph-core

# Follow logs in real-time
docker-compose logs -f langgraph-core

# Last 50 lines
docker-compose logs --tail=50 streamlit
```

## Database Access

### Using psql (included in postgres container)

```bash
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence
```

### Common Queries

```sql
-- View all active promotions
SELECT * FROM v_active_promotions;

-- View SKU inventory status
SELECT * FROM v_inventory_status WHERE stock_status != 'normal';

-- View agent costs by agent
SELECT * FROM v_cost_by_agent;

-- View promotion ROI
SELECT * FROM v_promotion_roi ORDER BY roi_ratio DESC LIMIT 10;

-- View recent agent decisions
SELECT agent_name, decision_type, reasoning, created_at
FROM agent_decisions
ORDER BY created_at DESC
LIMIT 10;
```

## Performance Optimization

### For Lower Costs

```bash
# Increase monitoring interval to 60 minutes
AGENT_MONITORING_INTERVAL_MINUTES=60

# Reduce number of SKUs in seed data
# Edit db/seed.sql before first run
```

### For Faster Response

```bash
# Decrease monitoring interval to 15 minutes
AGENT_MONITORING_INTERVAL_MINUTES=15

# Note: This increases costs
```

## Next Steps

1. **Explore Streamlit Dashboard**
   - Monitor real-time promotions
   - View cost breakdown
   - Analyze agent decisions

2. **Experiment with Simulators**
   - Trigger extreme weather scenarios
   - Create competitor promotions
   - Inject viral social trends

3. **Review Agent Decisions**
   - Check Analytics page for decision logs
   - Understand agent reasoning
   - Optimize thresholds based on results

4. **Monitor Token Costs**
   - Track daily/weekly spending
   - Identify expensive operations
   - Adjust agent configuration to optimize costs

5. **Analyze Promotion ROI**
   - Compare agent cost vs revenue generated
   - Identify most profitable SKU categories
   - Refine promotion strategies

## Support

If you encounter issues:

1. Check the main README.md troubleshooting section
2. Review Docker logs for specific services
3. Verify all environment variables are set correctly
4. Ensure Docker has sufficient resources allocated
5. Check LangSmith traces if observability is enabled

---

**🎉 Congratulations! Your autonomous pricing intelligence system is now running!**

The agent is continuously monitoring inventory, market conditions, and external factors to automatically create and manage promotional offers. Watch the Streamlit dashboard to see it in action.
