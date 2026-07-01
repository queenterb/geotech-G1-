from flask import Flask, render_template_string, jsonify, request, redirect, url_for
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask import Response
from functools import wraps
import json
import os
import time

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
          <li><a href='/billing-summary'>Billing Summary</a></li>
          <li><a href='/upgrade' style="color: green; font-weight: bold;">🚀 Upgrade to Pro</a></li>
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
        time.sleep(2)

@app.route("/stream/alerts")
@login_required
def stream_alerts():
    return Response(alert_stream(), mimetype="text/event-stream")



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


@app.route("/upgrade")
@login_required
def upgrade_page():
    """Pro plan upgrade page with payment form."""
    upgrade_template = """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Upgrade to Pro - CIS</title>
        <style>
            body { font-family: Arial, sans-serif; max-width: 600px; margin: 50px auto; }
            .upgrade-card { background: #f5f5f5; padding: 20px; border-radius: 8px; }
            .plan-info { background: #e8f4f8; padding: 15px; margin: 20px 0; border-left: 4px solid #0066cc; }
            input { width: 100%; padding: 8px; margin: 8px 0; border: 1px solid #ccc; border-radius: 4px; box-sizing: border-box; }
            button { background: #0066cc; color: white; padding: 12px 20px; border: none; border-radius: 4px; cursor: pointer; width: 100%; font-size: 16px; }
            button:hover { background: #0052a3; }
            .error { color: red; margin: 10px 0; }
            .success { color: green; margin: 10px 0; }
            .pricing { display: flex; gap: 20px; margin: 20px 0; }
            .price-option { flex: 1; padding: 15px; border: 1px solid #ddd; border-radius: 4px; text-align: center; cursor: pointer; }
            .price-option.selected { background: #0066cc; color: white; }
        </style>
    </head>
    <body>
        <h1>🚀 Upgrade to Pro</h1>
        <div class="upgrade-card">
            <div class="plan-info">
                <h3>Choose Your Plan</h3>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
                    <div class="price-option selected" id="proOption" data-plan="pro">
                        <strong>Pro</strong><br>
                        $6 / endpoint / month<br>
                        $60 / endpoint / year<br>
                        Up to 50 endpoints
                    </div>
                    <div class="price-option" id="enterpriseOption" data-plan="enterprise">
                        <strong>Enterprise</strong><br>
                        $12 / endpoint / month<br>
                        $120 / endpoint / year<br>
                        Unlimited endpoints
                    </div>
                </div>
                <div style="display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 20px;">
                    <label style="flex: 1; cursor: pointer;"><input type="radio" name="billingPeriod" value="monthly" checked> Monthly</label>
                    <label style="flex: 1; cursor: pointer;"><input type="radio" name="billingPeriod" value="yearly"> Yearly</label>
                </div>
                <p><strong id="selectedPrice">Price: $299/month</strong></p>
            </div>
            
            <form id="upgradeForm">
                <h3>Payment Details</h3>
                
                <label>Full Name</label>
                <input type="text" id="cardName" placeholder="John Doe" required>
                
                <label>Email</label>
                <input type="email" id="cardEmail" placeholder="john@example.com" required>
                
                <label>Endpoints</label>
                <input type="number" id="endpoints" value="10" min="1" required>
                
                <label>Card Number</label>
                <input type="text" id="cardNumber" placeholder="4242 4242 4242 4242" maxlength="19" required>
                
                <div style="display: flex; gap: 10px;">
                    <div style="flex: 1;">
                        <label>Expiry (MM/YY)</label>
                        <input type="text" id="cardExpiry" placeholder="12/34" maxlength="5" required>
                    </div>
                    <div style="flex: 1;">
                        <label>CVC</label>
                        <input type="text" id="cardCVC" placeholder="123" maxlength="4" required>
                    </div>
                </div>
                
                <div id="message"></div>
                
                <button type="submit">Upgrade Now</button>
                <a href="/" style="display: block; text-align: center; margin-top: 10px;">← Back to Dashboard</a>
            </form>
        </div>
        
        <script>
            document.getElementById('upgradeForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const messageDiv = document.getElementById('message');
                messageDiv.innerHTML = '<p style="color: blue;">Processing payment...</p>';
                
                // Format card data
                const [month, year] = document.getElementById('cardExpiry').value.split('/');
                const cardNumber = document.getElementById('cardNumber').value.replace(/\\s/g, '');
                
                try {
                    const response = await fetch('/api/billing/upgrade', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Subscription-ID': '1' // Default admin subscription
                        },
                        body: JSON.stringify({
                            plan: 'pro',
                            endpoints: 10,
                            payment_method: {
                                name: document.getElementById('cardName').value,
                                email: document.getElementById('cardEmail').value,
                                card_number: cardNumber,
                                exp_month: month,
                                exp_year: year,
                                cvc: document.getElementById('cardCVC').value
                            }
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = `<p class="success">✓ Upgrade successful! Welcome to Pro. Redirecting...</p>`;
                        setTimeout(() => window.location.href = '/', 2000);
                    } else {
                        messageDiv.innerHTML = `<p class="error">✗ ${data.error || 'Payment failed'}</p>`;
                    }
                } catch (error) {
                    messageDiv.innerHTML = `<p class="error">✗ ${error.message}</p>`;
                }
            });
            
            // Format card number input
            document.getElementById('cardNumber').addEventListener('input', (e) => {
                let value = e.target.value.replace(/\\s/g, '');
                let formatted = value.match(/.{1,4}/g)?.join(' ') || value;
                e.target.value = formatted;
            });

            const planOptions = document.querySelectorAll('.price-option');
            const billingRadios = document.querySelectorAll('input[name="billingPeriod"]');
            const selectedPrice = document.getElementById('selectedPrice');
            const endpointsInput = document.getElementById('endpoints');
            let selectedPlan = 'pro';
            let selectedBilling = 'monthly';

            function updateSelection() {
                planOptions.forEach((option) => {
                    option.classList.toggle('selected', option.dataset.plan === selectedPlan);
                });
                let priceText = '$299/month';
                if (selectedPlan === 'pro') {
                    priceText = selectedBilling === 'monthly' ? '$6 / endpoint / month' : '$60 / endpoint / year';
                    endpointsInput.value = 10;
                } else {
                    priceText = selectedBilling === 'monthly' ? '$12 / endpoint / month' : '$120 / endpoint / year';
                    endpointsInput.value = 1;
                }
                selectedPrice.textContent = `Price: ${priceText}`;
            }

            planOptions.forEach((option) => {
                option.addEventListener('click', () => {
                    selectedPlan = option.dataset.plan;
                    updateSelection();
                });
            });

            billingRadios.forEach((radio) => {
                radio.addEventListener('change', () => {
                    selectedBilling = document.querySelector('input[name="billingPeriod"]:checked').value;
                    updateSelection();
                });
            });

            updateSelection();
            
            document.getElementById('upgradeForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const messageDiv = document.getElementById('message');
                messageDiv.innerHTML = '<p style="color: blue;">Processing payment...</p>';
                
                const [month, year] = document.getElementById('cardExpiry').value.split('/');
                const cardNumber = document.getElementById('cardNumber').value.replace(/\\s/g, '');
                
                try {
                    const response = await fetch('/api/billing/upgrade', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'X-Subscription-ID': '1' // Default admin subscription
                        },
                        body: JSON.stringify({
                            plan: selectedPlan,
                            billing_period: selectedBilling,
                            endpoints: parseInt(document.getElementById('endpoints').value, 10),
                            payment_method: {
                                name: document.getElementById('cardName').value,
                                email: document.getElementById('cardEmail').value,
                                card_number: cardNumber,
                                exp_month: month,
                                exp_year: year,
                                cvc: document.getElementById('cardCVC').value
                            }
                        })
                    });
                    
                    const data = await response.json();
                    
                    if (response.ok) {
                        messageDiv.innerHTML = `<p class="success">✓ Upgrade successful! Welcome to ${selectedPlan.toUpperCase()} (${selectedBilling}). Redirecting...</p>`;
                        setTimeout(() => window.location.href = '/', 2000);
                    } else {
                        messageDiv.innerHTML = `<p class="error">✗ ${data.error || 'Payment failed'}</p>`;
                    }
                } catch (error) {
                    messageDiv.innerHTML = `<p class="error">✗ ${error.message}</p>`;
                }
            });
        </script>
    </body>
    </html>
    """
    return render_template_string(upgrade_template)

