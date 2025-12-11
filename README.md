# Pricing Intelligence and Promotion Agent

A fully autonomous AI-powered system that analyzes inventory, market conditions, and external factors to dynamically create, execute, and retract hyper-personalized promotional offers in real-time.

## 🏗️ Architecture Overview

This application consists of 7 Docker containers working together:

1. **PostgreSQL** - Core database for inventory, pricing, promotions, and analytics
2. **MCP Postgres Server** - Model Context Protocol server for database operations
3. **MCP Weather Simulator** - Realistic weather simulation service
4. **MCP Competitor Simulator** - Competitor pricing behavior simulation
5. **MCP Social Trends Simulator** - Social media trends and events simulation
6. **LangGraph Core** - Multi-agent AI system powered by GPT-5-mini
7. **LangGraph Studio** - Graph visualization server
8. **Streamlit UI** - Interactive web dashboard

## 🚀 Quick Start

### Prerequisites

- Docker Desktop installed and running
- OpenAI API key (GPT-5-mini access)
- LangSmith API key (optional, for observability)
- At least 8GB RAM available for Docker

### Installation

1. **Clone or navigate to the project directory**
```bash
cd neuroshelf_v3
```

2. **Create environment file**
```bash
cp .env.example .env
```

3. **Edit `.env` file with your API keys**
```
OPENAI_API_KEY=sk-your-openai-api-key-here
LANGSMITH_API_KEY=your-langsmith-api-key-here
LANGSMITH_PROJECT=pricing-intelligence-agent
```

4. **Build and start all containers**
```bash
docker-compose up --build
```

5. **Wait for initialization** (first run takes 2-3 minutes)
   - Postgres will initialize schema and seed data
   - MCP servers will start and register tools
   - LangGraph agents will begin monitoring cycle

### Access Points

- **Streamlit UI**: http://localhost:8501
- **LangGraph Studio**: http://localhost:8080
- **PostgreSQL**: localhost:95432 (user: `pricing_user`, password: `pricing_pass`, database: `pricing_intelligence`)

## 📊 Features

### Autonomous Agent System

The system uses 6 specialized agents coordinated by LangGraph:

- **Data Collection Agent** - Gathers inventory, sales, weather, competitor prices, and social trends
- **Market Analysis Agent** - Identifies demand patterns and opportunities
- **Pricing Strategy Agent** - Calculates optimal price points within margin constraints
- **Promotion Design Agent** - Creates hyper-targeted offers (time, location, customer segment)
- **Execution Agent** - Deploys promotions and handles rollbacks
- **Monitoring Agent** - Tracks performance and auto-retracts unprofitable promotions

### External Factor Simulation

All external data is simulated with realistic, controllable behavior:

- **Weather Simulator**
  - Seasonal temperature patterns
  - Random daily variations
  - Extreme weather events (heatwaves, storms)
  - Manual scenario injection via UI

- **Competitor Pricing Simulator**
  - 3 competitors per SKU with distinct strategies (aggressive, premium, follower)
  - Dynamic pricing responses
  - Coordinated sales events
  - Historical trend tracking

- **Social Media Trends Simulator**
  - Calendar-based events (sports, concerts, festivals)
  - Trending topics with decay curves
  - Category-specific sentiment analysis
  - Viral moment injection

### Token Usage & Cost Tracking

- Real-time token consumption monitoring
- Cost breakdown by agent, SKU, and promotion
- Budget alerts and projections
- ROI analysis (promotion cost vs revenue generated)
- GPT-5-mini pricing: $0.150/1M input tokens, $0.600/1M output tokens

### Promotion Capabilities

- **Granularity**: Store-level, time-boxed (1-24 hours)
- **Targeting**: Location radius, customer segment, time windows
- **Safety**: Hard margin floor to prevent losses
- **Autonomy**: Fully automated with optional manual approval mode
- **Manual Approval Workflow**: Review and approve/reject agent recommendations before execution
- **Learning**: Performance tracking for continuous improvement

## 🖥️ User Interface

### Dashboard
- Real-time SKU health indicators
- Active promotion count and revenue impact
- Pending approval count with action indicator
- Cost accumulation tracking
- System alerts and recommendations

### SKU Monitor
- Drill-down view per product
- Current inventory levels across locations
- Sell-through rate trends
- External factors affecting SKU
- Pricing history and competitor comparison

### Promotion Manager
- Active promotions list with performance metrics
- Historical promotion archive
- Manual override controls
- Promotion effectiveness leaderboard

### Approval Queue ✅ NEW
- Review pending agent-recommended promotions
- View detailed promotion parameters and reasoning
- Inspect market data used in decision-making
- Approve promotions to activate them
- Reject promotions with notes for agent learning
- Filter by status (pending/approved/rejected)
- Track approval statistics and rates

### Token & Cost Tracker
- Live cost accumulation (hourly/daily/monthly)
- Cost per agent breakdown
- Cost per SKU analysis
- Cost per promotion ROI
- Budget burn rate projections
- Export cost reports

