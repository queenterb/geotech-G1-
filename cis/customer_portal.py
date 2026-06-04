# Customer Portal - Self-Service Features
from flask import Flask, render_template_string, jsonify, request
from functools import wraps
from datetime import datetime
import os

try:
    from .database import get_db_connection, get_user_subscription
    from .auth import verify_password, hash_password
    from .license_check import check_license
    from .usage_analytics import UsageTracker
    from .invoice_generator import InvoiceGenerator
except ImportError:
    from database import get_db_connection, get_user_subscription
    from auth import verify_password, hash_password
    from license_check import check_license
    from usage_analytics import UsageTracker
    from invoice_generator import InvoiceGenerator

# Create Blueprint for customer portal
customer_bp = None

def create_customer_portal():
    """Create Flask blueprint for customer portal."""
    from flask import Blueprint
    global customer_bp
    
    customer_bp = Blueprint('customer', __name__, url_prefix='/portal')
    
    # ============================================================================
    # DECORATORS
    # ============================================================================
    
    def portal_login_required(f):
        """Require portal login."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            if not current_user.is_authenticated:
                return render_template_string(PORTAL_LOGIN_TEMPLATE), 401
            return f(*args, **kwargs)
        return decorated_function
    
    # ============================================================================
    # ROUTES
    # ============================================================================
    
    @customer_bp.route('/dashboard')
    @portal_login_required
    def portal_dashboard():
        """Customer portal dashboard."""
        from flask_login import current_user
        
        subscription = get_user_subscription(current_user.id)
        if not subscription:
            return render_template_string(NO_SUBSCRIPTION_TEMPLATE)
        
        license_info = check_license(subscription['id'])
        usage_stats = UsageTracker.get_usage_stats(subscription['id'])
        
        return render_template_string(CUSTOMER_DASHBOARD_TEMPLATE,
                                     user=current_user,
                                     subscription=subscription,
                                     license=license_info,
                                     usage=usage_stats)
    
    @customer_bp.route('/usage')
    @portal_login_required
    def usage_dashboard():
        """Customer usage dashboard."""
        from flask_login import current_user
        
        subscription = get_user_subscription(current_user.id)
        if not subscription:
            return jsonify({'error': 'No subscription'}), 404
        
        daily_usage = UsageTracker.get_daily_usage(subscription['id'], days=30)
        top_features = UsageTracker.get_top_features(subscription['id'])
        
        return render_template_string(USAGE_DASHBOARD_TEMPLATE,
                                     user=current_user,
                                     daily_usage=daily_usage,
                                     top_features=top_features)
    
    @customer_bp.route('/invoices')
    @portal_login_required
    def view_invoices():
        """View billing history and invoices."""
        from flask_login import current_user
        
        subscription = get_user_subscription(current_user.id)
        if not subscription:
            return jsonify({'error': 'No subscription'}), 404
        
        invoices = InvoiceGenerator.list_invoices(subscription_id=subscription['id'])
        summary = InvoiceGenerator.get_invoice_summary()
        
        return render_template_string(INVOICES_TEMPLATE,
                                     user=current_user,
                                     invoices=invoices,
                                     summary=summary)
    
    @customer_bp.route('/invoices/<invoice_number>')
    @portal_login_required
    def view_invoice(invoice_number):
        """View specific invoice."""
        invoice = InvoiceGenerator.get_invoice(invoice_number)
        
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        html = InvoiceGenerator.generate_html_invoice(invoice_number)
        return html, 200, {'Content-Type': 'text/html'}
    
    @customer_bp.route('/invoices/<invoice_number>/download')
    @portal_login_required
    def download_invoice(invoice_number):
        """Download invoice as HTML/PDF."""
        invoice = InvoiceGenerator.get_invoice(invoice_number)
        
        if not invoice:
            return jsonify({'error': 'Invoice not found'}), 404
        
        html = InvoiceGenerator.generate_html_invoice(invoice_number)
        
        # In production, convert to PDF
        return html, 200, {
            'Content-Type': 'application/pdf',
            'Content-Disposition': f'attachment; filename="{invoice_number}.pdf"'
        }
    
    @customer_bp.route('/change-password', methods=['GET', 'POST'])
    @portal_login_required
    def change_password():
        """Change password."""
        from flask_login import current_user
        
        if request.method == 'POST':
            old_password = request.form.get('old_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if new_password != confirm_password:
                return render_template_string(CHANGE_PASSWORD_TEMPLATE,
                                             error='Passwords do not match'), 400
            
            # Verify old password
            conn = get_db_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT password_hash FROM users WHERE id = ?', (current_user.id,))
            user = cursor.fetchone()
            
            if not user or not verify_password(old_password, user['password_hash']):
                conn.close()
                return render_template_string(CHANGE_PASSWORD_TEMPLATE,
                                             error='Current password is incorrect'), 401
            
            # Update password
            new_hash = hash_password(new_password)
            cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?',
                         (new_hash, current_user.id))
            conn.commit()
            conn.close()
            
            return render_template_string(CHANGE_PASSWORD_TEMPLATE,
                                         success='Password changed successfully')
        
        return render_template_string(CHANGE_PASSWORD_TEMPLATE)
    
    @customer_bp.route('/account-settings')
    @portal_login_required
    def account_settings():
        """Account settings page."""
        from flask_login import current_user
        
        subscription = get_user_subscription(current_user.id)
        
        return render_template_string(ACCOUNT_SETTINGS_TEMPLATE,
                                     user=current_user,
                                     subscription=subscription)
    
    @customer_bp.route('/support')
    @portal_login_required
    def support():
        """Customer support page."""
        return render_template_string(SUPPORT_TEMPLATE)
    
    return customer_bp


# ============================================================================
# HTML TEMPLATES
# ============================================================================

PORTAL_LOGIN_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Portal Login - CIS</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
    <div style="max-width: 400px; margin: 5rem auto; background: white; padding: 2rem; border-radius: 10px;">
        <h2>Portal Login</h2>
        <form method="post" action="/login">
            <div class="mb-3">
                <label>Email</label>
                <input type="email" class="form-control" name="email" required>
            </div>
            <div class="mb-3">
                <label>Password</label>
                <input type="password" class="form-control" name="password" required>
            </div>
            <button type="submit" class="btn btn-primary w-100">Login</button>
        </form>
    </div>
</body>
</html>
'''

CUSTOMER_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Customer Portal - CIS</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; }
        .sidebar { background: white; min-height: 100vh; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
        .nav-link { color: #333; border-left: 3px solid transparent; }
        .nav-link.active { background: #f0f0f0; border-left-color: #667eea; }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-3 sidebar p-3">
                <h4>Portal Menu</h4>
                <nav class="nav flex-column">
                    <a class="nav-link active" href="/portal/dashboard">Dashboard</a>
                    <a class="nav-link" href="/portal/usage">Usage Analytics</a>
                    <a class="nav-link" href="/portal/invoices">Billing & Invoices</a>
                    <a class="nav-link" href="/portal/change-password">Change Password</a>
                    <a class="nav-link" href="/portal/account-settings">Account Settings</a>
                    <a class="nav-link" href="/portal/support">Support</a>
                    <a class="nav-link" href="/logout">Logout</a>
                </nav>
            </div>
            
            <div class="col-md-9 p-4">
                <h1>Customer Portal</h1>
                
                <div class="row mt-4">
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5>Current Plan</h5>
                                <p class="text-primary">{{ subscription.plan|upper }}</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5>Endpoints</h5>
                                <p class="text-primary">{{ usage.active_endpoints }} Active</p>
                            </div>
                        </div>
                    </div>
                    <div class="col-md-4">
                        <div class="card">
                            <div class="card-body">
                                <h5>Account Status</h5>
                                <p class="text-success">{{ subscription.status|capitalize }}</p>
                            </div>
                        </div>
                    </div>
                </div>
                
                <div class="card mt-4">
                    <div class="card-header">
                        <h5>Quick Links</h5>
                    </div>
                    <div class="card-body">
                        <a href="/billing" class="btn btn-outline-primary">Manage Subscription</a>
                        <a href="/alerts" class="btn btn-outline-primary">View Alerts</a>
                        <a href="/portal/invoices" class="btn btn-outline-primary">Download Invoices</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

USAGE_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Usage Analytics - CIS Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Usage Analytics</h1>
        
        <div class="row mt-4">
            <div class="col-md-8">
                <div class="card">
                    <div class="card-header">
                        <h5>Daily Usage (Last 30 Days)</h5>
                    </div>
                    <div class="card-body">
                        <div id="chart-placeholder">Loading chart...</div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-4">
                <div class="card">
                    <div class="card-header">
                        <h5>Top Features</h5>
                    </div>
                    <div class="card-body">
                        <ul class="list-unstyled">
                            {% for feature in top_features %}
                            <li class="mb-2">
                                <span>{{ feature.feature }}</span>
                                <span class="badge bg-primary">{{ feature.usage_count }}</span>
                            </li>
                            {% endfor %}
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

INVOICES_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Invoices - CIS Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Billing & Invoices</h1>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Invoice History</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    <thead>
                        <tr>
                            <th>Invoice #</th>
                            <th>Date</th>
                            <th>Amount</th>
                            <th>Status</th>
                            <th>Action</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for invoice in invoices %}
                        <tr>
                            <td>{{ invoice.invoice_number }}</td>
                            <td>{{ invoice.invoice_date }}</td>
                            <td>${{ invoice.amount_dollars }}</td>
                            <td><span class="badge bg-success">{{ invoice.payment_status }}</span></td>
                            <td>
                                <a href="/portal/invoices/{{ invoice.invoice_number }}" class="btn btn-sm btn-outline-primary">View</a>
                                <a href="/portal/invoices/{{ invoice.invoice_number }}/download" class="btn btn-sm btn-outline-secondary">Download</a>
                            </td>
                        </tr>
                        {% endfor %}
                    </tbody>
                </table>
            </div>
        </div>
    </div>
</body>
</html>
'''

CHANGE_PASSWORD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Change Password - CIS Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container" style="max-width: 500px; margin-top: 4rem;">
        <div class="card">
            <div class="card-header">
                <h5>Change Password</h5>
            </div>
            <div class="card-body">
                {% if error %}<div class="alert alert-danger">{{ error }}</div>{% endif %}
                {% if success %}<div class="alert alert-success">{{ success }}</div>{% endif %}
                
                <form method="post">
                    <div class="mb-3">
                        <label class="form-label">Current Password</label>
                        <input type="password" class="form-control" name="old_password" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">New Password</label>
                        <input type="password" class="form-control" name="new_password" required>
                    </div>
                    <div class="mb-3">
                        <label class="form-label">Confirm Password</label>
                        <input type="password" class="form-control" name="confirm_password" required>
                    </div>
                    <button type="submit" class="btn btn-primary">Change Password</button>
                </form>
            </div>
        </div>
    </div>
</body>
</html>
'''

ACCOUNT_SETTINGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Account Settings - CIS Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Account Settings</h1>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Account Information</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Email:</strong> {{ user.email }}</p>
                        <p><strong>Username:</strong> {{ user.username }}</p>
                        <p><strong>Account Created:</strong> 2026-06-02</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Actions</h5>
                    </div>
                    <div class="card-body">
                        <a href="/portal/change-password" class="btn btn-primary w-100 mb-2">Change Password</a>
                        <a href="/billing" class="btn btn-outline-primary w-100">Manage Billing</a>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

NO_SUBSCRIPTION_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Portal - CIS</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="alert alert-warning" role="alert">
            <h4>No Active Subscription</h4>
            <p>You need an active subscription to access the customer portal.</p>
            <a href="/billing" class="btn btn-primary">Start Free Trial</a>
        </div>
    </div>
</body>
</html>
'''

SUPPORT_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Support - CIS Portal</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Customer Support</h1>
        
        <div class="row mt-4">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Contact Us</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Email:</strong> support@cis-security.com</p>
                        <p><strong>Phone:</strong> +1 (555) 123-4567</p>
                        <p><strong>Hours:</strong> Monday-Friday, 9 AM - 5 PM EST</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Resources</h5>
                    </div>
                    <div class="card-body">
                        <ul>
                            <li><a href="https://docs.cis-security.com">Documentation</a></li>
                            <li><a href="https://cis-security.com/faq">FAQ</a></li>
                            <li><a href="https://status.cis-security.com">System Status</a></li>
                        </ul>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''
