# Project Structure Overview

## Complete File Tree

```
neuroshelf_v3/
│
├── 📄 README.md                        # Comprehensive documentation
├── 📄 STARTUP_GUIDE.md                 # Step-by-step startup instructions
├── 📄 QUICK_REFERENCE.md               # Command reference and tips
├── 📄 PROJECT_STRUCTURE.md             # This file
│
├── 🔧 docker-compose.yml               # Container orchestration (8 services)
├── 🔑 .env                             # Environment variables (API keys)
├── 🔑 .env.example                     # Environment template
├── 🚫 .gitignore                       # Git ignore rules
│
├── 🗄️ db/                              # Database Initialization
│   ├── init.sql                       # Schema (tables, indexes, views, functions)
│   └── seed.sql                       # Sample data (SKUs, stores, sales, etc.)
│
├── 🔌 mcp-servers/                    # Model Context Protocol Servers (4 independent services)
│   │
│   ├── postgres/                      # MCP Server: Database Operations
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   └── server.py                  # Tools: query_inventory, create_promotion, etc.
│   │
│   ├── weather-simulator/             # MCP Server: Weather Simulation
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── config.py                  # Season configs, weather patterns
│   │   ├── simulator.py               # Weather generation engine
│   │   └── server.py                  # Tools: get_weather, set_scenario, etc.
│   │
│   ├── competitor-simulator/          # MCP Server: Competitor Pricing
│   │   ├── Dockerfile
│   │   ├── requirements.txt
│   │   ├── config.py                  # Competitor strategies
│   │   ├── simulator.py               # Pricing behavior engine
│   │   └── server.py                  # Tools: get_prices, trigger_promo, etc.
│   │
│   └── social-simulator/              # MCP Server: Social Media Trends
│       ├── Dockerfile
│       ├── requirements.txt
│       ├── config.py                  # Trending topics, events
│       ├── simulator.py               # Trend generation engine
│       └── server.py                  # Tools: get_trending, inject_viral, etc.
│
├── 🤖 langgraph/                      # LangGraph Agent System
│   ├── Dockerfile
│   ├── requirements.txt
│   │
│   ├── main.py                        # Entry point, orchestration loop
│   ├── graph.py                       # LangGraph state graph definition
│   ├── config.py                      # Agent configuration
│   ├── mcp_client.py                  # MCP client wrapper
│   ├── token_tracker.py               # Token usage & cost tracking
│   │
│   └── agents/                        # Individual Agent Implementations
│       ├── __init__.py
│       ├── data_collector.py          # Collects data from all MCP servers
│       ├── market_analyzer.py         # Analyzes market conditions (uses LLM)
│       ├── pricing_strategy.py        # Calculates optimal prices (uses LLM)
│       ├── promo_designer.py          # Designs promotion details (uses LLM)
│       ├── executor.py                # Deploys promotions to database
│       └── monitor.py                 # Monitors performance, retracts if needed
│
├── 📊 langgraph-studio/               # LangGraph Visualization Server
│   ├── Dockerfile
│   ├── requirements.txt
│   └── server.py                      # Web-based graph visualization
│
└── 🎨 streamlit/                      # Streamlit UI Application
    ├── Dockerfile
    ├── requirements.txt
    ├── app.py                         # Main dashboard page
    │
    └── pages/                         # Multi-page application
        ├── 1_dashboard.py             # Analytics dashboard
        ├── 2_sku_monitor.py           # SKU detail view
        ├── 3_promo_manager.py         # Promotion management
        ├── 4_token_cost_tracker.py    # Cost tracking & analysis
        ├── 5_simulator_control.py     # Simulator control panel
        └── 6_analytics.py             # Agent decision logs & insights
```

## Container Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    Docker Compose Network                        │
│                  (pricing-network: bridge)                       │
└─────────────────────────────────────────────────────────────────┘
                                │
        ┌───────────────────────┼───────────────────────────┐
        │                       │                           │
