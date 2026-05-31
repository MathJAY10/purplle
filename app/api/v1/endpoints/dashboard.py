from __future__ import annotations

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter()


@router.get("/dashboard", response_class=HTMLResponse)
async def dashboard() -> HTMLResponse:
    return HTMLResponse(
        content="""
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Store Intelligence Dashboard</title>
  <style>
    body { margin: 0; font-family: Inter, Arial, sans-serif; background: #0f172a; color: #e2e8f0; }
    .shell { max-width: 1100px; margin: 0 auto; padding: 32px; }
    .hero { display: flex; justify-content: space-between; align-items: flex-end; gap: 16px; margin-bottom: 24px; }
    .card { background: #111827; border: 1px solid #1f2937; border-radius: 16px; padding: 20px; box-shadow: 0 10px 30px rgba(0,0,0,.2); }
    .grid { display: grid; grid-template-columns: repeat(4, minmax(0,1fr)); gap: 16px; }
    .kpi { font-size: 36px; font-weight: 700; margin: 8px 0 0; }
    .label { color: #94a3b8; text-transform: uppercase; letter-spacing: .08em; font-size: 12px; }
    .muted { color: #94a3b8; }
    input, button { border-radius: 10px; border: 1px solid #334155; background: #0f172a; color: #e2e8f0; padding: 10px 14px; }
    button { background: #2563eb; border-color: #2563eb; cursor: pointer; }
    ul { padding-left: 18px; }
    .section { margin-top: 18px; }
    @media (max-width: 900px) { .grid { grid-template-columns: 1fr 1fr; } .hero { flex-direction: column; align-items: stretch; } }
    @media (max-width: 640px) { .grid { grid-template-columns: 1fr; } }
  </style>
</head>
<body>
  <div class="shell">
    <div class="hero">
      <div>
        <div class="label">Store Intelligence System</div>
        <h1 style="margin:8px 0 0">Demo Dashboard</h1>
        <div class="muted">Visitor count, conversion, queue depth, and anomaly status.</div>
      </div>
      <div style="display:flex; gap:10px; align-items:center; flex-wrap:wrap;">
        <input id="storeId" value="default-store" aria-label="Store ID" />
        <button onclick="refreshDashboard()">Refresh</button>
      </div>
    </div>

    <div class="grid">
      <div class="card"><div class="label">Visitor Count</div><div class="kpi" id="visitors">-</div></div>
      <div class="card"><div class="label">Conversion Rate</div><div class="kpi" id="conversion">-</div></div>
      <div class="card"><div class="label">Queue Depth</div><div class="kpi" id="queue">-</div></div>
      <div class="card"><div class="label">Stale Feed</div><div class="kpi" id="stale">-</div></div>
    </div>

    <div class="section card">
      <div class="label">Anomaly List</div>
      <ul id="anomalies"><li class="muted">No data loaded yet.</li></ul>
    </div>
  </div>

  <script>
    async function refreshDashboard() {
      const storeId = document.getElementById('storeId').value || 'default-store';
      const [metricsResponse, anomaliesResponse, healthResponse] = await Promise.all([
        fetch(`/api/v1/stores/${storeId}/metrics`),
        fetch(`/api/v1/stores/${storeId}/anomalies`),
        fetch('/health')
      ]);
      const metrics = metricsResponse.ok ? await metricsResponse.json() : {};
      const anomalies = anomaliesResponse.ok ? await anomaliesResponse.json() : { anomalies: [] };
      const health = healthResponse.ok ? await healthResponse.json() : {};

      document.getElementById('visitors').textContent = metrics.unique_visitors ?? '-';
      document.getElementById('conversion').textContent = metrics.conversion_rate != null ? `${(metrics.conversion_rate * 100).toFixed(2)}%` : '-';
      document.getElementById('queue').textContent = metrics.queue_depth ?? '-';
      document.getElementById('stale').textContent = health.stale_feed ? 'Yes' : 'No';

      const list = document.getElementById('anomalies');
      list.innerHTML = '';
      if (!anomalies.anomalies || anomalies.anomalies.length === 0) {
        list.innerHTML = '<li class="muted">No anomalies detected.</li>';
        return;
      }
      anomalies.anomalies.forEach(item => {
        const li = document.createElement('li');
        li.textContent = `${item.anomaly_type} - ${item.severity}: ${item.description}`;
        list.appendChild(li);
      });
    }
    refreshDashboard();
  </script>
</body>
</html>
"""
    )