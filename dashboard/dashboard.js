// dashboard.js
// This script fetches data from your backend and updates the dashboard UI.

// --- CONFIG ---
const ALERTS_API = 'http://127.0.0.1:5000/alerts'; // Update if your API endpoint is different

// --- Chart.js Setup ---
const fileChartCtx = document.getElementById('fileChart').getContext('2d');
const networkChartCtx = document.getElementById('networkChart').getContext('2d');

const fileChart = new Chart(fileChartCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            { label: 'Modifications', data: [], borderColor: '#17a2b8', fill: false },
            { label: 'Renames', data: [], borderColor: '#ffc107', fill: false }
        ]
    },
    options: { responsive: true, plugins: { legend: { display: true } } }
});

const networkChart = new Chart(networkChartCtx, {
    type: 'line',
    data: {
        labels: [],
        datasets: [
            { label: 'Connections', data: [], borderColor: '#007bff', fill: false },
            { label: 'Suspicious IPs', data: [], borderColor: '#dc3545', fill: false }
        ]
    },
    options: { responsive: true, plugins: { legend: { display: true } } }
});

// --- Fetch and Update Dashboard ---
async function fetchAndUpdate() {
    try {
        const res = await fetch(ALERTS_API);
        const alerts = await res.json();
        updateMetrics(alerts);
        updateCharts(alerts);
        updateAlerts(alerts);
    } catch (e) {
        document.getElementById('system-status').textContent = '⚠️ SYSTEM OFFLINE';
        document.getElementById('system-status').className = 'status-danger';
    }
}

function updateMetrics(alerts) {
    // Example: Calculate metrics from alerts (customize as needed)
    document.getElementById('mods').textContent = alerts.length;
    document.getElementById('renames').textContent = alerts.filter(a => a.event_type === 'rename').length;
    document.getElementById('entropy').textContent = (Math.random() * 8).toFixed(2); // Placeholder
    document.getElementById('connections').textContent = Math.floor(Math.random() * 20); // Placeholder
    document.getElementById('susp_ext').textContent = alerts.filter(a => a.suspicious_ext).length;
    document.getElementById('susp_ips').textContent = alerts.filter(a => a.suspicious_ip).length;
    document.getElementById('out_kbs').textContent = Math.floor(Math.random() * 100); // Placeholder
    document.getElementById('c2_status').textContent = 'Clear'; // Placeholder
}

function updateAlerts(alerts) {
    const alertsList = document.getElementById('alerts');
    alertsList.innerHTML = '';
    document.getElementById('alert-count').textContent = alerts.length;
    alerts.slice(-20).reverse().forEach(alert => {
        const li = document.createElement('li');
        li.className = 'list-group-item ' + (alert.immune_alarm ? 'alert-high' : alert.heuristic_alarm ? 'alert-low' : 'alert-info');
        li.innerHTML = `
            <b>Process:</b> ${alert.process_name || ''} <b>PID:</b> ${alert.pid} <b>File:</b> ${alert.file_affected || ''}<br>
            <b>What happened:</b> ${alert.actionable ? alert.actionable.what_happened : ''}<br>
            <b>What to do:</b> ${alert.actionable ? alert.actionable.what_to_do : ''}<br>
            <b>Timestamp:</b> ${new Date(alert.timestamp * 1000).toLocaleString()}<br>
            <b>False Positive:</b> ${alert.false_positive ? 'Yes' : 'No'}
        `;
        alertsList.appendChild(li);
    });
}
networkChart.data.datasets[0].data = Array.from({ length: 10 }, () => Math.floor(Math.random() * 20));
networkChart.data.datasets[1].data = Array.from({ length: 10 }, () => Math.floor(Math.random() * 3));
networkChart.update();
}

function updateAlerts(alerts) {
    const alertsList = document.getElementById('alerts');
    alertsList.innerHTML = '';
    document.getElementById('alert-count').textContent = alerts.length;
    alerts.slice(-20).reverse().forEach(alert => {
        const li = document.createElement('li');
        li.className = 'list-group-item ' + (alert.immune_alarm ? 'alert-high' : alert.heuristic ? 'alert-low' : 'alert-info');
        li.innerHTML = `<b>${alert.event_type || 'ALERT'}</b> | PID: ${alert.pid} | <span class="text-muted">${new Date(alert.timestamp * 1000).toLocaleTimeString()}</span><br>${JSON.stringify(alert)}`;
        alertsList.appendChild(li);
    });
}

// --- Poll every 3 seconds ---
setInterval(fetchAndUpdate, 3000);
fetchAndUpdate();