┌───────▼────────┐  ┌──────────▼─────────┐  ┌─────────────▼──────┐
│   PostgreSQL   │  │  LangGraph Studio  │  │   Streamlit UI     │
│   Container    │  │     Container      │  │    Container       │
│                │  │                    │  │                    │
│  Port: 5432    │  │    Port: 8080      │  │   Port: 8501       │
│  Volume: pgdata│  │                    │  │                    │
└────────┬───────┘  └────────────────────┘  └──────────┬─────────┘
         │                                              │
         │          ┌────────────────────┐             │
         └──────────│  LangGraph Core    │─────────────┘
                    │    Container       │
                    │                    │
                    │   Port: 8000       │
                    │  (Agent System)    │
                    └──────────┬─────────┘
                               │
        ┌──────────────────────┼──────────────────────┐
        │                      │                      │
┌───────▼──────┐  ┌───────────▼────┐  ┌──────────────▼────┐
│ MCP Postgres │  │  MCP Weather   │  │  MCP Competitor   │
│  Container   │  │   Container    │  │    Container      │
│ Port: 3000   │  │  Port: 3001    │  │   Port: 3002      │
└──────────────┘  └────────────────┘  └───────────────────┘
                               │
                    ┌──────────▼─────────┐
                    │   MCP Social       │
                    │    Container       │
                    │   Port: 3003       │
                    └────────────────────┘
```

## Data Flow Diagram

```
┌─────────────┐
│   User UI   │  Streamlit Dashboard (Port 8501)
│  (Browser)  │  - View promotions
└──────┬──────┘  - Control simulators
       │         - Monitor costs
       │
       ▼
┌─────────────────────────────────────────────────────────┐
│                   Application Layer                      │
├─────────────────────────────────────────────────────────┤
│  LangGraph Core (Port 8000)                             │
│  ┌─────────────────────────────────────────────┐       │
│  │  Agent Orchestration Loop (Every 30 min)    │       │
│  │                                              │       │
│  │  1. Data Collection Agent                   │       │
│  │     ↓                                        │       │
│  │  2. Market Analysis Agent (LLM)             │       │
│  │     ↓                                        │       │
│  │  3. Should Act? ──No──> END                 │       │
│  │     │                                        │       │
│  │     Yes                                      │       │
│  │     ↓                                        │       │
│  │  4. Pricing Strategy Agent (LLM)            │       │
│  │     ↓                                        │       │
│  │  5. Promotion Design Agent (LLM)            │       │
│  │     ↓                                        │       │
│  │  6. Execution Agent                         │       │
│  │     ↓                                        │       │
│  │  7. Monitor Performance Agent               │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  Token Tracker: Logs all LLM calls with costs          │
└─────────────────────────────────────────────────────────┘
       │         │         │         │
       │         │         │         │
       ▼         ▼         ▼         ▼
