const WS_URL = 'ws://127.0.0.1:8000/ws/events';
const ALERTS_API = 'http://127.0.0.1:8000/api/alerts';

const processRows = [
    { name: 'suspicious_encryption.exe', pid: 4824, cpu: '45.2%', memory: '128.5 MB', status: 'Quarantined' },
    { name: 'explorer.exe', pid: 2456, cpu: '2.1%', memory: '45.8 MB', status: 'Running' },
    { name: 'chrome.exe', pid: 3788, cpu: '1.8%', memory: '89.2 MB', status: 'Running' },
    { name: 'CIS_Service.exe', pid: 1620, cpu: '1.2%', memory: '12.4 MB', status: 'Protected' },
];

const liveEvents = [
    { time: '10:24:15', title: 'RANSOMWARE DETECTED', message: 'Process: suspicious_encryption.exe', type: 'high' },
    { time: '10:24:13', title: 'FILE ENCRYPTION DETECTED', message: 'Multiple files being encrypted', type: 'medium' },
    { time: '10:24:11', title: 'BEHAVIOR ANALYSIS', message: 'Suspicious behavior pattern matched', type: 'low' },
    { time: '10:24:09', title: 'NETWORK CONNECTION', message: 'Connection to suspicious IP blocked', type: 'low' },
    { time: '10:24:07', title: 'IMMUNE RESPONSE ACTIVATED', message: 'Process terminated and quarantined', type: 'info' },
];

function setText(id, text) {
    const el = document.getElementById(id);
    if (el) el.textContent = text;
}

function setMetric(id, value) {
    const el = document.getElementById(id);
    if (el) el.textContent = value;
}

function renderEventFeed(events) {
    const container = document.getElementById('eventFeed');
    if (!container) return;
    container.innerHTML = '';
    events.slice(0, 8).forEach(item => {
        const card = document.createElement('div');
        card.className = 'alert-item';
        card.innerHTML = `
            <h4>${item.title}</h4>
            <p>${item.message}</p>
            <div class="meta"><span>${item.time}</span><span>${item.type.toUpperCase()}</span></div>
        `;
        container.appendChild(card);
    });
}

function renderProcessTable(rows) {
    const body = document.getElementById('processTableBody');
    if (!body) return;
    body.innerHTML = '';
    rows.forEach(row => {
        const tr = document.createElement('tr');
        tr.innerHTML = `
            <td>${row.name}</td>
            <td>${row.pid}</td>
            <td>${row.cpu}</td>
            <td>${row.memory}</td>
            <td><span class="process-status ${row.status.toLowerCase() === 'quarantined' ? 'status-quarantined' : row.status.toLowerCase() === 'running' ? 'status-running' : 'status-protected'}">${row.status}</span></td>
        `;
        body.appendChild(tr);
    });
}

function renderMetrics() {
    setText('mods', '0');
    setText('renames', '0');
    setText('entropy', '0');
    setText('connections', '0');
    setText('susp_ext', '0');
    setText('susp_ips', '0');
    setText('out_kbs', '0');
    setText('c2_status', 'Clear');
    setText('cpu-usage', '23%');
    setText('mem-usage', '45%');
    setText('disk-usage', '31%');
    setText('network-usage', '12%');
}

function renderMapNodes() {
    const map = document.getElementById('mapCanvas');
    if (!map) return;
    map.innerHTML = '';
    const nodes = [
        { top: '22%', left: '36%', delay: 0 },
        { top: '40%', left: '52%', delay: 0.3 },
        { top: '60%', left: '48%', delay: 0.6 },
        { top: '55%', left: '70%', delay: 1 },
    ];
    nodes.forEach(node => {
        const dot = document.createElement('div');
        dot.className = 'attack-node';
        dot.style.top = node.top;
        dot.style.left = node.left;
        dot.style.animationDelay = `${node.delay}s`;
        map.appendChild(dot);
    });
}

function updateClock() {
    const now = new Date();
    setText('clock', now.toLocaleTimeString('en-US', { hour12: true }));
}

function initWebSocket() {
    const status = document.getElementById('feed-status');
    try {
        const ws = new WebSocket(WS_URL);
        ws.addEventListener('open', () => { if (status) status.textContent = 'WS Connected'; });
        ws.addEventListener('message', event => {
            const payload = JSON.parse(event.data);
            if (payload.type === 'alert') {
                const next = {
                    time: new Date().toLocaleTimeString('en-US', { hour12: true }),
                    title: payload.data.event_type || 'ALERT',
                    message: payload.data.description || JSON.stringify(payload.data.payload || {}),
                    type: payload.data.severity || 'high',
                };
                liveEvents.unshift(next);
                renderEventFeed(liveEvents);
            }
        });
        ws.addEventListener('close', () => { if (status) status.textContent = 'WS Disconnected'; });
        ws.addEventListener('error', () => { if (status) status.textContent = 'WS Error'; });
    } catch (e) {
        if (status) status.textContent = 'WS Error';
    }
}

async function loadLiveAlerts() {
    try {
        const response = await fetch(ALERTS_API);
        if (!response.ok) throw new Error('Fetch failed');
        const alerts = await response.json();
        setText('events-today', alerts.length.toString());
        setText('threat-level', alerts.some(a => a.severity === 'high') ? 'HIGH' : 'MEDIUM');
        setText('process-count', processRows.length.toString());
    } catch (err) {
        console.warn('Live alert fetch failed:', err);
    }
}

function initPage() {
    setText('attack-origin', '192.168.1.105');
    setText('target-system', 'DESKTOP-8G7JH2K');
    renderMetrics();
    renderEventFeed(liveEvents);
    renderProcessTable(processRows);
    renderMapNodes();
    updateClock();
    initWebSocket();
    loadLiveAlerts();
    setInterval(updateClock, 1000);
    document.getElementById('refreshLive')?.addEventListener('click', () => {
        loadLiveAlerts();
        renderEventFeed(liveEvents);
    });
}

initPage();
