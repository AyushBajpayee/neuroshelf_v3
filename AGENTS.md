# AGENTS.md

## Purpose
Reference guide for coding agents working in this repository.

This project is an autonomous pricing intelligence system with:
- LangGraph-based decision agents
- MCP servers for database + simulated external factors
- PostgreSQL data layer
- Streamlit operations UI
- Optional manual approval workflow for promotions

## Source Of Truth
Use this order when information conflicts:
1. Runtime code (`docker-compose.yml`, Python services, SQL schema)
2. Database schema (`db/init.sql`)
3. Markdown docs (`README.md`, `STARTUP_GUIDE.md`, etc.)

When docs and code disagree, follow code and update docs.

## Architecture Snapshot
Docker services (8):
- `postgres` -> host port `65432` mapped to container `5432`
- `mcp-postgres` -> `3000`
- `mcp-weather` -> `3001`
- `mcp-competitor` -> `3002`
- `mcp-social` -> `3003`
- `langgraph-core` -> `8000`
- `langgraph-studio` -> `8080`
- `streamlit` -> `8501`

Key note: several docs still mention Postgres on host `5432`; current compose maps to `65432`.

## Startup And Dev Commands
- `cp .env.example .env`
- `docker-compose up --build`
- `docker-compose ps`
- `docker-compose logs -f langgraph-core`
- `docker-compose restart <service>`
- `docker-compose down`
- `docker-compose down -v` (destructive: removes DB volume)

## Key Configuration
Environment variables are defined in `.env.example`.

Important toggles:
- `AGENT_AUTO_START` (`true`/`false`) controls whether agent processing starts automatically on container boot
- `AGENT_REQUIRE_MANUAL_APPROVAL` (`true`/`false`)
- `AGENT_MONITORING_INTERVAL_MINUTES`
- `AGENT_MIN_MARGIN_PERCENT`
- `AGENT_MAX_DISCOUNT_PERCENT`
- `AGENT_AUTO_RETRACT_THRESHOLD`

Model caveat:
- `.env.example` sets `OPENAI_MODEL=gpt-5-mini`
- `docker-compose.yml` fallback for `langgraph-core` is `gpt-4o-mini` if unset
- Set `OPENAI_MODEL` explicitly in `.env` to avoid ambiguity

## Code Map
- `db/init.sql`: full schema, views, triggers, approval tables
- `db/seed.sql`: demo stores/SKUs/inventory/sales seed
- `mcp-servers/postgres/server.py`: DB tool API (including approval tools)
- `mcp-servers/weather-simulator/*`: weather simulation + DB writes
- `mcp-servers/competitor-simulator/*`: competitor pricing simulation
- `mcp-servers/social-simulator/*`: trends/events simulation + DB writes
- `langgraph/graph.py`: pricing + monitoring graphs
- `langgraph/main.py`: FastAPI endpoints + background worker + pause/resume cursor
- `langgraph/runtime_tracker.py`: thread-safe live runtime context (current agent/sku/store)
- `langgraph/agents/*.py`: agent nodes (collect/analyze/price/design/execute/monitor)
- `streamlit/app.py` and `streamlit/pages/*`: UI and approval queue
- `docs/MANUAL_APPROVAL_WORKFLOW.md`: human-in-the-loop workflow details

## Runtime Behavior Notes
- Pricing graph flow:
  `collect_data -> analyze_market -> (act?) -> design_pricing -> design_promotion -> execute_promotion`
- Monitoring graph flow:
  `monitor -> (retract?) -> retract`
- Manual approval mode routes promotions to `pending_promotions`; approvals create active records in `promotions`.
- Agent target scan order defaults to stores `[1..5]` x SKUs `[1..20]` (overridable via `SKUS_CONSIDERED` and `STORES_CONSIDERED`).
- `langgraph/main.py` no longer hard-starts processing on startup; it starts paused unless `AGENT_AUTO_START=true`.
- Agent processing is pause/resume capable and resumes from `next_target_index` in the current cycle.
- Blocking graph calls run through `asyncio.to_thread(...)` in the loop so `/status` and control APIs stay responsive while agents run.

## Agent Control APIs
- `POST /agent/start`: start or resume loop from current cursor
- `POST /agent/stop`: pause loop without resetting cursor
- `GET /status`: includes runtime metadata:
  - `in_progress_target`
  - `current_agent`
  - `current_sku_id`
  - `current_store_id`
  - `current_agent_updated_at`

## Streamlit Control Panel
- Sidebar Agent Control in `streamlit/app.py` supports:
  - Start/Stop buttons (calls `/agent/start` and `/agent/stop`)
  - cycle progress and completed cycles
  - next target
  - in-progress SKU/store and current agent name
- `streamlit/pages/*.py` no longer call `st.set_page_config(...)`; page config is set only once in `streamlit/app.py` to avoid multipage import conflicts.

## Recent Implementation Notes
- New file: `langgraph/runtime_tracker.py`.
- Agent nodes now set live agent context:
  - `Data Collection Agent`
  - `Market Analysis Agent`
  - `Pricing Strategy Agent`
  - `Promotion Design Agent`
  - `Execution Agent`
  - `Monitoring Agent` / `Monitoring Agent (Retraction)`

## MCP Tool Surface (High Level)
- Postgres MCP: inventory, sell-through, promotion CRUD, token logs, decision logs, pending approval tools
- Weather MCP: current weather, forecast, scenario override
- Competitor MCP: current prices, history, trigger/end promo, strategy updates
- Social MCP: trends, event calendar, sentiment, viral injection

## Data Layer Highlights
Core tables:
- `stores`, `skus`, `inventory`, `sales_transactions`
- `promotions`, `promotion_performance`, `pending_promotions`
- `competitor_prices`, `external_factors`
- `token_usage`, `agent_decisions`, `simulator_state`

Useful views:
- `v_inventory_status`
- `v_active_promotions`
- `v_sell_through_rate`
- `v_cost_by_agent`
- `v_pending_promotions`

## Agent Editing Guidelines
- Preserve both execution modes: auto-execute and manual-approval.
- If you change schema/tool contracts, update:
  - MCP server handlers
  - LangGraph call sites
  - Streamlit pages
  - relevant `.md` docs
- Avoid introducing hard-coded host ports outside `docker-compose.yml` contracts.
- Do not commit secrets from `.env`.