### Simulator Control Panel
- **Weather Tab**: View/modify weather conditions per location
- **Competitor Tab**: Trigger competitor promotions, adjust strategies
- **Social Trends Tab**: Inject events, view trending topics
- Reset all simulators to defaults

### Analytics
- Performance correlation with external factors
- Agent decision audit log with explanations
- Sell-through rate analysis
- Margin safety tracking
- A/B testing results (when available)

## 🔧 Configuration

### Agent Behavior

Edit `langgraph/config.py` to adjust:

```python
AGENT_CONFIG = {
    "monitoring_interval_minutes": 30,  # How often agents check each SKU
    "min_margin_percent": 10,           # Hard floor for profitability
    "max_discount_percent": 40,         # Maximum allowed discount
    "auto_retract_threshold": 0.5,      # Retract if performance < 50% expected
    "require_manual_approval": False,   # Set True to enable manual approval workflow
}
```

**Manual Approval Workflow**: When `require_manual_approval` is set to `True`:
- Agents will create promotion recommendations and save them to `pending_promotions` table
- Promotions are NOT automatically activated
- Human reviewers must approve/reject via the Approval Queue UI
- Approved promotions are converted to active promotions
- Rejected promotions are logged with reviewer notes for agent learning

📘 **Full documentation**: See [docs/MANUAL_APPROVAL_WORKFLOW.md](docs/MANUAL_APPROVAL_WORKFLOW.md) for detailed workflow, database schema, MCP tools, and best practices.

### Simulator Settings

Edit respective `mcp-servers/*/config.py`:

- Weather: Base temperatures, variation ranges, extreme event probability
- Competitor: Strategy aggressiveness, response lag, sale frequency
- Social: Event density, trending topic generation rate, sentiment volatility

### Database Connection

If you need to connect external tools to Postgres:

```
Host: localhost
Port: 95432
Database: pricing_intelligence
User: pricing_user
Password: pricing_pass
```

## 📁 Project Structure

```
neuroshelf_v3/
├── docker-compose.yml           # Container orchestration
├── .env                         # API keys and secrets (create from .env.example)
├── .env.example                 # Template for environment variables
├── README.md                    # This file
│
├── db/
│   ├── init.sql                 # Database schema
│   └── seed.sql                 # Sample data (SKUs, stores, historical data)
│
├── mcp-servers/
│   ├── postgres/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py            # MCP server for database operations
│   │
│   ├── weather-simulator/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── server.py            # MCP server wrapper
│   │   ├── simulator.py         # Weather simulation engine
│   │   └── config.py            # Simulation parameters
│   │
│   ├── competitor-simulator/
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── server.py
│   │   ├── simulator.py         # Competitor behavior engine
│   │   └── config.py
│   │
│   └── social-simulator/
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── server.py
│       ├── simulator.py         # Social trends engine
│       └── config.py
│
├── langgraph/
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── main.py                  # Entry point, agent orchestration loop
│   ├── graph.py                 # LangGraph state graph definition
│   ├── config.py                # Agent configuration
│   ├── token_tracker.py         # Token usage and cost tracking
│   ├── mcp_client.py            # MCP client wrapper
│   │
│   └── agents/
│       ├── __init__.py
│       ├── data_collector.py    # Data Collection Agent
│       ├── market_analyzer.py   # Market Analysis Agent
│       ├── pricing_strategy.py  # Pricing Strategy Agent
│       ├── promo_designer.py    # Promotion Design Agent
│       ├── executor.py          # Execution & Deployment Agent
│       └── monitor.py           # Monitoring & Evaluation Agent
│
├── langgraph-studio/
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py                # Graph visualization server
│
└── streamlit/
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                   # Main Streamlit app
    │
    └── pages/
        ├── 1_dashboard.py       # Overview dashboard
        ├── 2_sku_monitor.py     # SKU detail view
        ├── 3_promo_manager.py   # Promotion management
        ├── 4_token_cost_tracker.py  # Cost tracking
        ├── 5_simulator_control.py   # Simulator controls
        ├── 6_analytics.py       # Analytics and reporting
        └── 7_approval_queue.py  # Manual approval interface
```

## 🔍 How It Works

### Agent Decision Cycle (Every 30 Minutes per SKU)

1. **Data Collection**
   - Query inventory levels via MCP Postgres
   - Calculate 7-day sell-through rate
   - Fetch current weather and forecast
   - Get competitor prices for this SKU
   - Check trending topics and upcoming events

2. **Market Analysis**
   - Identify demand patterns (growing/declining)
   - Correlate external factors (hot weather → ice cream demand)
   - Assess competitive positioning
   - Detect opportunities (excess inventory + demand spike)

3. **Decision Point**
   - Should we act? (If no opportunity, wait until next cycle)
   - If yes, proceed to strategy design

4. **Pricing Strategy**
   - Calculate optimal price point
   - Ensure margin constraints are met
   - Estimate demand elasticity
   - Risk assessment

5. **Promotion Design**
   - Define targeting: which store(s), which customers
   - Time window: 1-2 hour flash sale vs all-day offer
   - Delivery: push notification, in-app banner, email
   - Create promotion record

