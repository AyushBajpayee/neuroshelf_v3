"""
LangGraph Studio Visualization Server
Provides graph visualization and execution monitoring
"""

import os

import httpx
import uvicorn
from fastapi import FastAPI
from fastapi.responses import HTMLResponse

app = FastAPI(title="LangGraph Studio", version="1.0.0")

LANGGRAPH_CORE_URL = os.getenv("LANGGRAPH_CORE_URL", "http://langgraph-core:8000")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve visualization dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>LangGraph Studio - Pricing Intelligence Agent</title>
        <style>
            @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&display=swap');

            :root {
                --bg-1: #f6f9f2;
                --bg-2: #edf4ff;
                --panel: rgba(255, 255, 255, 0.88);
                --text-main: #142133;
                --text-muted: #5a6b82;
                --stroke: #d9e4ef;
                --ok: #1f8a4c;
                --warn: #b45309;
                --bad: #b91c1c;
                --accent: #0d9488;
                --accent-2: #0f766e;
                --disabled: #94a3b8;
                --shadow-lg: 0 18px 40px rgba(15, 23, 42, 0.12);
                --shadow-sm: 0 6px 18px rgba(15, 23, 42, 0.08);
            }

            * { box-sizing: border-box; }

            body {
                margin: 0;
                min-height: 100vh;
                font-family: "Space Grotesk", "Avenir Next", "Trebuchet MS", sans-serif;
                color: var(--text-main);
                background:
                    radial-gradient(1300px 520px at 0% -10%, #d8f7ec 0%, transparent 55%),
                    radial-gradient(1000px 420px at 100% 0%, #dbe8ff 0%, transparent 48%),
                    linear-gradient(180deg, var(--bg-1), var(--bg-2));
                padding: 20px;
            }

            .shell {
                max-width: 1340px;
                margin: 0 auto;
                background: var(--panel);
                backdrop-filter: blur(6px);
                border: 1px solid rgba(255, 255, 255, 0.72);
                border-radius: 18px;
                box-shadow: var(--shadow-lg);
                overflow: hidden;
            }

            .hero {
                padding: 22px 24px;
                background: linear-gradient(90deg, #0f172a 0%, #134e4a 58%, #0f172a 100%);
                color: #eff6ff;
                position: relative;
                overflow: hidden;
            }

            .hero::after {
                content: "";
                position: absolute;
                right: -80px;
                top: -120px;
                width: 280px;
                height: 280px;
                border-radius: 50%;
                background: radial-gradient(circle, rgba(56, 189, 158, 0.42) 0%, rgba(56, 189, 158, 0) 68%);
                pointer-events: none;
            }

            .hero-row {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                justify-content: space-between;
                gap: 12px;
                position: relative;
                z-index: 1;
            }

            .title {
                margin: 0;
                font-size: 27px;
                line-height: 1.15;
                letter-spacing: 0.2px;
            }

            .subtitle {
                margin: 8px 0 0 0;
                color: rgba(226, 232, 240, 0.96);
                font-size: 14px;
            }

            .live-pill {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                border-radius: 999px;
                padding: 7px 14px;
                border: 1px solid rgba(190, 242, 230, 0.5);
                color: #d1fae5;
                background: rgba(20, 83, 74, 0.56);
                font-size: 12px;
                font-weight: 600;
            }

            .live-dot {
                width: 8px;
                height: 8px;
                border-radius: 50%;
                background: #34d399;
                box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.7);
                animation: pulse 1.6s infinite;
            }

            @keyframes pulse {
                0% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0.62); }
                70% { box-shadow: 0 0 0 10px rgba(52, 211, 153, 0); }
                100% { box-shadow: 0 0 0 0 rgba(52, 211, 153, 0); }
            }

            .content {
                padding: 20px 22px 24px 22px;
            }

            .section-title {
                margin: 18px 2px 10px 2px;
                font-size: 16px;
                color: #0f172a;
                letter-spacing: 0.3px;
            }

            .metric-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
                gap: 10px;
            }

            .metric {
                background: #fbfdff;
                border: 1px solid var(--stroke);
                border-radius: 12px;
                padding: 11px 12px;
                box-shadow: var(--shadow-sm);
                transition: transform 0.2s ease, box-shadow 0.2s ease;
            }

            .metric:hover {
                transform: translateY(-1px);
                box-shadow: 0 10px 22px rgba(15, 23, 42, 0.11);
            }

            .metric .k {
                font-size: 11px;
                color: var(--text-muted);
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.5px;
            }

            .metric .v {
                margin-top: 6px;
                font-size: 14px;
                font-weight: 700;
                color: var(--text-main);
            }

            .v.ok { color: var(--ok); }
            .v.bad { color: var(--bad); }

            .flag-wrap {
                background: #f8fbff;
                border: 1px solid var(--stroke);
                border-radius: 12px;
                padding: 12px;
            }

            .flag-row {
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .flag {
                display: inline-flex;
                align-items: center;
                gap: 8px;
                padding: 6px 12px;
                font-size: 12px;
                border-radius: 999px;
                border: 1px solid #cbd5e1;
                background: #ffffff;
                color: #0f172a;
                font-weight: 600;
            }

            .flag.on {
                background: #dcfce7;
                border-color: #86efac;
                color: #166534;
            }

            .flag.off {
                background: #f1f5f9;
                border-color: #cbd5e1;
                color: #64748b;
            }

            .workflow-shell {
                background: #f8fbff;
                border: 1px solid var(--stroke);
                border-radius: 14px;
                padding: 14px;
                overflow: hidden;
            }

            .flow-title {
                margin: 2px 2px 10px 2px;
                font-size: 13px;
                color: #475569;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.45px;
            }

            .flow-track {
                display: flex;
                flex-wrap: wrap;
                align-items: center;
                gap: 8px;
            }

            .stage {
                min-width: 130px;
                padding: 9px 10px;
                border-radius: 10px;
                border: 1px solid #cbd5e1;
                background: #ffffff;
                box-shadow: var(--shadow-sm);
                transition: all 0.25s ease;
            }

            .stage .name {
                font-size: 12px;
                font-weight: 700;
                color: #0f172a;
            }

            .stage .state {
                margin-top: 4px;
                font-size: 11px;
                color: #6b7280;
                font-weight: 600;
                text-transform: uppercase;
                letter-spacing: 0.35px;
            }

            .stage.pending { opacity: 0.9; }
            .stage.complete {
                background: #e8f9ef;
                border-color: #86efac;
            }
            .stage.complete .state { color: #166534; }

            .stage.active {
                border-color: #2dd4bf;
                background: linear-gradient(180deg, #ecfeff 0%, #d1fae5 100%);
                box-shadow: 0 0 0 2px rgba(45, 212, 191, 0.2), 0 12px 24px rgba(15, 23, 42, 0.12);
                animation: bob 1.4s ease-in-out infinite;
            }

            .stage.active .state { color: #0f766e; }

            .stage.disabled {
                background: #e2e8f0;
                border-color: #cbd5e1;
                opacity: 0.75;
            }
            .stage.disabled .name,
            .stage.disabled .state {
                color: var(--disabled);
            }

            .stage.reject {
                background: #fee2e2;
                border-color: #fecaca;
            }
            .stage.reject .name,
            .stage.reject .state {
                color: #991b1b;
            }

            @keyframes bob {
                0% { transform: translateY(0px); }
                50% { transform: translateY(-2px); }
                100% { transform: translateY(0px); }
            }

            .arrow {
                color: #64748b;
                font-weight: 700;
                font-size: 13px;
                padding: 0 2px;
            }

            .hint {
                margin-top: 12px;
                border: 1px solid #fde68a;
                background: #fffbeb;
                border-radius: 10px;
                padding: 10px 12px;
                font-size: 12px;
                color: #92400e;
                line-height: 1.45;
            }

            .err {
                border-color: #fecaca;
                background: #fff1f2;
                color: #9f1239;
            }

            @media (max-width: 760px) {
                body { padding: 10px; }
                .hero { padding: 16px; }
                .content { padding: 12px; }
                .stage { min-width: 112px; }
            }
        </style>
    </head>
    <body>
        <div class="shell">
            <div class="hero">
                <div class="hero-row">
                    <div>
                        <h1 class="title">LangGraph Studio</h1>
                        <div class="subtitle">Live workflow map for pricing intelligence orchestration</div>
                    </div>
                    <div class="live-pill">
                        <span class="live-dot"></span>
                        <span id="liveText">Auto-refresh every 4s</span>
                    </div>
                </div>
            </div>

            <div class="content">
                <div class="section-title">Runtime Status</div>
                <div class="metric-grid">
                    <div class="metric"><div class="k">Loop State</div><div id="status" class="v">Loading...</div></div>
                    <div class="metric"><div class="k">Worker Task</div><div id="workerRunning" class="v">-</div></div>
                    <div class="metric"><div class="k">Completed Cycles</div><div id="cycles" class="v">-</div></div>
                    <div class="metric"><div class="k">Last Run</div><div id="lastRun" class="v">-</div></div>
                    <div class="metric"><div class="k">Current Agent Node</div><div id="currentAgent" class="v">-</div></div>
                    <div class="metric"><div class="k">Current Target</div><div id="currentTarget" class="v">-</div></div>
                    <div class="metric"><div class="k">Next Target</div><div id="nextTarget" class="v">-</div></div>
                    <div class="metric"><div class="k">Last Sync</div><div id="lastSync" class="v">-</div></div>
                </div>

                <div class="section-title">Feature Flags</div>
                <div class="flag-wrap">
                    <div class="flag-row" id="featureFlags"></div>
                </div>

                <div class="section-title">Pricing Workflow</div>
                <div class="workflow-shell">
                    <div class="flow-title">Execution lane</div>
                    <div class="flow-track" id="pricingFlow"></div>
                    <div class="flow-title" style="margin-top: 14px;">Critic rejection branch</div>
                    <div class="flow-track" id="rejectFlow"></div>
                    <div class="hint" id="ragHint"></div>
                </div>

                <div class="section-title">Monitoring Workflow</div>
                <div class="workflow-shell">
                    <div class="flow-track" id="monitorFlow"></div>
                </div>

                <div class="hint" id="connectionHint">
                    Status is streamed from <code>/api/status</code> via LangGraph Core.
                </div>
            </div>
        </div>

        <script>
            const REFRESH_MS = 4000;
            const PRICING_STAGES = [
                { key: 'start', name: 'START', aliases: [] },
                { key: 'collect_data', name: 'Data Collection', aliases: ['Data Collection Agent'] },
                { key: 'analyze_market', name: 'Market Analysis', aliases: ['Market Analysis Agent'] },
                { key: 'should_act', name: 'Should Act?', aliases: [] },
                { key: 'load_decision_priors', name: 'Decision Learning', aliases: ['Decision Learning Agent'], optionalFlag: 'enable_decision_learning' },
                { key: 'design_pricing', name: 'Pricing Strategy', aliases: ['Pricing Strategy Agent'] },
                { key: 'design_promotion', name: 'Promotion Design', aliases: ['Promotion Design Agent'] },
                { key: 'optimize_offer', name: 'Offer Optimization', aliases: ['Offer Optimization Agent'], optionalFlag: 'enable_optimization_loop' },
                { key: 'multi_critic_review', name: 'Multi-Critic Review', aliases: ['Multi-Critic Review Agent'], optionalFlag: 'enable_multi_critic' },
                { key: 'execute_promotion', name: 'Execution', aliases: ['Execution Agent'] },
                { key: 'end', name: 'END', aliases: [] }
            ];

            const MONITOR_STAGES = [
                { key: 'monitor', name: 'Monitor', aliases: ['Monitoring Graph', 'Monitoring Agent'] },
                { key: 'should_retract', name: 'Should Retract?', aliases: [] },
                { key: 'retract', name: 'Retract', aliases: ['Monitoring Agent (Retraction)'] },
                { key: 'end', name: 'END', aliases: [] }
            ];

            function setText(id, value) {
                const element = document.getElementById(id);
                if (element) {
                    element.textContent = value;
                }
            }

            function formatIso(isoValue) {
                if (!isoValue) {
                    return '-';
                }
                try {
                    const dt = new Date(isoValue);
                    if (Number.isNaN(dt.getTime())) {
                        return isoValue;
                    }
                    return dt.toLocaleString();
                } catch (_) {
                    return isoValue;
                }
            }

            function normalizeCurrentStage(agentName) {
                if (!agentName) {
                    return null;
                }

                for (const stage of PRICING_STAGES) {
                    if (stage.aliases.includes(agentName)) {
                        return stage.key;
                    }
                }

                for (const stage of MONITOR_STAGES) {
                    if (stage.aliases.includes(agentName)) {
                        return stage.key;
                    }
                }

                return null;
            }

            function appendArrow(parent) {
                const arrow = document.createElement('span');
                arrow.className = 'arrow';
                arrow.textContent = '->';
                parent.appendChild(arrow);
            }

            function appendStage(parent, stageName, stateClass, stateText) {
                const card = document.createElement('div');
                card.className = 'stage ' + stateClass;

                const name = document.createElement('div');
                name.className = 'name';
                name.textContent = stageName;

                const state = document.createElement('div');
                state.className = 'state';
                state.textContent = stateText;

                card.appendChild(name);
                card.appendChild(state);
                parent.appendChild(card);
            }

            function renderFeatureFlags(flags) {
                const container = document.getElementById('featureFlags');
                container.innerHTML = '';

                const defs = [
                    ['enable_decision_learning', 'Decision Learning'],
                    ['enable_optimization_loop', 'Optimization Loop'],
                    ['enable_multi_critic', 'Multi-Critic'],
                    ['enable_approval_learning', 'Approval Learning'],
                    ['enable_rag_similarity', 'RAG Similarity']
                ];

                for (const [key, label] of defs) {
                    const enabled = Boolean(flags[key]);
                    const chip = document.createElement('span');
                    chip.className = 'flag ' + (enabled ? 'on' : 'off');
                    chip.textContent = label + ': ' + (enabled ? 'ON' : 'OFF');
                    container.appendChild(chip);
                }
            }

            function renderPricingWorkflow(flags, currentStage) {
                const flow = document.getElementById('pricingFlow');
                const rejectFlow = document.getElementById('rejectFlow');
                const ragHint = document.getElementById('ragHint');
                flow.innerHTML = '';
                rejectFlow.innerHTML = '';

                const visibleStages = PRICING_STAGES.map((stage) => {
                    if (!stage.optionalFlag) {
                        return { ...stage, enabled: true };
                    }
                    const enabled = Boolean(flags[stage.optionalFlag]);
                    return { ...stage, enabled };
                });

                const currentIndex = visibleStages.findIndex((stage) => stage.key === currentStage);

                visibleStages.forEach((stage, index) => {
                    if (index > 0) {
                        appendArrow(flow);
                    }

                    const isDisabled = stage.optionalFlag && !stage.enabled;
                    const isActive = stage.key === currentStage;

                    let stateClass = 'pending';
                    let stateText = 'Pending';

                    if (isDisabled) {
                        stateClass = 'disabled';
                        stateText = 'Bypassed';
                    } else if (isActive) {
                        stateClass = 'active';
                        stateText = 'Active';
                    } else if (currentIndex > -1 && index < currentIndex) {
                        stateClass = 'complete';
                        stateText = 'Complete';
                    }

                    appendStage(flow, stage.name, stateClass, stateText);
                });

                if (flags.enable_multi_critic) {
                    appendStage(rejectFlow, 'Critic action: reject', 'reject', 'Branch');
                    appendArrow(rejectFlow);
                    appendStage(rejectFlow, 'END (Rejected)', 'reject', 'Terminal');
                } else {
                    appendStage(rejectFlow, 'Critic branch disabled', 'disabled', 'Inactive');
                }

                if (flags.enable_rag_similarity) {
                    ragHint.textContent = 'RAG is enabled. Data Collection first tries vector similarity retrieval and falls back to Postgres historical cases when vector service is unavailable.';
                } else {
                    ragHint.textContent = 'RAG is disabled. Data Collection runs without similarity augmentation.';
                }
            }

            function renderMonitoringWorkflow(currentStage) {
                const flow = document.getElementById('monitorFlow');
                flow.innerHTML = '';
                const currentIndex = MONITOR_STAGES.findIndex((stage) => stage.key === currentStage);

                MONITOR_STAGES.forEach((stage, index) => {
                    if (index > 0) {
                        appendArrow(flow);
                    }

                    let stateClass = 'pending';
                    let stateText = 'Pending';

                    if (stage.key === currentStage) {
                        stateClass = 'active';
                        stateText = 'Active';
                    } else if (currentIndex > -1 && index < currentIndex) {
                        stateClass = 'complete';
                        stateText = 'Complete';
                    }

                    appendStage(flow, stage.name, stateClass, stateText);
                });
            }

            async function updateStatus() {
                const syncTime = new Date();
                setText('lastSync', syncTime.toLocaleTimeString());

                try {
                    const response = await fetch('/api/status');
                    const data = await response.json();
                    const flags = data.feature_flags || {};

                    const running = (data.running !== undefined) ? data.running : Boolean(data.agent_running);
                    const workerRunning = Boolean(data.worker_running);

                    const statusEl = document.getElementById('status');
                    statusEl.className = 'v ' + (running ? 'ok' : 'bad');
                    statusEl.textContent = running ? 'Running' : 'Stopped';

                    const workerEl = document.getElementById('workerRunning');
                    workerEl.className = 'v ' + (workerRunning ? 'ok' : 'bad');
                    workerEl.textContent = workerRunning ? 'Active' : 'Idle';

                    setText('cycles', String(data.cycles_completed || 0));
                    setText('lastRun', formatIso(data.last_run));
                    setText('currentAgent', data.current_agent || '-');

                    const currentTargetData = data.current_target_effective
                        || ((data.current_sku_id && data.current_store_id)
                            ? { sku_id: data.current_sku_id, store_id: data.current_store_id }
                            : null);
                    const currentTargetText = currentTargetData
                        ? ('SKU ' + currentTargetData.sku_id + ' / Store ' + currentTargetData.store_id)
                        : '-';
                    setText('currentTarget', currentTargetText);

                    const hasNextAfterCurrent = Object.prototype.hasOwnProperty.call(
                        data,
                        'next_target_after_current'
                    );
                    const nextTargetData = (data.next_target_after_current !== undefined)
                        ? data.next_target_after_current
                        : data.next_target;
                    let nextTargetText = '-';
                    if (nextTargetData) {
                        nextTargetText = 'SKU ' + nextTargetData.sku_id + ' / Store ' + nextTargetData.store_id;
                    } else if (running && hasNextAfterCurrent) {
                        nextTargetText = 'None (end of cycle / monitoring)';
                    }
                    setText('nextTarget', nextTargetText);

                    const currentStage = normalizeCurrentStage(data.current_agent);
                    renderFeatureFlags(flags);
                    renderPricingWorkflow(flags, currentStage);
                    renderMonitoringWorkflow(currentStage);

                    const connectionHint = document.getElementById('connectionHint');
                    connectionHint.className = 'hint';
                    connectionHint.textContent = 'Status stream healthy. Last payload synced from LangGraph Core.';
                } catch (error) {
                    const statusEl = document.getElementById('status');
                    statusEl.className = 'v bad';
                    statusEl.textContent = 'Unavailable';

                    const connectionHint = document.getElementById('connectionHint');
                    connectionHint.className = 'hint err';
                    connectionHint.textContent = 'Could not fetch /api/status: ' + error.message;
                }
            }

            setText('liveText', 'Auto-refresh every ' + (REFRESH_MS / 1000) + 's');
            updateStatus();
            setInterval(updateStatus, REFRESH_MS);
        </script>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    """Health check."""
    return {"status": "healthy", "service": "langgraph-studio"}


@app.get("/api/status")
async def get_agent_status():
    """Proxy status request to langgraph-core."""
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"{LANGGRAPH_CORE_URL}/status", timeout=5.0)
            return response.json()
    except Exception as e:
        return {
            "running": False,
            "agent_running": False,
            "worker_running": False,
            "error": str(e),
            "feature_flags": {
                "enable_decision_learning": False,
                "enable_optimization_loop": False,
                "enable_multi_critic": False,
                "enable_approval_learning": False,
                "enable_rag_similarity": False,
            },
        }


if __name__ == "__main__":
    print("Starting LangGraph Studio...")
    print(f"LangGraph Core URL: {LANGGRAPH_CORE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
