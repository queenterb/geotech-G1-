from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Response
import json
import os

try:
    from .alert_explanation import annotate_alert
except ImportError:
    from alert_explanation import annotate_alert

app = Flask(__name__)
app.secret_key = os.environ.get("CIS_DASHBOARD_SECRET", "change_this_secret")
login_manager = LoginManager()
login_manager.init_app(app)


# Simple user/org store (for demo; use a DB in production)
USERS = {
    "admin": {"password": "adminpass", "role": "admin", "org": "acme"},
    "user": {"password": "userpass", "role": "user", "org": "acme"},
    "msp": {"password": "msppass", "role": "msp_admin", "org": "msp1"},
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.role = USERS[username]["role"]
        self.org = USERS[username]["org"]

@login_manager.user_loader
def load_user(user_id):
    if user_id in USERS:
        return User(user_id)
    return None

# RBAC decorator
from functools import wraps
def roles_required(*roles):
    def decorator(f):
        @wraps(f)
        def wrapped(*args, **kwargs):
            if not current_user.is_authenticated or current_user.role not in roles:
                return "Access denied", 403
            return f(*args, **kwargs)
        return wrapped
    return decorator

ALERTS_FILE = os.environ.get("CIS_ALERTS_FILE", r"C:\\Users\\TECHWAVE\\AppData\\Local\\Temp\\cis_alerts.jsonl")
STATUS_FILE = os.environ.get("CIS_STATUS_FILE", r"C:\\Users\\TECHWAVE\\AppData\\Local\\Temp\\cis_status.json")


@app.route("/")
def index():
    if current_user.is_authenticated:
        return render_template_string("""
        <h1>CIS Monitoring Dashboard</h1>
        <p>Logged in as: {{user}}</p>
        <ul>
          <li><a href='/status'>System Status</a></li>
          <li><a href='/alerts'>Recent Alerts</a></li>
          {% if role == 'admin' %}<li><a href='/admin'>Admin Panel</a></li>{% endif %}
          <li><a href='/logout'>Logout</a></li>
        </ul>
        """, user=current_user.id, role=current_user.role)
    else:
        return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        if username in USERS and USERS[username]["password"] == password:
            user = User(username)
            login_user(user)
            return redirect(url_for("index"))
        return render_template_string("<h2>Login Failed</h2><a href='/login'>Try again</a>")
    return render_template_string('''
        <h2>Login</h2>
        <form method="post">
            Username: <input name="username"><br>
            Password: <input name="password" type="password"><br>
            <input type="submit" value="Login">
        </form>
    ''')

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))


@app.route("/status")
@login_required
def status():
    try:
        with open(STATUS_FILE, "r") as f:
            status = json.load(f)
    except Exception:
        status = {"error": "Status file not found."}
    return jsonify(status)




# Real-time alert streaming (SSE)
def alert_stream():
    last_len = 0
    while True:
        try:
            with open(ALERTS_FILE, "r") as f:
                lines = f.readlines()
        except Exception:
            lines = []
        if len(lines) > last_len:
            for line in lines[last_len:]:
                try:
                    alert = annotate_alert(json.loads(line))
                except Exception:
                    alert = json.loads(line) if line.strip() else {}
                yield f"data: {json.dumps(alert)}\n\n"
            last_len = len(lines)
        import time; time.sleep(2)

@app.route("/stream/alerts")
@login_required
def stream_alerts():
    return Response(alert_stream(), mimetype="text/event-stream")


import threading

ACK_FILE = os.path.join(os.path.dirname(__file__), "acknowledged_alerts.json")
def load_acknowledged():
    try:
        with open(ACK_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return []
def save_acknowledged(data):
    with open(ACK_FILE, "w") as f:
        json.dump(data, f)

@app.route("/acknowledge_alert", methods=["POST"])
@login_required
def acknowledge_alert():
    alert_id = request.form.get("alert_id")
    comment = request.form.get("comment", "")
    escalate = request.form.get("escalate", "false") == "true"
    mark_fp = request.form.get("false_positive", "false") == "true"
    ack = load_acknowledged()
    ack.append({"alert_id": alert_id, "user": current_user.id, "comment": comment, "escalate": escalate, "false_positive": mark_fp})
    save_acknowledged(ack)
    # Mark alert as false positive in alert file if requested
    if mark_fp:
        try:
            with open(ALERTS_FILE, "r", encoding="utf-8") as f:
                alerts = [json.loads(line) for line in f]
            for a in alerts:
                if str(a.get("timestamp")) == str(alert_id):
                    a["false_positive"] = True
            with open(ALERTS_FILE, "w", encoding="utf-8") as f:
                for a in alerts:
                    f.write(json.dumps(a) + "\n")
        except Exception:
            pass
    return ("", 204)

@app.route("/alerts")
@login_required
def alerts():
    return render_template_string('''
        <h2>Recent Alerts (Live)</h2>
        <ul id="alert-list"></ul>
        <script>
        var evtSource = new EventSource("/stream/alerts");
        evtSource.onmessage = function(e) {
            var alert = JSON.parse(e.data);
            var li = document.createElement("li");
            li.innerHTML = `<b>Process:</b> ${alert.process_name || ''} <b>PID:</b> ${alert.pid} <b>File:</b> ${alert.file_affected || ''}<br>
                <b>What happened:</b> ${alert.explanation ? alert.explanation.summary : (alert.actionable ? alert.actionable.what_happened : '')}<br>
                <b>Recommended:</b> ${alert.explanation ? alert.explanation.recommended_action : (alert.actionable ? alert.actionable.what_to_do : '')}<br>
                <b>Timestamp:</b> ${new Date(alert.timestamp*1000).toLocaleString()}<br>
                <b>False Positive:</b> ${alert.false_positive ? 'Yes' : 'No'}`;
            // Add acknowledge button
            var btn = document.createElement("button");
            btn.textContent = "Acknowledge / Mark FP";
            btn.onclick = function() {
                var comment = prompt("Add comment (optional):");
                var escalate = confirm("Escalate this alert?");
                var mark_fp = confirm("Mark as false positive?");
                var form = new FormData();
                form.append("alert_id", alert.timestamp || alert.pid || Math.random());
                form.append("comment", comment || "");
                form.append("escalate", escalate);
                form.append("false_positive", mark_fp);
                fetch("/acknowledge_alert", {method: "POST", body: form});
                btn.disabled = true;
            };
            li.appendChild(btn);
            document.getElementById("alert-list").appendChild(li);
        };
        </script>
        <a href='/'>Back</a>
    ''')


# Admin-only route example
@app.route("/admin")
@login_required
@roles_required("admin", "msp_admin")
def admin_panel():
    return render_template_string("<h2>Admin Panel</h2><p>Only admins and MSP admins can see this.</p><a href='/'>Back</a>")

# Example: Organization dashboard
@app.route("/org")
@login_required
def org_dashboard():
    return render_template_string(f"<h2>Org Dashboard</h2><p>Org: {current_user.org}</p><a href='/'>Back</a>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