# Admin-only route example
@app.route("/admin")
@login_required
@roles_required("admin", "msp_admin")
def admin_panel():
    return render_template_string("<h2>Admin Panel</h2><p>Only admins and MSP admins can see this.</p><a href='/'>Back</a>")

@app.route("/billing-summary")
@login_required
def billing_summary():
    return render_template_string('''
        <!DOCTYPE html>
        <html>
        <head>
            <title>Billing Summary</title>
            <style>
                body { font-family: Arial, sans-serif; max-width: 700px; margin: 40px auto; }
                .card { background: #f8f9fa; border: 1px solid #ddd; border-radius: 8px; padding: 20px; }
                .label { color: #555; margin-bottom: 8px; display: block; }
                .value { font-size: 1.1rem; margin-bottom: 16px; }
                .status { font-weight: bold; }
                .error { color: red; }
                .loading { color: #0066cc; }
            </style>
        </head>
        <body>
            <h2>Billing Summary</h2>
            <div class="card">
                <div id="billingContent">
                    <p class="loading">Loading billing details...</p>
                </div>
                <div id="billingError" class="error"></div>
                <a href='/upgrade'>Change plan or billing</a><br>
                <a href='/'>Back to Dashboard</a>
            </div>
            <script>
                async function loadBilling() {
                    const content = document.getElementById('billingContent');
                    const error = document.getElementById('billingError');
                    try {
                        const resp = await fetch('/api/billing/subscription', {
                            headers: {
                                'Content-Type': 'application/json',
                                'X-Subscription-ID': '1'
                            }
                        });
                        const data = await resp.json();
                        if (!resp.ok) {
                            throw new Error(data.error || 'Failed to load subscription');
                        }
                        const nextPaymentDate = data.subscription && data.subscription.subscription_end ? new Date(data.subscription.subscription_end).toLocaleDateString() : 'N/A';
                        content.innerHTML = `
                            <span class="label">Plan</span><div class="value">${data.plan || 'N/A'}</div>
                            <span class="label">Billing Cycle</span><div class="value">${data.billing_period || 'monthly'}</div>
                            <span class="label">Next Payment Date</span><div class="value">${nextPaymentDate}</div>
                            <span class="label">Endpoints</span><div class="value">${data.endpoints || 'N/A'}</div>
                            <span class="label">Status</span><div class="value status">${data.status || 'N/A'}</div>
                            <span class="label">Subscription ID</span><div class="value">${data.subscription_id || 'N/A'}</div>
                        `;
                    } catch (e) {
                        content.innerHTML = '';
                        error.textContent = e.message;
                    }
                }
                loadBilling();
            </script>
        </body>
        </html>
    ''')

# Example: Organization dashboard
@app.route("/org")
@login_required
def org_dashboard():
    return render_template_string(f"<h2>Org Dashboard</h2><p>Org: {current_user.org}</p><a href='/'>Back</a>")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