6. **Execution**
   - **Auto Mode** (`require_manual_approval=False`):
     - Write promotion to database immediately
     - Set valid_from, valid_until timestamps
     - Trigger downstream systems (simulated)
     - Log decision rationale to LangSmith
   - **Manual Approval Mode** (`require_manual_approval=True`):
     - Save promotion to `pending_promotions` table
     - Include all parameters, reasoning, and market data
     - Wait for human review in Approval Queue UI
     - Only activate upon explicit approval

7. **Monitoring**
   - Check sales velocity every 15 minutes
   - Compare actual vs expected performance
   - If margin drops below threshold → auto-retract
   - If successful → log to performance database for learning

### Example Scenario

**SKU**: ICECREAM-VANILLA-001
**Initial State**: 500 units at Store A, sell-through: 50 units/day (slow)
**External Factors**:
- Weather: 35°C heatwave forecasted tomorrow
- Competitor: Competitor A drops price to $3.99 (we're at $4.99)
- Social: Local music festival trending on social media

**Agent Decision**:
- Market Analyzer: "High demand opportunity, but price not competitive"
- Pricing Strategy: "Drop to $3.49, maintains 12% margin"
- Promo Designer: "2-hour flash sale tomorrow 12pm-2pm, Store A only, push notification to users within 5km radius"
- Executor: Creates promotion in database
- Monitor: Tracks performance, sees 3x sell-through rate, marks promotion as successful

**Outcome**: 300 units sold during promotion, excess inventory cleared, profitable margin maintained, learned that weather+events are strong predictors for ice cream.

## 🐛 Troubleshooting

### Containers won't start
```bash
# Check Docker resources (need 8GB+ RAM)
docker stats

# View container logs
docker-compose logs [container_name]

# Restart specific container
docker-compose restart [container_name]
```

### Database connection errors
```bash
# Check if Postgres is ready
docker-compose exec postgres pg_isready -U pricing_user

# Verify schema initialization
docker-compose exec postgres psql -U pricing_user -d pricing_intelligence -c "\dt"
```

### MCP servers not responding
```bash
# Check MCP server logs
docker-compose logs mcp-postgres
docker-compose logs mcp-weather

# Test MCP server health
curl http://localhost:3000/health
curl http://localhost:3001/health
```

### Agents not making decisions
- Check OpenAI API key is valid in `.env`
- Verify LangGraph logs: `docker-compose logs langgraph-core`
- Check token budget hasn't been exceeded
- Ensure seed data exists: `docker-compose exec postgres psql -U pricing_user -d pricing_intelligence -c "SELECT COUNT(*) FROM skus;"`

### Streamlit UI not loading
```bash
# Restart Streamlit
docker-compose restart streamlit

# Check logs
docker-compose logs streamlit
```

## 📈 Performance Optimization

### Reduce Token Costs
- Increase `monitoring_interval_minutes` to check less frequently
- Reduce number of seeded SKUs in `db/seed.sql`
- Enable manual approval mode to prevent auto-execution

### Speed Up Decisions
- Decrease LLM temperature in `langgraph/config.py`
- Use smaller context windows
- Cache external factor data (already implemented)

### Scale to More SKUs
- Currently optimized for 10-50 SKUs
- For 100+ SKUs, implement parallel agent execution
- Consider batching SKU analysis

## 🔐 Security Notes

- `.env` file contains secrets - DO NOT commit to version control
- Default Postgres password should be changed in production
- MCP servers have no authentication - only for local development
- Streamlit has no login - add authentication for production use

## 📚 Technologies Used

- **LangGraph** - Agent orchestration and state management
- **LangSmith** - LLM observability and tracing
- **OpenAI GPT-5-mini** - Language model for agent reasoning
- **MCP (Model Context Protocol)** - Standardized tool calling interface
- **PostgreSQL** - Relational database
- **Streamlit** - Python web UI framework
- **Docker** - Containerization
- **Python 3.11** - Core programming language

## 🤝 Contributing

This is a standalone project not connected to version control. To make changes:

1. Edit files directly in the project directory
2. Rebuild affected containers: `docker-compose up --build [service_name]`
3. Test changes locally before deploying

## 📝 License

Proprietary - Internal use only

## 📞 Support

For issues or questions:
1. Check logs: `docker-compose logs [container_name]`
2. Review this README troubleshooting section
3. Inspect LangSmith traces for agent decision debugging
4. Check Streamlit Token Cost Tracker for budget issues

## 🎯 Roadmap

Future enhancements:
- [ ] Multi-SKU batch analysis for efficiency
- [ ] A/B testing framework for promotion strategies
- [ ] Customer segment targeting (loyalty tier, purchase history)
- [ ] Integration with real POS systems
- [ ] Mobile app for promotion alerts
- [ ] Machine learning for demand forecasting
- [ ] Automated margin optimization
- [ ] Multi-store promotion coordination

---

**Version**: 1.0.0
**Last Updated**: 2025-12-11
**Status**: Production Ready
