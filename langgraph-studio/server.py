"""
LangGraph Studio Visualization Server
Provides graph visualization and execution monitoring
"""

import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn
import httpx

app = FastAPI(title="LangGraph Studio", version="1.0.0")

LANGGRAPH_CORE_URL = os.getenv("LANGGRAPH_CORE_URL", "http://langgraph-core:8000")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Serve visualization dashboard"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LangGraph Studio - Pricing Intelligence Agent</title>
        <style>
            body {
                font-family: Arial, sans-serif;
                margin: 0;
                padding: 20px;
                background: #f5f5f5;
            }
            .container {
                max-width: 1200px;
                margin: 0 auto;
                background: white;
                padding: 30px;
                border-radius: 8px;
                box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            }
            h1 {
                color: #333;
                border-bottom: 3px solid #4CAF50;
                padding-bottom: 10px;
            }
            .graph-container {
                margin: 30px 0;
                padding: 20px;
                background: #fafafa;
                border-radius: 5px;
            }
            .node {
                display: inline-block;
                padding: 15px 25px;
                margin: 10px;
                background: #4CAF50;
                color: white;
                border-radius: 5px;
                font-weight: bold;
            }
            .arrow {
                display: inline-block;
                margin: 0 10px;
                font-size: 24px;
            }
            .status {
                padding: 15px;
                margin: 20px 0;
                background: #e3f2fd;
                border-left: 4px solid #2196F3;
                border-radius: 3px;
            }
            .info {
                margin: 10px 0;
                font-size: 14px;
            }
            .label {
                font-weight: bold;
                color: #555;
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🤖 LangGraph Studio - Pricing Intelligence Agent</h1>

            <div class="status">
                <h2>Agent Status</h2>
                <div class="info"><span class="label">Status:</span> <span id="status">Loading...</span></div>
                <div class="info"><span class="label">Last Run:</span> <span id="lastRun">-</span></div>
                <div class="info"><span class="label">Cycles Completed:</span> <span id="cycles">-</span></div>
            </div>

            <h2>Agent Workflow Graph</h2>
            <div class="graph-container">
                <div style="text-align: center;">
                    <div style="margin: 20px 0;">
                        <div class="node">START</div>
                    </div>
                    <div class="arrow">↓</div>
                    <div style="margin: 20px 0;">
                        <div class="node">Data Collection Agent</div>
                    </div>
                    <div class="arrow">↓</div>
                    <div style="margin: 20px 0;">
                        <div class="node">Market Analysis Agent</div>
                    </div>
                    <div class="arrow">↓</div>
                    <div style="margin: 20px 0; font-size: 18px; color: #ff9800;">
                        <strong>Should Act?</strong>
                    </div>
                    <div style="margin: 20px;">
                        <div style="display: inline-block; width: 40%; vertical-align: top;">
                            <div style="color: #f44336;">← No</div>
                            <div class="arrow">↓</div>
                            <div class="node" style="background: #9e9e9e;">END (No Action)</div>
                        </div>
                        <div style="display: inline-block; width: 40%; vertical-align: top;">
                            <div style="color: #4CAF50;">Yes →</div>
                            <div class="arrow">↓</div>
                            <div class="node">Pricing Strategy Agent</div>
                            <div class="arrow">↓</div>
                            <div class="node">Promotion Design Agent</div>
                            <div class="arrow">↓</div>
                            <div class="node">Execution Agent</div>
                            <div class="arrow">↓</div>
                            <div class="node" style="background: #2196F3;">END (Promotion Created)</div>
                        </div>
                    </div>
                </div>
            </div>

            <h2>Monitoring Workflow</h2>
            <div class="graph-container">
                <div style="text-align: center;">
                    <div style="margin: 20px 0;">
                        <div class="node" style="background: #ff9800;">Monitor Active Promotions</div>
                    </div>
                    <div class="arrow">↓</div>
                    <div style="margin: 20px 0; font-size: 18px; color: #ff9800;">
                        <strong>Should Retract?</strong>
                    </div>
                    <div style="margin: 20px;">
                        <div style="display: inline-block; width: 40%; vertical-align: top;">
                            <div style="color: #4CAF50;">← No</div>
                            <div class="arrow">↓</div>
                            <div class="node" style="background: #4CAF50;">Continue Monitoring</div>
                        </div>
                        <div style="display: inline-block; width: 40%; vertical-align: top;">
                            <div style="color: #f44336;">Yes →</div>
                            <div class="arrow">↓</div>
                            <div class="node" style="background: #f44336;">Retract Promotion</div>
                        </div>
                    </div>
                </div>
            </div>

            <div style="margin-top: 30px; padding: 15px; background: #fff3cd; border-left: 4px solid #ffc107; border-radius: 3px;">
                <strong>ℹ️ Info:</strong> This visualization shows the autonomous agent workflow.
                The agent runs every 30 minutes (configurable), analyzing SKUs and creating/retracting promotions automatically.
            </div>
        </div>

        <script>
            async function updateStatus() {
                try {
                    const response = await fetch('http://localhost:8000/status');
                    const data = await response.json();

                    document.getElementById('status').textContent = data.agent_running ? '🟢 Running' : '🔴 Stopped';
                    document.getElementById('lastRun').textContent = data.last_run || 'Never';
                    document.getElementById('cycles').textContent = data.cycles_completed || 0;
                } catch (error) {
                    document.getElementById('status').textContent = '🟡 Unknown';
                }
            }

            // Update status every 5 seconds
            updateStatus();
            setInterval(updateStatus, 5000);
        </script>
    </body>
    </html>
    """


@app.get("/health")
def health_check():
    """Health check"""
    return {"status": "healthy", "service": "langgraph-studio"}


if __name__ == "__main__":
    print("Starting LangGraph Studio...")
    print(f"LangGraph Core URL: {LANGGRAPH_CORE_URL}")
    uvicorn.run(app, host="0.0.0.0", port=8080)