┌─────────────────────────────────────────────────────────┐
│                MCP Server Layer                          │
├─────────────────────────────────────────────────────────┤
│  MCP Postgres     MCP Weather    MCP Competitor         │
│  (Port 3000)      (Port 3001)    (Port 3002)            │
│  - Inventory      - Current      - Competitor Prices    │
│  - Promotions     - Forecast     - Promo Triggers       │
│  - Token Logs     - Scenarios    - Strategies           │
│                                                          │
│  MCP Social (Port 3003)                                 │
│  - Trending Topics                                      │
│  - Events Calendar                                      │
│  - Viral Moments                                        │
└─────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────┐
│              Data Persistence Layer                      │
├─────────────────────────────────────────────────────────┤
│  PostgreSQL Database (Port 5432)                        │
│  ┌─────────────────────────────────────────────┐       │
│  │  Tables:                                     │       │
│  │  - skus, stores, inventory                  │       │
│  │  - sales_transactions                        │       │
│  │  - promotions, promotion_performance         │       │
│  │  - competitor_prices, external_factors       │       │
│  │  - token_usage, agent_decisions              │       │
│  │                                              │       │
│  │  Views:                                      │       │
│  │  - v_inventory_status                        │       │
│  │  - v_active_promotions                       │       │
│  │  - v_sell_through_rate                       │       │
│  │  - v_cost_by_agent                           │       │
│  │  - v_promotion_roi                           │       │
│  └─────────────────────────────────────────────┘       │
│                                                         │
│  Volume: pgdata (persists across restarts)             │
└─────────────────────────────────────────────────────────┘
```

## Technology Stack

### Backend
- **Python 3.11**: Core language
- **FastAPI**: REST APIs for all services
- **PostgreSQL 16**: Relational database
- **LangChain**: LLM framework
- **LangGraph**: Agent orchestration
- **OpenAI GPT-4o-mini**: Language model

### Frontend
- **Streamlit**: Python-based web UI
- **Plotly**: Interactive charts
- **Pandas**: Data manipulation

### Infrastructure
- **Docker & Docker Compose**: Containerization
- **httpx**: HTTP client for inter-service communication

### Observability
- **LangSmith**: LLM tracing and monitoring
- **Custom Token Tracking**: Cost analysis

## Key Files Explained

### Configuration Files

| File | Purpose |
|------|---------|
| `docker-compose.yml` | Defines all 8 containers, networks, volumes |
| `.env` | Environment variables (API keys, config) |
| `langgraph/config.py` | Agent behavior parameters |
| `mcp-servers/*/config.py` | Simulator configurations |

### Database Files

| File | Purpose |
|------|---------|
| `db/init.sql` | Database schema (15 tables, 6 views, functions) |
| `db/seed.sql` | Sample data (20 SKUs, 5 stores, historical sales) |

### Agent Implementation

| File | Purpose |
|------|---------|
| `langgraph/main.py` | Entry point, monitoring loop |
| `langgraph/graph.py` | LangGraph workflow definition |
| `langgraph/agents/*.py` | Individual agent logic |
| `langgraph/token_tracker.py` | Cost tracking for LLM calls |
| `langgraph/mcp_client.py` | MCP server communication |

### MCP Servers

| Server | File | Purpose |
|--------|------|---------|
| Postgres | `mcp-servers/postgres/server.py` | 15+ tools for DB operations |
| Weather | `mcp-servers/weather-simulator/server.py` | Weather data & scenario control |
| Competitor | `mcp-servers/competitor-simulator/server.py` | Competitor pricing simulation |
| Social | `mcp-servers/social-simulator/server.py` | Social trends & events |

### UI Pages

| Page | Purpose |
|------|---------|
| `streamlit/app.py` | Main dashboard |
| `pages/1_dashboard.py` | Analytics overview |
| `pages/2_sku_monitor.py` | SKU detail view |
| `pages/3_promo_manager.py` | Promotion CRUD |
| `pages/4_token_cost_tracker.py` | Cost analysis |
| `pages/5_simulator_control.py` | Simulator controls |
| `pages/6_analytics.py` | Agent decision logs |

## Agent Decision Flow

```
START
  │
  ▼
┌─────────────────────────────────────┐
│  1. DATA COLLECTION                 │
│  ─────────────────────────────────  │
│  - Query inventory (MCP Postgres)   │
│  - Get weather (MCP Weather)        │
│  - Get competitor prices (MCP Comp) │
│  - Get social trends (MCP Social)   │
│  - Calculate sell-through rate      │
└──────────────┬──────────────────────┘
               ▼
┌─────────────────────────────────────┐
│  2. MARKET ANALYSIS (LLM CALL)      │
│  ─────────────────────────────────  │
│  Analyzes:                          │
│  - Inventory status (excess?)       │
│  - Weather impact                   │
│  - Competitor positioning           │
│  - Social buzz                      │
│                                     │
│  Decision: Should Act? Yes/No       │
└──────────────┬──────────────────────┘
               ▼
        ┌──────┴──────┐
        │             │
       NO            YES
        │             │
        ▼             ▼
      END   ┌──────────────────────────┐
            │  3. PRICING STRATEGY     │
            │     (LLM CALL)           │
            │  ──────────────────────  │
            │  Calculates:             │
            │  - Optimal price         │
            │  - Maintains min margin  │
            │  - Competitive position  │
            └────────┬─────────────────┘
                     ▼
            ┌──────────────────────────┐
            │  4. PROMOTION DESIGN     │
            │     (LLM CALL)           │
            │  ──────────────────────  │
            │  Determines:             │
            │  - Promotion type        │
            │  - Duration              │
            │  - Targeting             │
            │  - Expected performance  │
            └────────┬─────────────────┘
                     ▼
            ┌──────────────────────────┐
            │  5. EXECUTION            │
            │  ──────────────────────  │
            │  - Create promotion in DB│
            │  - Log decision          │
            │  - Log token usage       │
            └────────┬─────────────────┘
                     ▼
                   END

Separate Monitoring Loop (every 15 min):
┌──────────────────────────────────────┐
│  6. MONITOR PERFORMANCE               │
│  ──────────────────────────────────  │
│  For each active promotion:          │
│  - Check actual vs expected sales    │
│  - Verify margin maintained          │
│  - Decide: Continue or Retract?      │
│                                      │
│  If underperforming:                 │
│    → Retract promotion               │
│    → Log decision                    │
└──────────────────────────────────────┘
```

## Token Tracking Flow

Every LLM call is automatically tracked:

```
LLM Call
   │
   ▼
Token Tracker extracts usage
   │
   ├─ prompt_tokens
   ├─ completion_tokens
   └─ calculates cost
   │
   ▼
Logs to database via MCP
   │
   ├─ agent_name
   ├─ operation
   ├─ total_tokens
   ├─ estimated_cost
   └─ context (sku_id, promotion_id)
   │
   ▼
Viewable in Streamlit
   │
   ├─ Cost by Agent
   ├─ Cost over Time
   └─ ROI Analysis
```

## Port Mapping Summary

| Port | Service | Purpose |
|------|---------|---------|
| 5432 | PostgreSQL | Database access |
| 3000 | MCP Postgres | Database operations API |
| 3001 | MCP Weather | Weather simulator API |
| 3002 | MCP Competitor | Competitor simulator API |
| 3003 | MCP Social | Social trends API |
| 8000 | LangGraph Core | Agent system API |
| 8080 | LangGraph Studio | Graph visualization web UI |
| 8501 | Streamlit | Main dashboard web UI |

## Volume Mapping

| Volume | Container | Path | Purpose |
|--------|-----------|------|---------|
| `pgdata` | postgres | `/var/lib/postgresql/data` | Database persistence |
| `./db/init.sql` | postgres | `/docker-entrypoint-initdb.d/01-init.sql` | Schema initialization |
| `./db/seed.sql` | postgres | `/docker-entrypoint-initdb.d/02-seed.sql` | Data seeding |

## Development Workflow

1. **Modify Code**: Edit files in your IDE
2. **Rebuild Container**: `docker-compose up --build [service]`
3. **View Logs**: `docker-compose logs -f [service]`
4. **Test Changes**: Use Streamlit UI or API endpoints
5. **Iterate**: Repeat as needed

## Production Considerations

This is a **demonstration/development system**. For production:

1. **Security**:
   - Change default passwords
   - Add authentication to APIs
   - Use secrets management
   - Enable SSL/TLS

2. **Scalability**:
   - Add load balancers
   - Scale LangGraph Core horizontally
   - Use managed database (RDS, Cloud SQL)
   - Implement caching (Redis)

3. **Monitoring**:
   - Add Prometheus/Grafana
   - Implement alerting
   - Use APM tools
   - Enhanced logging (ELK stack)

4. **Reliability**:
   - Add health checks
   - Implement retries
   - Database backups
   - Disaster recovery plan

---

**For questions or issues, refer to README.md or STARTUP_GUIDE.md**
