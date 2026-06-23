from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
import json
import os
from functools import wraps

try:
    from .billing_api import register_billing_routes
    from .license_check import check_license, LicenseError
    from .feature_gating import FeatureGate
    from .database import get_user_subscription, get_db_connection
    from .auth import verify_password
    from .alert_explanation import annotate_alert
    from .security_automation import ThreatIntelligenceEngine, SelfHealingEngine
except ImportError:
    from billing_api import register_billing_routes
    from license_check import check_license, LicenseError
    from feature_gating import FeatureGate
    from database import get_user_subscription, get_db_connection
    from auth import verify_password
    from alert_explanation import annotate_alert
    from security_automation import ThreatIntelligenceEngine, SelfHealingEngine


app = Flask(__name__)
app.secret_key = os.environ.get("CIS_DASHBOARD_SECRET", "change_this_secret_in_production")
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"

# Register billing routes
register_billing_routes(app)

# ============================================================================
# USER & DATABASE MANAGEMENT
# ============================================================================

class User(UserMixin):
    def __init__(self, user_id, email, username, subscription_id=None, is_admin=False):
        self.id = user_id
        self.email = email
        self.username = username
        self.subscription_id = subscription_id
        self.is_admin = is_admin

@login_manager.user_loader
def load_user(user_id):
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, username FROM users WHERE id = ? AND is_active = 1', (int(user_id),))
        row = cursor.fetchone()
        conn.close()
        
        if row:
            subscription = get_user_subscription(row['id'])
            return User(row['id'], row['email'], row['username'], 
                       subscription['id'] if subscription else None)
    except Exception:
        pass
    return None

# ============================================================================
# DECORATORS & HELPERS
# ============================================================================

