import sys
import json
import webbrowser
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

# Ensure project root is in sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.knowledge_graph import KnowledgeGraph
from src.history_manager import HistoryManager

PORT = 8000


HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>System-Wide AI Copilot - Knowledge Graph & History Dashboard</title>
    <script type="text/javascript" src="https://unpkg.com/vis-network/standalone/umd/vis-network.min.js"></script>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; font-family: 'Segoe UI', system-ui, -apple-system, sans-serif; }
        body { background-color: #0F0F17; color: #E2E8F0; display: flex; height: 100vh; overflow: hidden; }
        
        /* Sidebar */
        #sidebar { width: 340px; background: #181825; border-right: 1px solid #2A2B3D; display: flex; flex-direction: column; }
        .header { padding: 20px; border-bottom: 1px solid #2A2B3D; background: #1E1E2E; }
        .header h1 { font-size: 1.1rem; color: #CBA6F7; display: flex; align-items: center; gap: 8px; }
        .header p { font-size: 0.8rem; color: #A6ADC8; margin-top: 4px; }
        
        .tabs { display: flex; border-bottom: 1px solid #2A2B3D; background: #181825; }
        .tab-btn { flex: 1; padding: 12px; border: none; background: none; color: #A6ADC8; font-weight: 600; cursor: pointer; transition: 0.2s; }
        .tab-btn.active { color: #89B4FA; border-bottom: 2px solid #89B4FA; background: #1E1E2E; }
        
        .content-area { flex: 1; overflow-y: auto; padding: 16px; }
        
        /* App List & Cards */
        .app-card { background: #1E1E2E; border: 1px solid #313244; border-radius: 8px; padding: 12px; margin-bottom: 12px; cursor: pointer; transition: 0.2s; }
        .app-card:hover { border-color: #89B4FA; transform: translateY(-1px); }
        .app-card.active { border-color: #CBA6F7; background: #242437; }
        .app-name { font-weight: 600; font-size: 0.95rem; color: #F5E0DC; }
        .app-meta { font-size: 0.78rem; color: #BAC2DE; margin-top: 4px; display: flex; justify-content: space-between; }

        /* History Entry */
        .history-item { background: #1E1E2E; border-left: 3px solid #89B4FA; border-radius: 4px; padding: 12px; margin-bottom: 10px; font-size: 0.85rem; }
        .history-scenario { font-weight: 700; color: #A6E3A1; font-size: 0.75rem; text-transform: uppercase; margin-bottom: 4px; }
        .history-text { color: #CDD6F4; line-height: 1.4; white-space: pre-wrap; font-family: inherit; }
        .history-arrow { color: #F9E2AF; margin: 6px 0; font-weight: bold; font-size: 0.75rem; }

        /* Graph Canvas */
        #main { flex: 1; display: flex; flex-direction: column; background: #0F0F17; position: relative; }
        #network { flex: 1; height: 100%; }
        
        .graph-controls { position: absolute; top: 16px; right: 16px; background: rgba(30, 30, 46, 0.85); backdrop-filter: blur(8px); border: 1px solid #313244; border-radius: 8px; padding: 10px; display: flex; gap: 10px; z-index: 10; }
        .control-btn { background: #313244; border: none; color: #CDD6F4; padding: 6px 12px; border-radius: 6px; font-size: 0.8rem; cursor: pointer; transition: 0.2s; }
        .control-btn:hover { background: #45475A; }
    </style>
</head>
<body>

    <div id="sidebar">
        <div class="header">
            <h1>✨ Copilot Dashboard</h1>
            <p>Knowledge Graph & Application Memory</p>
        </div>

        <div class="tabs">
            <button class="tab-btn active" onclick="switchTab('apps')">Applications</button>
            <button class="tab-btn" onclick="switchTab('nodes')">Graph Nodes</button>
        </div>

        <div class="content-area" id="tab-content">
            <!-- Dynamic Content -->
        </div>
    </div>

    <div id="main">
        <div class="graph-controls">
            <button class="control-btn" onclick="network.fit()">Zoom Fit</button>
            <button class="control-btn" onclick="fetchData()">Refresh Data</button>
        </div>
        <div id="network"></div>
    </div>

    <script>
        let network = null;
        let globalGraphData = null;
        let globalHistoryData = null;
        let currentTab = 'apps';

        async function fetchData() {
            try {
                const [gRes, hRes] = await Promise.all([
                    fetch('/api/graph'),
                    fetch('/api/history')
                ]);
                globalGraphData = await gRes.json();
                globalHistoryData = await hRes.json();
                
                renderGraph(globalGraphData);
                renderSidebar();
            } catch(e) {
                console.error("Error fetching dashboard data:", e);
            }
        }

        function renderGraph(graphData) {
            const container = document.getElementById('network');
            const nodes = [];
            const edges = [];

            const colorMap = {
                'APPLICATION': '#F38BA8',
                'PROJECT': '#CBA6F7',
                'TOOL': '#89B4FA',
                'TECH': '#A6E3A1',
                'SERVICE': '#FAB387',
                'CONCEPT': '#89DCEB'
            };

            for (const [name, meta] of Object.entries(graphData.nodes || {})) {
                const nodeType = meta.type || 'CONCEPT';
                nodes.push({
                    id: name,
                    label: name,
                    color: {
                        background: colorMap[nodeType] || '#89DCEB',
                        border: '#11111B',
                        highlight: { background: '#F5E0DC', border: '#CBA6F7' }
                    },
                    shape: nodeType === 'APPLICATION' ? 'hexagon' : 'dot',
                    size: 15 + Math.min((meta.frequency || 1) * 3, 30),
                    font: { color: '#CDD6F4', face: 'Segoe UI', size: 14 }
                });
            }

            for (const edge of (graphData.edges || [])) {
                edges.push({
                    from: edge.source,
                    to: edge.target,
                    label: edge.relation,
                    color: { color: '#45475A', highlight: '#CBA6F7' },
                    arrows: 'to',
                    font: { color: '#A6ADC8', size: 10, align: 'middle' }
                });
            }

            const data = { nodes: new vis.DataSet(nodes), edges: new vis.DataSet(edges) };
            const options = {
                nodes: { borderWidth: 2, shadow: true },
                edges: { width: 1.5, smooth: { type: 'continuous' } },
                physics: {
                    barnesHut: { gravitationalConstant: -3000, centralGravity: 0.3, springLength: 120 }
                }
            };

            if (network) network.destroy();
            network = new vis.Network(container, data, options);
        }

        function switchTab(tab) {
            currentTab = tab;
            document.querySelectorAll('.tab-btn').forEach(btn => btn.classList.remove('active'));
            event.target.classList.add('active');
            renderSidebar();
        }

        function renderSidebar() {
            const container = document.getElementById('tab-content');
            container.innerHTML = '';

            if (currentTab === 'apps') {
                const apps = globalHistoryData?.applications || {};
                if (Object.keys(apps).length === 0) {
                    container.innerHTML = '<p style="color:#6C7086;font-size:0.85rem;">No application logs yet.</p>';
                    return;
                }
                for (const [proc, meta] of Object.entries(apps)) {
                    const card = document.createElement('div');
                    card.className = 'app-card';
                    card.innerHTML = `
                        <div class="app-name">${proc}</div>
                        <div class="app-meta">
                            <span>${meta.count} interactions</span>
                            <span>${meta.last_scenario || 'GENERAL'}</span>
                        </div>
                    `;
                    card.onclick = () => renderAppHistory(proc);
                    container.appendChild(card);
                }
            } else {
                const nodes = globalGraphData?.nodes || {};
                for (const [name, meta] of Object.entries(nodes)) {
                    const card = document.createElement('div');
                    card.className = 'app-card';
                    card.innerHTML = `
                        <div class="app-name">${name}</div>
                        <div class="app-meta">
                            <span>Type: ${meta.type || 'CONCEPT'}</span>
                            <span>Frequency: ${meta.frequency || 1}</span>
                        </div>
                    `;
                    container.appendChild(card);
                }
            }
        }

        function renderAppHistory(processName) {
            const container = document.getElementById('tab-content');
            container.innerHTML = `<h3 style="font-size:0.9rem;color:#89B4FA;margin-bottom:12px;">Logs for ${processName}</h3>`;

            const entries = globalHistoryData?.entries?.[processName] || [];
            if (entries.length === 0) {
                container.innerHTML += '<p style="color:#6C7086;font-size:0.85rem;">No history found for this app.</p>';
                return;
            }

            for (const entry of entries.reverse()) {
                const item = document.createElement('div');
                item.className = 'history-item';
                item.innerHTML = `
                    <div class="history-scenario">${entry.scenario || 'GENERAL'}</div>
                    <div class="history-text"><b>Input:</b> ${escapeHtml(entry.original_text || '')}</div>
                    <div class="history-arrow">⬇ Rewritten</div>
                    <div class="history-text" style="color:#A6E3A1;">${escapeHtml(entry.rewritten_text || '')}</div>
                `;
                container.appendChild(item);
            }
        }

        function escapeHtml(str) {
            return str.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
        }

        fetchData();
    </script>
</body>
</html>
"""


class ThreadedHTTPServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True


class DashboardHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/' or self.path == '/index.html':
            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.end_headers()
            self.wfile.write(HTML_TEMPLATE.encode('utf-8'))

        elif self.path == '/api/graph':
            kg = KnowledgeGraph()
            graph_data = kg._read_local_graph()
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(graph_data, ensure_ascii=False).encode('utf-8'))

        elif self.path == '/api/history':
            history_mgr = HistoryManager()
            index_data = {}
            if history_mgr.index_file.exists():
                with open(history_mgr.index_file, 'r', encoding='utf-8') as f:
                    index_data = json.load(f)
            
            # Fetch per app entries
            entries_by_app = {}
            for app in index_data.get('applications', {}):
                entries_by_app[app] = history_mgr.get_app_history(app, limit=20)

            payload = {
                "applications": index_data.get('applications', {}),
                "total_entries": index_data.get('total_entries', 0),
                "entries": entries_by_app
            }
            self.send_response(200)
            self.send_header('Content-Type', 'application/json; charset=utf-8')
            self.end_headers()
            self.wfile.write(json.dumps(payload, ensure_ascii=False).encode('utf-8'))

        else:
            self.send_response(404)
            self.end_headers()

    def log_message(self, format, *args):
        pass # Suppress default HTTP server logs


def main():
    server = ThreadedHTTPServer(('localhost', PORT), DashboardHandler)
    url = f"http://localhost:{PORT}"
    print(f"============================================================")
    print(f" Launching Copilot Knowledge Graph Dashboard at: {url}")
    print(f" Press Ctrl+C in this terminal to stop the server.")
    print(f"============================================================")
    
    webbrowser.open(url)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping dashboard server...")
        server.server_close()


if __name__ == '__main__':
    main()