def require_license(f):
    """Decorator to require valid license for accessing features."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.subscription_id:
            return redirect(url_for('billing.trial_signup_page'))
        
        try:
            check_license(current_user.subscription_id)
            return f(*args, **kwargs)
        except LicenseError:
            return redirect(url_for('trial_expired'))
    
    return decorated_function

# ============================================================================
# ROUTES
# ============================================================================

@app.route("/")
def index():
    if current_user.is_authenticated:
        return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    """User login page."""
    if request.method == "POST":
        login_value = request.form.get("email")
        password = request.form.get("password")
        
        if not login_value or not password:
            return render_template_string(LOGIN_TEMPLATE, error="Email/username and password required"), 400
        
        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute(
                'SELECT id, email, username, password_hash FROM users '
                'WHERE (email = ? OR username = ?) AND is_active = 1',
                (login_value, login_value)
            )
            row = cursor.fetchone()
            conn.close()
            
            if row and verify_password(password, row['password_hash']):
                user = User(row['id'], row['email'], row['username'])
                login_user(user)
                return redirect(url_for("dashboard"))
            else:
                return render_template_string(LOGIN_TEMPLATE, error="Invalid email/username or password"), 401
        except Exception:
            return render_template_string(LOGIN_TEMPLATE, error="Login error"), 500
    
    return render_template_string(LOGIN_TEMPLATE)

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

@app.route("/dashboard")
@login_required
def dashboard():
    """Main dashboard page."""
    try:
        subscription = get_user_subscription(current_user.id)
        if not subscription:
            return redirect(url_for("billing.trial_signup_page"))
        
        license_info = check_license(subscription['id'])
        gate = FeatureGate(subscription['plan'])
        
        return render_template_string(DASHBOARD_TEMPLATE, 
                                     user=current_user,
                                     subscription=subscription,
                                     license=license_info,
                                     plan_summary=gate.get_plan_summary())
    except LicenseError:
        return redirect(url_for("trial_expired"))

@app.route("/trial-expired")
def trial_expired():
    """Trial expired page."""
    return render_template_string(TRIAL_EXPIRED_TEMPLATE), 403

@app.route("/billing")
@login_required
def billing():
    """Billing and subscription management page."""
    try:
        subscription = get_user_subscription(current_user.id)
        if not subscription:
            return redirect(url_for("billing.trial_signup_page"))
        
        license_info = check_license(subscription['id'])
        gate = FeatureGate(subscription['plan'])
        
        return render_template_string(BILLING_TEMPLATE,
                                     user=current_user,
                                     subscription=subscription,
                                     subscription_id=subscription['id'],
                                     license=license_info,
                                     plan_summary=gate.get_plan_summary())
    except LicenseError:
        return redirect(url_for("trial_expired"))

@app.route('/security-intelligence')
@login_required
@require_license
def security_intelligence():
    get_user_subscription(current_user.id)
    system_state = {
        'suspicious_ips': 3,
        'divergence': 1.9,
        'immune_alarm': False,
        'heuristic_alarm': True,
        'event_buffer': 40
    }
    engine = ThreatIntelligenceEngine()
    risk_score = engine.predict_risk_score(system_state)
    attack_path = engine.get_predicted_attack_path(system_state)
    recommendations = engine.get_recommendations(risk_score)
    business_impact = engine.get_business_impact(risk_score)
    feed = engine.get_global_threat_feed()

    return render_template_string(SECURITY_INTELLIGENCE_TEMPLATE,
                                 user=current_user,
                                 risk_score=risk_score,
                                 attack_path=attack_path,
                                 business_impact=business_impact,
                                 recommendations=recommendations,
                                 feed=feed)

@app.route('/self-healing')
@login_required
@require_license
def self_healing():
    get_user_subscription(current_user.id)
    system_state = {
        'suspicious_ips': 3,
        'divergence': 1.9,
        'immune_alarm': True,
        'heuristic_alarm': False,
        'event_buffer': 55
    }
    engine = SelfHealingEngine()
    actions = engine.evaluate_status(system_state)
    history = engine.get_action_history()

    return render_template_string(SELF_HEALING_TEMPLATE,
                                 user=current_user,
                                 actions=actions,
                                 history=history)


# Preview routes (no auth) for visual checks / screenshots
@app.route('/preview/security-intelligence')
def preview_security_intelligence():
    class DummyUser: pass
    dummy = DummyUser()
    dummy.id = 1
    dummy.username = 'preview'

    system_state = {
        'suspicious_ips': 3,
        'divergence': 1.9,
        'immune_alarm': False,
        'heuristic_alarm': True,
        'event_buffer': 40
    }
    engine = ThreatIntelligenceEngine()
    risk_score = engine.predict_risk_score(system_state)
    attack_path = engine.get_predicted_attack_path(system_state)
    recommendations = engine.get_recommendations(risk_score)
    business_impact = engine.get_business_impact(risk_score)
    feed = engine.get_global_threat_feed()

    return render_template_string(SECURITY_INTELLIGENCE_TEMPLATE,
                                 user=dummy,
                                 risk_score=risk_score,
                                 attack_path=attack_path,
                                 business_impact=business_impact,
                                 recommendations=recommendations,
                                 feed=feed)


@app.route('/preview/self-healing')
def preview_self_healing():
    class DummyUser: pass
    dummy = DummyUser()
    dummy.id = 1
    dummy.username = 'preview'

    system_state = {
        'suspicious_ips': 3,
        'divergence': 1.9,
        'immune_alarm': True,
        'heuristic_alarm': False,
        'event_buffer': 55
    }
    engine = SelfHealingEngine()
    actions = engine.evaluate_status(system_state)
    history = engine.get_action_history()

    return render_template_string(SELF_HEALING_TEMPLATE,
                                 user=dummy,
                                 actions=actions,
                                 history=history)

@app.route('/self-healing-action', methods=['POST'])
@login_required
@require_license
def self_healing_action():
    data = request.get_json() or {}
    action_id = data.get('action_id')
    engine = SelfHealingEngine()
    result = engine.perform_action(action_id, current_user.id)
    return jsonify(result)

@app.route("/status")
@login_required
@require_license
def status():
    """System status page."""
    status_file = os.environ.get("CIS_STATUS_FILE", os.path.join(os.environ.get("TEMP", "/tmp"), "cis_status.json"))
    
    try:
        if os.path.exists(status_file):
            with open(status_file, "r") as f:
                status_data = json.load(f)
        else:
            status_data = {"status": "initializing"}
    except Exception as e:
        status_data = {"error": str(e)}
    
    return jsonify(status_data)

@app.route("/alerts")
@login_required
@require_license
def alerts():
    """Recent alerts page."""
    alerts_file = os.environ.get("CIS_ALERTS_FILE", os.path.join(os.environ.get("TEMP", "/tmp"), "cis_alerts.jsonl"))
    
    alerts_list = []
    if os.path.exists(alerts_file):
        try:
            with open(alerts_file, "r") as f:
                for line in f:
                    if line.strip():
                        alerts_list.append(annotate_alert(json.loads(line)))
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    
    return render_template_string(ALERTS_TEMPLATE, alerts=alerts_list[-50:])

@app.route("/alerts-json")
@login_required
@require_license
def alerts_json():
    alerts_file = os.environ.get("CIS_ALERTS_FILE", os.path.join(os.environ.get("TEMP", "/tmp"), "cis_alerts.jsonl"))
    alerts_list = []
    if os.path.exists(alerts_file):
        try:
            with open(alerts_file, "r") as f:
                for line in f:
                    if line.strip():
                        alerts_list.append(annotate_alert(json.loads(line)))
        except Exception as e:
            return jsonify({"error": str(e)}), 400
    return jsonify(alerts_list[-20:])

@app.errorhandler(404)
def page_not_found(e):
    return render_template_string("<h1>404 - Page Not Found</h1><a href='/'>Home</a>"), 404

@app.errorhandler(500)
def server_error(e):
    return render_template_string("<h1>500 - Server Error</h1><a href='/'>Home</a>"), 500

# ============================================================================
# HTML TEMPLATES
# ============================================================================

LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Login</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; display: flex; align-items: center; }
        .login-container { max-width: 400px; width: 100%; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
        h2 { color: #667eea; margin-bottom: 1.5rem; }
        .btn-primary { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border: none; }
    </style>
</head>
<body>
    <div class="login-container">
        <h2 class="text-center">CIS Login</h2>
        {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
        <form method="post">
            <div class="mb-3">
                <label class="form-label">Email</label>
                <input type="email" class="form-control" name="email" required autofocus>
            </div>
            <div class="mb-3">
                <label class="form-label">Password</label>
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100 mb-3">Login</button>
        </form>
        <hr>
        <div class="text-center">
            <p class="text-muted">No account yet?</p>
            <a href="/api/billing/trial-signup" class="btn btn-outline-primary w-100">Start Free Trial</a>
        </div>
    </div>
</body>
</html>
'''

DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <style>
        body { background: #0b1120; color: #e5e7eb; }
        .navbar { background: #111827; }
        .navbar-brand, .nav-link { color: #e5e7eb !important; }
        .metric-card, .dashboard-card { border: 1px solid rgba(148, 163, 184, 0.18); background: rgba(15, 23, 42, 0.9); border-radius: 1rem; }
        .metric-title { color: #94a3b8; font-size: 0.85rem; text-transform: uppercase; letter-spacing: 0.04em; }
        .metric-value { font-size: 2rem; font-weight: 700; margin: 0; }
        .metric-note { color: #94a3b8; font-size: 0.8rem; }
        .status-pill { padding: 0.5rem 1rem; border-radius: 999px; font-weight: 700; }
        .status-clear { background: #16a34a; color: #ecfccb; }
        .status-alert { background: #dc2626; color: #fecaca; }
        .chart-card { min-height: 320px; }
        .alert-feed { max-height: 420px; overflow-y: auto; }
        .alert-item { border-bottom: 1px solid rgba(148, 163, 184, 0.15); padding: 1rem 0; }
        .alert-item:last-child { border-bottom: none; }
        .alert-severity { font-size: 0.75rem; padding: 0.25rem 0.6rem; border-radius: 999px; font-weight: 700; }
        .alert-high { background: #dc2626; color: white; }
        .alert-medium { background: #f97316; color: white; }
        .alert-info { background: #2563eb; color: white; }
        .top-summary { display: flex; gap: 0.75rem; flex-wrap: wrap; }
        .top-box { flex: 1 1 180px; padding: 1rem; background: rgba(255,255,255,0.04); border-radius: 1rem; border: 1px solid rgba(148, 163, 184, 0.18); }
        .top-box h6 { margin-bottom: 0.5rem; color: #94a3b8; }
        .top-box p { margin: 0; font-size: 1.6rem; font-weight: 700; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid px-4">
            <a class="navbar-brand" href="/">CIS Ransomware Detection</a>
            <div class="d-flex gap-3">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/alerts">Alerts</a>
                <a class="nav-link" href="/security-intelligence">Threat Intel</a>
                <a class="nav-link" href="/self-healing">Auto Response</a>
                <a class="nav-link" href="/billing">Billing</a>
                <a class="nav-link" href="/logout">Logout ({{ user.username }})</a>
            </div>
        </div>
    </nav>

    <div class="container-fluid px-4 py-4">
        <div class="d-flex justify-content-between align-items-center mb-4">
            <div>
                <h1 class="h3">Realtime System Monitor</h1>
                <p class="text-muted">Monitor everything the CI S engine is doing in real time.</p>
            </div>
            <div id="healthStatus" class="status-pill status-clear">System Secure</div>
        </div>

        <div class="top-summary mb-4">
            <div class="top-box">
                <h6>Mods / min</h6>
                <p id="modsPerMin">0</p>
            </div>
            <div class="top-box">
                <h6>Renames / min</h6>
                <p id="renamesPerMin">0</p>
            </div>
            <div class="top-box">
                <h6>Suspicious Ext</h6>
                <p id="suspExt">0</p>
            </div>
            <div class="top-box">
                <h6>Entropy</h6>
                <p id="entropy">0.00</p>
            </div>
            <div class="top-box">
                <h6>Connections</h6>
                <p id="connections">0</p>
            </div>
            <div class="top-box">
                <h6>Susp. IPs</h6>
                <p id="suspIps">0</p>
            </div>
            <div class="top-box">
                <h6>Out KB/s</h6>
                <p id="outKbps">0</p>
            </div>
            <div class="top-box">
                <h6>C2 Status</h6>
                <p id="c2Status">Clear</p>
            </div>
        </div>

        <div class="row g-3 mb-4">
            <div class="col-xl-8">
                <div class="card chart-card p-4 dashboard-card">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h5 class="mb-1">File Activity</h5>
                            <p class="text-muted mb-0">Live modifications and alert divergence.</p>
                        </div>
                    </div>
                    <canvas id="fileActivityChart"></canvas>
                </div>
            </div>
            <div class="col-xl-4">
                <div class="card p-4 dashboard-card">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h5 class="mb-1">Real-Time Alerts</h5>
                            <p class="text-muted mb-0">Latest detection items.</p>
                        </div>
                    </div>
                    <div id="alertFeed" class="alert-feed"></div>
                </div>
            </div>
        </div>

        <div class="row g-3">
            <div class="col-xl-6">
                <div class="card chart-card p-4 dashboard-card">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h5 class="mb-1">Network Activity</h5>
                            <p class="text-muted mb-0">Event buffer and system traffic.</p>
                        </div>
                    </div>
                    <canvas id="networkActivityChart"></canvas>
                </div>
            </div>
            <div class="col-xl-6">
                <div class="card p-4 dashboard-card">
                    <div class="d-flex justify-content-between align-items-start mb-3">
                        <div>
                            <h5 class="mb-1">Engine Telemetry</h5>
                            <p class="text-muted mb-0">Current telemetry values.</p>
                        </div>
                        <span class="text-muted" id="statusTimestamp">--</span>
                    </div>
                    <div class="row g-3">
                        <div class="col-6">
                            <div class="metric-card p-3">
                                <div class="metric-title">Buffer</div>
                                <p id="eventBuffer" class="metric-value">0</p>
                                <p class="metric-note">Queued event count</p>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="metric-card p-3">
                                <div class="metric-title">Side Samples</div>
                                <p id="sideBuffer" class="metric-value">0</p>
                                <p class="metric-note">Side-channel buffer</p>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="metric-card p-3">
                                <div class="metric-title">Divergence</div>
                                <p id="divergence" class="metric-value">0.00</p>
                                <p class="metric-note">Current model divergence</p>
                            </div>
                        </div>
                        <div class="col-6">
                            <div class="metric-card p-3">
                                <div class="metric-title">False Positives</div>
                                <p id="falsePositives" class="metric-value">0</p>
                                <p class="metric-note">Acknowledged alerts</p>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    </div>

    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        const statusHistory = { labels: [], mods: [], divergence: [], events: [] };
        const fileChartCtx = document.getElementById('fileActivityChart').getContext('2d');
        const networkChartCtx = document.getElementById('networkActivityChart').getContext('2d');

        const fileActivityChart = new Chart(fileChartCtx, {
            type: 'line',
            data: {
                labels: statusHistory.labels,
                datasets: [
                    { label: 'Mods', data: statusHistory.mods, borderColor: '#38bdf8', backgroundColor: 'rgba(56, 189, 248, 0.24)', tension: 0.35, fill: true },
                    { label: 'Divergence', data: statusHistory.divergence, borderColor: '#f87171', backgroundColor: 'rgba(248, 113, 113, 0.22)', tension: 0.35, fill: false }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: { ticks: { color: '#cbd5e1' } },
                    y: { ticks: { color: '#cbd5e1' }, beginAtZero: true }
                },
                plugins: { legend: { labels: { color: '#e2e8f0' } } }
            }
        });

        const networkActivityChart = new Chart(networkChartCtx, {
            type: 'line',
            data: {
                labels: statusHistory.labels,
                datasets: [
                    { label: 'Event Buffer', data: statusHistory.events, borderColor: '#a78bfa', backgroundColor: 'rgba(167, 139, 250, 0.24)', tension: 0.35, fill: true }
                ]
            },
            options: {
                responsive: true,
                scales: {
                    x: { ticks: { color: '#cbd5e1' } },
                    y: { ticks: { color: '#cbd5e1' }, beginAtZero: true }
                },
                plugins: { legend: { labels: { color: '#e2e8f0' } } }
            }
        });

        function calculateRiskScore(status) {
            let score = 20;
            score += Math.min(40, (status.suspicious_ips || 0) * 8);
            score += Math.min(30, (status.divergence || 0) * 5);
            if (status.immune_alarm) score += 20;
            if (status.heuristic_alarm) score += 15;
            if ((status.event_buffer || 0) > 50) score += 10;
            return Math.min(100, Math.max(0, Math.round(score)));
        }

        function updateRiskWidgets(status) {
            const riskScore = calculateRiskScore(status);
            document.getElementById('riskScore').textContent = riskScore;
            const attackPath = status.immune_alarm && status.suspicious_ips > 2 ? 'Lateral movement via admin shares' :
                               status.divergence > 2.5 ? 'Ransomware encryption chain' :
                               status.suspicious_ips > 0 ? 'C2 beaconing and reconnaissance' :
                               'No active path predicted';
            document.getElementById('attackPath').textContent = attackPath;
        }

        function updateStatusDisplay(status) {
            const now = new Date();
            document.getElementById('statusTimestamp').textContent = now.toLocaleTimeString();
            document.getElementById('modsPerMin').textContent = status.modifications_per_min ?? 0;
            document.getElementById('renamesPerMin').textContent = status.renames_per_min ?? 0;
            document.getElementById('suspExt').textContent = (status.divergence ?? 0).toFixed(2);
            document.getElementById('entropy').textContent = (status.encryption_indicator ?? 0).toFixed(2);
            document.getElementById('connections').textContent = status.connections ?? 0;
            document.getElementById('suspIps').textContent = status.suspicious_ips ?? 0;
            document.getElementById('outKbps').textContent = status.out_kbps ?? 0;
            document.getElementById('c2Status').textContent = (status.immune_alarm || status.heuristic_alarm) ? 'Suspected' : 'Clear';
            document.getElementById('eventBuffer').textContent = status.event_buffer ?? 0;
            document.getElementById('sideBuffer').textContent = status.side_buffer ?? 0;
            document.getElementById('divergence').textContent = (status.divergence ?? 0).toFixed(2);
            document.getElementById('falsePositives').textContent = status.false_positive_count ?? 0;
            updateRiskWidgets(status);

            const health = document.getElementById('healthStatus');
            if (status.immune_alarm || status.heuristic_alarm) {
                health.textContent = 'Threat Detected';
                health.classList.remove('status-clear');
                health.classList.add('status-alert');
            } else {
                health.textContent = 'System Secure';
                health.classList.remove('status-alert');
                health.classList.add('status-clear');
            }
        }

        function addStatusPoint(status) {
            const label = new Date().toLocaleTimeString();
            statusHistory.labels.push(label);
            statusHistory.mods.push(status.modified_files_count ?? 0);
            statusHistory.divergence.push(status.divergence ?? 0);
            statusHistory.events.push(status.event_buffer ?? 0);
            if (statusHistory.labels.length > 20) {
                statusHistory.labels.shift();
                statusHistory.mods.shift();
                statusHistory.divergence.shift();
                statusHistory.events.shift();
            }
            fileActivityChart.update();
            networkActivityChart.update();
        }

        function renderAlerts(alerts) {
            const feed = document.getElementById('alertFeed');
            feed.innerHTML = '';
            if (!alerts.length) {
                feed.innerHTML = '<p class="text-muted">No recent alerts.</p>';
                return;
            }
            alerts.slice().reverse().forEach(alert => {
                const alertTime = alert.timestamp ? new Date(alert.timestamp * 1000).toLocaleTimeString() : 'Now';
                const severity = alert.severity || 'INFO';
                const severityClass = severity === 'HIGH' ? 'alert-high' : severity === 'MEDIUM' ? 'alert-medium' : 'alert-info';
                const item = document.createElement('div');
                item.className = 'alert-item';
                item.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        <div><strong>${alert.process_name || alert.event || 'Alert'}</strong></div>
                        <span class="alert-severity ${severityClass}">${severity}</span>
                    </div>
                    <div><small>${alert.explanation?.summary || alert.actionable?.what_happened || 'No explanation'}</small></div>
                    <div class="text-muted mt-2" style="font-size: 0.8rem;">${alertTime}</div>
                `;
                feed.appendChild(item);
            });
        }

        async function refreshStatus() {
            try {
                const res = await fetch('/status');
                const status = await res.json();
                updateStatusDisplay(status);
                addStatusPoint(status);
            } catch (err) {
                console.error('Status refresh failed', err);
            }
        }

        async function refreshAlerts() {
            try {
                const res = await fetch('/alerts-json');
                const alerts = await res.json();
                renderAlerts(alerts);
            } catch (err) {
                console.error('Alerts refresh failed', err);
            }
        }

        refreshStatus();
        refreshAlerts();
        setInterval(refreshStatus, 2000);
        setInterval(refreshAlerts, 3000);
    </script>
</body>
</html>
'''

SECURITY_INTELLIGENCE_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Threat Intelligence</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        /* Light, clean theme matching Alerts page */
        body { background: #f8f9fa; color: #111827; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: #ffffff; border: 1px solid #e5e7eb; color: #111827; box-shadow: 0 6px 18px rgba(0,0,0,0.06); }
        .badge-recommendation { background: #2563eb; color: white; }
        h1, h3, h4, h5, h6 { color: #0f172a; }
        .text-muted { color: #6b7280 !important; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid px-4">
            <a class="navbar-brand" href="/">CIS Security</a>
            <div class="d-flex gap-3">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/alerts">Alerts</a>
                <a class="nav-link" href="/security-intelligence">Threat Intel</a>
                <a class="nav-link" href="/self-healing">Auto Response</a>
                <a class="nav-link" href="/billing">Billing</a>
                <a class="nav-link" href="/logout">Logout ({{ user.username }})</a>
            </div>
        </div>
    </nav>
    <div class="container py-4">
        <div class="row g-4">
            <div class="col-lg-8">
                <div class="card p-4 mb-4">
                    <h3>Threat Intelligence</h3>
                    <p class="text-muted">A predictive intelligence feed with attack path and business impact.</p>
                    <div class="row gy-3 mt-3">
                        <div class="col-md-4">
                            <div class="p-3 border rounded">
                                <h6>Risk Score</h6>
                                <p class="display-6 mb-0">{{ risk_score }}%</p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded">
                                <h6>Attack Path</h6>
                                <p>{{ attack_path }}</p>
                            </div>
                        </div>
                        <div class="col-md-4">
                            <div class="p-3 border rounded">
                                <h6>Business Impact</h6>
                                <p>{{ business_impact }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="card p-4 mb-4">
                    <h4>Threat Feed</h4>
                    <div class="list-group list-group-flush mt-3">
                        {% for item in feed %}
                        <div class="list-group-item bg-transparent border-bottom">
                            <div class="d-flex justify-content-between align-items-start">
                                <div>
                                    <h6 class="mb-1">{{ item.name }}</h6>
                                    <small class="text-muted">{{ item.source }}</small>
                                </div>
                                <span class="badge bg-{{ 'danger' if item.confidence == 'high' else 'warning' if item.confidence == 'medium' else 'secondary' }}">{{ item.confidence|capitalize }}</span>
                            </div>
                            <p class="mb-0 mt-2 text-muted">{{ item.description }}</p>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div class="col-lg-4">
                <div class="card p-4 mb-4">
                    <h4>Recommendations</h4>
                    <ul class="list-group list-group-flush mt-3">
                        {% for rec in recommendations %}
                        <li class="list-group-item bg-transparent border-bottom">{{ rec }}</li>
                        {% endfor %}
                    </ul>
                </div>
                <div class="card p-4">
                    <h4>Why this matters</h4>
                    <p class="text-muted mb-0">Predictive analysis combines global threat feed signals with local telemetry to surface the highest-risk attack vectors before they execute.</p>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

SELF_HEALING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Self-Healing Response</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        /* Light, clean Auto Response styling */
        body { background: #f8f9fa; color: #111827; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .card { background: #ffffff; border: 1px solid #e5e7eb; color: #111827; box-shadow: 0 6px 18px rgba(0,0,0,0.06); }
        .action-card:hover { transform: translateY(-2px); box-shadow: 0 8px 24px rgba(0,0,0,0.08); }
        h3, h4, h5 { color: #0f172a; }
        .text-muted { color: #6b7280 !important; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg">
        <div class="container-fluid px-4">
            <a class="navbar-brand" href="/">CIS Security</a>
            <div class="d-flex gap-3">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/alerts">Alerts</a>
                <a class="nav-link" href="/security-intelligence">Threat Intel</a>
                <a class="nav-link" href="/self-healing">Auto Response</a>
                <a class="nav-link" href="/billing">Billing</a>
                <a class="nav-link" href="/logout">Logout ({{ user.username }})</a>
            </div>
        </div>
    </nav>
    <div class="container py-4">
        <div class="row g-4">
            <div class="col-lg-7">
                <div class="card p-4 mb-4">
                    <h3>Self-Healing Actions</h3>
                    <p class="text-muted">Actions are recommended automatically to block threats, recover systems, and reduce risk.</p>
                    <div class="row row-cols-1 gy-3 mt-3">
                        {% for action in actions %}
                        <div class="col">
                            <div class="card p-3 action-card">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <h5>{{ action.title }}</h5>
                                        <p class="text-muted mb-1">{{ action.description }}</p>
                                        <small class="text-secondary">Risk reduction: {{ action.risk_reduction }}%</small>
                                    </div>
                                    <button class="btn btn-primary" onclick="executeAction('{{ action.id }}')">Execute</button>
                                </div>
                            </div>
                        </div>
                        {% endfor %}
                    </div>
                </div>
            </div>
            <div class="col-lg-5">
                <div class="card p-4 mb-4">
                    <h4>Automation History</h4>
                    <div id="historyList" class="list-group list-group-flush mt-3">
                        {% if history %}
                            {% for event in history[:8] %}
                            <div class="list-group-item bg-transparent border-bottom">
                                <div class="d-flex justify-content-between align-items-start">
                                    <div>
                                        <strong>{{ event.title }}</strong>
                                        <p class="text-muted mb-1">{{ event.result }}</p>
                                    </div>
                                    <small>{{ event.timestamp }}</small>
                                </div>
                                <p class="text-muted mb-0">Risk reduction: {{ event.risk_reduction }}%</p>
                            </div>
                            {% endfor %}
                        {% else %}
                        <div class="list-group-item bg-transparent">
                            <p class="text-muted mb-0">No automation actions executed yet.</p>
                        </div>
                        {% endif %}
                    </div>
                </div>
                <div class="card p-4">
                    <h4>Why self-healing?</h4>
                    <p class="text-muted mb-0">Automated remediation and rollback reduce dwell time, stop attackers faster, and produce clear audit trails for every change.</p>
                </div>
            </div>
        </div>
    </div>
    <script>
        async function executeAction(actionId) {
            try {
                const response = await fetch('/self-healing-action', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ action_id: actionId })
                });
                const payload = await response.json();
                if (!response.ok || !payload.success) {
                    alert(payload.message || 'Self-healing action failed.');
                    return;
                }
                alert(payload.message);
                window.location.reload();
            } catch (err) {
                alert('Action failed: ' + err.message);
            }
        }
    </script>
</body>
</html>
'''

BILLING_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Billing</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
        .pricing-card { border: none; box-shadow: 0 2px 10px rgba(0,0,0,0.1); transition: transform 0.3s; }
        .pricing-card:hover { transform: translateY(-5px); }
        .current-plan { border: 3px solid #28a745; }
        .price { font-size: 2rem; font-weight: bold; color: #667eea; }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">CIS Security</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4 mb-5">
        <h1>Billing & Subscription</h1>
        
        <div class="row mt-4">
            <div class="col-md-12">
                <div class="card p-3">
                    <h5>Current Subscription</h5>
                    <div class="row">
                        <div class="col-md-6">
                            <p><strong>Plan:</strong> <span class="badge bg-primary">{{ subscription.plan.upper() }}</span></p>
                            <p><strong>Status:</strong> <span class="badge bg-success">{{ subscription.status }}</span></p>
                        </div>
                        <div class="col-md-6">
                            {% if subscription.is_trial %}
                            <p><strong>Trial Expires:</strong> {{ subscription.trial_end_date }}</p>
                            {% else %}
                            <p><strong>Next Billing Date:</strong> {{ subscription.subscription_end_date }}</p>
                            {% endif %}
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <h3 class="mt-5 mb-3">Payment Details</h3>
        <div class="card p-4 mb-4">
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="form-label">Full Name</label>
                    <input id="cardholderName" type="text" class="form-control" placeholder="Cardholder name" required>
                </div>
                <div class="col-md-6">
                    <label class="form-label">Billing Email</label>
                    <input id="billingEmail" type="email" class="form-control" placeholder="name@example.com" required>
                </div>
                <div class="col-md-12">
                    <label class="form-label">Card Number</label>
                    <input id="cardNumber" type="text" class="form-control" placeholder="1234 5678 9012 3456" maxlength="19" required>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Exp. Month</label>
                    <input id="expMonth" type="text" class="form-control" placeholder="MM" maxlength="2" required>
                </div>
                <div class="col-md-4">
                    <label class="form-label">Exp. Year</label>
                    <input id="expYear" type="text" class="form-control" placeholder="YY" maxlength="2" required>
                </div>
                <div class="col-md-4">
                    <label class="form-label">CVC</label>
                    <input id="cvc" type="text" class="form-control" placeholder="123" maxlength="4" required>
                </div>
            </div>
        </div>

        <h3 class="mt-5 mb-3">Available Plans</h3>
        <div class="mb-4">
            <label class="form-label">Billing Cycle</label>
            <div class="btn-group" role="group" aria-label="Billing period">
                <input type="radio" class="btn-check" name="billingPeriod" id="billingMonthly" value="monthly" autocomplete="off" checked>
                <label class="btn btn-outline-primary" for="billingMonthly">Monthly</label>
                <input type="radio" class="btn-check" name="billingPeriod" id="billingYearly" value="yearly" autocomplete="off">
                <label class="btn btn-outline-primary" for="billingYearly">Yearly</label>
            </div>
            <p class="text-muted small mt-2">Yearly billing saves 2 months of fees compared to monthly pricing.</p>
        </div>
        <div class="row">
            <div class="col-md-4">
                <div class="card pricing-card p-3 {% if subscription.plan == 'free_trial' %}current-plan{% endif %}">
                    <h5>Free Trial</h5>
                    <p class="text-muted small">14 days, all features</p>
                    <p class="price">$0<span style="font-size: 1rem;">/mo</span></p>
                    <ul class="list-unstyled small">
                        <li>✓ 5 endpoints</li>
                        <li>✓ Basic detection</li>
                        <li>✓ Alerts & monitoring</li>
                        <li>✓ Community support</li>
                    </ul>
                    {% if subscription.plan == 'free_trial' %}
                    <span class="badge bg-success w-100 mt-2">Current Plan</span>
                    {% endif %}
                </div>
            </div>
            <div class="col-md-4">
                <div class="card pricing-card p-3 {% if subscription.plan == 'pro' %}current-plan{% endif %}">
                    <h5>Pro</h5>
                    <p class="text-muted small">$6 / endpoint / month<br>$60 / endpoint / year</p>
                    <p class="price"><span id="proPrice">$6</span><span style="font-size: 1rem;">/endpoint</span></p>
                    <ul class="list-unstyled small">
                        <li>✓ 50 endpoints</li>
                        <li>✓ Causal trace analysis</li>
                        <li>✓ API access</li>
                        <li>✓ Email support</li>
                    </ul>
                    {% if subscription.plan == 'pro' %}
                    <span class="badge bg-success w-100 mt-2">Current Plan</span>
                    {% else %}
                    <button class="btn btn-primary btn-sm w-100 mt-2" onclick="upgradePlan('pro')">Upgrade</button>
                    {% endif %}
                </div>
            </div>
            <div class="col-md-4">
                <div class="card pricing-card p-3 {% if subscription.plan == 'enterprise' %}current-plan{% endif %}">
                    <h5>Enterprise</h5>
                    <p class="text-muted small">$12 / endpoint / month<br>$120 / endpoint / year</p>
                    <p class="price"><span id="enterprisePrice">$12</span><span style="font-size: 1rem;">/endpoint</span></p>
                    <ul class="list-unstyled small">
                        <li>✓ Unlimited endpoints</li>
                        <li>✓ All features</li>
                        <li>✓ Custom integration</li>
                        <li>✓ SLA support</li>
                    </ul>
                    {% if subscription.plan == 'enterprise' %}
                    <span class="badge bg-success w-100 mt-2">Current Plan</span>
                    {% else %}
                    <button class="btn btn-primary btn-sm w-100 mt-2" onclick="upgradePlan('enterprise')">Upgrade</button>
                    {% endif %}
                </div>
            </div>
        </div>
    </div>
    
    <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/js/bootstrap.bundle.min.js"></script>
    <script>
        function collectPaymentMethod() {
            return {
                name: document.getElementById('cardholderName').value.trim(),
                email: document.getElementById('billingEmail').value.trim(),
                card_number: document.getElementById('cardNumber').value.replace(/\s+/g, ''),
                exp_month: document.getElementById('expMonth').value.trim(),
                exp_year: document.getElementById('expYear').value.trim(),
                cvc: document.getElementById('cvc').value.trim()
            };
        }

        function getBillingPeriod() {
            const selected = document.querySelector('input[name="billingPeriod"]:checked');
            return selected ? selected.value : 'monthly';
        }

        function updatePriceLabels() {
            const period = getBillingPeriod();
            document.getElementById('proPrice').textContent = period === 'monthly' ? '$6' : '$60';
            document.getElementById('enterprisePrice').textContent = period === 'monthly' ? '$12' : '$120';
        }

        document.querySelectorAll('input[name="billingPeriod"]').forEach((radio) => {
            radio.addEventListener('change', updatePriceLabels);
        });

        updatePriceLabels();

        async function upgradePlan(plan) {
            const billingPeriod = getBillingPeriod();
            const endpoints = plan === 'enterprise' ? 1 : 10;
            const paymentMethod = collectPaymentMethod();

            if (!paymentMethod.name || !paymentMethod.email || !paymentMethod.card_number || !paymentMethod.exp_month || !paymentMethod.exp_year || !paymentMethod.cvc) {
                alert('Please complete all payment fields before upgrading.');
                return;
            }

            if (!confirm(`Upgrade to ${plan.toUpperCase()} (${billingPeriod}) for ${endpoints} endpoint(s)?`)) {
                return;
            }

            try {
                const response = await fetch('/api/billing/upgrade', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-Subscription-ID': '{{ subscription_id }}'
                    },
                    body: JSON.stringify({
                        plan: plan,
                        billing_period: billingPeriod,
                        endpoints: endpoints,
                        payment_method: paymentMethod
                    })
                });

                const payload = await response.json();
                if (!response.ok) {
                    throw new Error(payload.error || 'Upgrade failed');
                }

                alert(payload.message || `Successfully upgraded to ${plan}.`);
                window.location.reload();
            } catch (error) {
                alert(`Payment upgrade failed: ${error.message}`);
            }
        }
    </script>
</body>
</html>
'''

ALERTS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>CIS - Alerts</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; }
        .navbar { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); }
    </style>
</head>
<body>
    <nav class="navbar navbar-expand-lg navbar-dark">
        <div class="container">
            <a class="navbar-brand" href="/">CIS Security</a>
            <div class="navbar-nav ms-auto">
                <a class="nav-link" href="/dashboard">Dashboard</a>
                <a class="nav-link" href="/logout">Logout</a>
            </div>
        </div>
    </nav>
    
    <div class="container mt-4">
        <h1>Recent Alerts</h1>
        {% if alerts %}
        <table class="table table-striped table-hover">
            <thead class="table-dark">
                <tr><th>Time</th><th>Severity</th><th>Message</th><th>Explanation</th><th>Recommended Action</th><th>Details</th></tr>
            </thead>
            <tbody>
                {% for alert in alerts %}
                <tr>
                    <td>{{ alert.get('timestamp', 'N/A') }}</td>
                    <td><span class="badge {% if alert.get('severity') == 'HIGH' %}bg-danger{% elif alert.get('severity') == 'MEDIUM' %}bg-warning{% else %}bg-info{% endif %}">{{ alert.get('severity', 'INFO') }}</span></td>
                    <td>{{ alert.get('message', 'No message') }}</td>
                    <td>{{ alert.get('explanation', {}).get('summary', alert.get('actionable', {}).get('what_happened', 'No explanation')) }}</td>
                    <td><small class="text-muted">{{ alert.get('explanation', {}).get('recommended_action', alert.get('actionable', {}).get('what_to_do', 'No action recommended')) }}</small></td>
                    <td><small class="text-muted">{{ alert.get('endpoint_id', 'N/A') }}</small></td>
                </tr>
                {% endfor %}
            </tbody>
        </table>
        {% else %}
        <div class="alert alert-info">No alerts</div>
        {% endif %}
    </div>
</body>
</html>
'''

TRIAL_EXPIRED_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>Trial Expired</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; display: flex; align-items: center; min-height: 100vh; }
        .alert-container { max-width: 600px; }
    </style>
</head>
<body>
    <div class="container">
        <div class="alert-container">
            <div class="alert alert-danger" role="alert">
                <h4 class="alert-heading">⚠️ Trial Expired</h4>
                <p>Your free trial has expired. Please upgrade to continue using CIS.</p>
                <hr>
                <div>
                    <a href="/api/billing/plans" class="btn btn-primary">View Plans</a>
                    <a href="/logout" class="btn btn-secondary">Logout</a>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

# ============================================================================
# START
# ============================================================================

if __name__ == "__main__":
    app.run(debug=True, host="127.0.0.1", port=5000)
