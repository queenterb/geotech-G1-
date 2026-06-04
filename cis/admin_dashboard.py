# Admin Dashboard UI and Routes
from flask import Flask, render_template_string, jsonify, request
from functools import wraps
from datetime import datetime

try:
    from .admin_manager import AdminManager
    from .database import get_db_connection
except ImportError:
    from admin_manager import AdminManager
    from database import get_db_connection

# Create Blueprint for admin panel
admin_bp = None

def create_admin_dashboard():
    """Create Flask blueprint for admin dashboard."""
    from flask import Blueprint
    global admin_bp
    
    admin_bp = Blueprint('admin', __name__, url_prefix='/admin')
    
    # ============================================================================
    # DECORATORS
    # ============================================================================
    
    def admin_required(f):
        """Require admin role."""
        @wraps(f)
        def decorated_function(*args, **kwargs):
            from flask_login import current_user
            if not current_user.is_authenticated or not getattr(current_user, 'is_admin', False):
                return jsonify({'error': 'Admin access required'}), 403
            return f(*args, **kwargs)
        return decorated_function
    
    # ============================================================================
    # ROUTES
    # ============================================================================
    
    @admin_bp.route('/dashboard')
    @admin_required
    def dashboard():
        """Admin dashboard home."""
        stats = AdminManager.get_billing_stats()
        recent = AdminManager.get_recent_activity(limit=10)
        
        return render_template_string(ADMIN_DASHBOARD_TEMPLATE,
                                     stats=stats,
                                     recent=recent)
    
    @admin_bp.route('/api/stats')
    @admin_required
    def get_stats():
        """Get dashboard statistics (API)."""
        return jsonify(AdminManager.get_billing_stats())
    
    @admin_bp.route('/users')
    @admin_required
    def users_list():
        """List all users."""
        users = AdminManager.get_all_users()
        
        return render_template_string(USERS_LIST_TEMPLATE,
                                     users=users)
    
    @admin_bp.route('/api/users')
    @admin_required
    def get_users():
        """Get users list (API)."""
        users = AdminManager.get_all_users()
        return jsonify(users)
    
    @admin_bp.route('/user/<int:user_id>')
    @admin_required
    def user_detail(user_id):
        """View user details."""
        details = AdminManager.get_subscription_details(user_id)
        
        if not details:
            return render_template_string(NOT_FOUND_TEMPLATE), 404
        
        return render_template_string(USER_DETAIL_TEMPLATE,
                                     details=details,
                                     user_id=user_id)
    
    @admin_bp.route('/api/user/<int:user_id>')
    @admin_required
    def get_user_api(user_id):
        """Get user details (API)."""
        details = AdminManager.get_subscription_details(user_id)
        
        if not details:
            return jsonify({'error': 'User not found'}), 404
        
        return jsonify(details)
    
    @admin_bp.route('/user/<int:user_id>/disable', methods=['POST'])
    @admin_required
    def disable_user(user_id):
        """Disable user account."""
        result = AdminManager.disable_user(user_id)
        return jsonify(result)
    
    @admin_bp.route('/user/<int:user_id>/extend-trial', methods=['POST'])
    @admin_required
    def extend_trial(user_id):
        """Extend user trial."""
        days = int(request.form.get('days', 7))
        result = AdminManager.extend_trial(user_id, days)
        return jsonify(result)
    
    @admin_bp.route('/subscriptions')
    @admin_required
    def subscriptions_list():
        """List all subscriptions."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT s.*, u.email, u.username
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            ORDER BY s.created_at DESC
        ''')
        subs = cursor.fetchall()
        conn.close()
        
        return render_template_string(SUBSCRIPTIONS_LIST_TEMPLATE,
                                     subscriptions=subs)
    
    @admin_bp.route('/billing')
    @admin_required
    def billing_overview():
        """Billing overview."""
        stats = AdminManager.get_billing_stats()
        
        return render_template_string(BILLING_OVERVIEW_TEMPLATE,
                                     stats=stats)
    
    @admin_bp.route('/api/billing-stats')
    @admin_required
    def get_billing_stats():
        """Get billing statistics (API)."""
        return jsonify(AdminManager.get_billing_stats())
    
    @admin_bp.route('/refunds')
    @admin_required
    def refunds_list():
        """List refunds."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            SELECT p.id, u.email, u.username, p.amount_cents, p.created_at, p.status
            FROM payments p
            JOIN subscriptions s ON s.id = p.subscription_id
            JOIN users u ON u.id = s.user_id
            WHERE p.status = "refunded"
            ORDER BY p.created_at DESC
        ''')
        refunds = cursor.fetchall()
        conn.close()
        
        return render_template_string(REFUNDS_LIST_TEMPLATE,
                                     refunds=refunds)
    
    @admin_bp.route('/refund/<int:payment_id>', methods=['POST'])
    @admin_required
    def process_refund(payment_id):
        """Process refund."""
        reason = request.form.get('reason', 'Customer request')
        result = AdminManager.process_refund(payment_id, reason)
        return jsonify(result)
    
    @admin_bp.route('/audits')
    @admin_required
    def audit_logs():
        """View audit logs."""
        from .security_audit import AuditLogger
        
        summary = AuditLogger.get_audit_summary(days=30)
        
        return render_template_string(AUDIT_LOGS_TEMPLATE,
                                     summary=summary)
    
    @admin_bp.route('/settings')
    @admin_required
    def settings():
        """Admin settings."""
        return render_template_string(ADMIN_SETTINGS_TEMPLATE)
    
    return admin_bp


# ============================================================================
# HTML TEMPLATES
# ============================================================================

ADMIN_DASHBOARD_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Admin Dashboard - CIS</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
    <style>
        body { background: #f8f9fa; }
        .stat-card { 
            background: white;
            border-radius: 10px;
            padding: 20px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            margin-bottom: 20px;
        }
        .stat-number { 
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        .stat-label {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
        }
        .sidebar {
            background: #2c3e50;
            color: white;
            min-height: 100vh;
            padding: 20px;
        }
        .sidebar a {
            color: #ecf0f1;
            text-decoration: none;
            display: block;
            padding: 10px 0;
            border-bottom: 1px solid #34495e;
        }
        .sidebar a:hover {
            color: #667eea;
        }
    </style>
</head>
<body>
    <div class="container-fluid">
        <div class="row">
            <div class="col-md-2 sidebar">
                <h4 style="margin-bottom: 30px;">Admin Panel</h4>
                <a href="/admin/dashboard">Dashboard</a>
                <a href="/admin/users">Users</a>
                <a href="/admin/subscriptions">Subscriptions</a>
                <a href="/admin/billing">Billing</a>
                <a href="/admin/refunds">Refunds</a>
                <a href="/admin/audits">Audit Logs</a>
                <a href="/admin/settings">Settings</a>
                <a href="/logout">Logout</a>
            </div>
            
            <div class="col-md-10 p-4">
                <h1>Admin Dashboard</h1>
                
                <div class="row mt-4">
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number">{{ stats.total_users }}</div>
                            <div class="stat-label">Total Users</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number">${{ stats.total_revenue }}</div>
                            <div class="stat-label">Total Revenue</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number">{{ stats.conversion_rate }}%</div>
                            <div class="stat-label">Conversion Rate</div>
                        </div>
                    </div>
                    <div class="col-md-3">
                        <div class="stat-card">
                            <div class="stat-number">{{ stats.paid_users }}</div>
                            <div class="stat-label">Paid Users</div>
                        </div>
                    </div>
                </div>
                
                <div class="card mt-4">
                    <div class="card-header">
                        <h5>Recent Activity</h5>
                    </div>
                    <div class="card-body">
                        <table class="table">
                            <thead>
                                <tr>
                                    <th>User</th>
                                    <th>Action</th>
                                    <th>Date</th>
                                </tr>
                            </thead>
                            <tbody>
                                {% for item in recent %}
                                <tr>
                                    <td>{{ item.username }}</td>
                                    <td>{{ item.action }}</td>
                                    <td>{{ item.timestamp }}</td>
                                </tr>
                                {% endfor %}
                            </tbody>
                        </table>
                    </div>
                </div>
            </div>
        </div>
    </div>
</body>
</html>
'''

USERS_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Users - Admin Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Users Management</h1>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>All Users</h5>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>ID</th>
                            <th>Email</th>
                            <th>Username</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Actions</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for user in users %}
                        <tr>
                            <td>{{ user.id }}</td>
                            <td>{{ user.email }}</td>
                            <td>{{ user.username }}</td>
                            <td>
                                {% if user.is_active %}
                                    <span class="badge bg-success">Active</span>
                                {% else %}
                                    <span class="badge bg-danger">Disabled</span>
                                {% endif %}
                            </td>
                            <td>{{ user.created_at }}</td>
                            <td>
                                <a href="/admin/user/{{ user.id }}" class="btn btn-sm btn-outline-primary">View</a>
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

USER_DETAIL_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>User Details - Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>User Details</h1>
        
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>User Information</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Email:</strong> {{ details.email }}</p>
                        <p><strong>Username:</strong> {{ details.username }}</p>
                        <p><strong>Created:</strong> {{ details.created_at }}</p>
                        <p><strong>Status:</strong> {{ details.status }}</p>
                    </div>
                </div>
            </div>
            
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Subscription</h5>
                    </div>
                    <div class="card-body">
                        <p><strong>Plan:</strong> {{ details.plan|upper }}</p>
                        <p><strong>Status:</strong> {{ details.subscription_status }}</p>
                        <p><strong>Endpoints:</strong> {{ details.endpoint_count }}</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Actions</h5>
            </div>
            <div class="card-body">
                <form style="display: inline;">
                    <label>Extend Trial (days):</label>
                    <input type="number" name="days" value="7">
                    <button type="submit" class="btn btn-primary">Extend Trial</button>
                </form>
                <button class="btn btn-danger" onclick="if(confirm('Disable user?')) window.location='/admin/user/{{ user_id }}/disable'">Disable User</button>
            </div>
        </div>
    </div>
</body>
</html>
'''

BILLING_OVERVIEW_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Billing - Admin Dashboard</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Billing Overview</h1>
        
        <div class="row mt-4">
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-primary">${{ stats.total_revenue }}</h2>
                        <p class="text-muted">Total Revenue</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-success">{{ stats.paid_users }}</h2>
                        <p class="text-muted">Paid Subscriptions</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-info">{{ stats.trial_users }}</h2>
                        <p class="text-muted">Trial Users</p>
                    </div>
                </div>
            </div>
            <div class="col-md-3">
                <div class="card text-center">
                    <div class="card-body">
                        <h2 class="text-warning">{{ stats.conversion_rate }}%</h2>
                        <p class="text-muted">Conversion Rate</p>
                    </div>
                </div>
            </div>
        </div>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Plan Distribution</h5>
            </div>
            <div class="card-body">
                {% for plan, count in stats.plan_distribution.items() %}
                <p>{{ plan|upper }}: {{ count }} users</p>
                {% endfor %}
            </div>
        </div>
    </div>
</body>
</html>
'''

SUBSCRIPTIONS_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Subscriptions - Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>All Subscriptions</h1>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Subscription List</h5>
            </div>
            <div class="card-body">
                <table class="table table-hover">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Plan</th>
                            <th>Status</th>
                            <th>Created</th>
                            <th>Trial?</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for sub in subscriptions %}
                        <tr>
                            <td>{{ sub.email }}</td>
                            <td>{{ sub.plan|upper }}</td>
                            <td>{{ sub.status }}</td>
                            <td>{{ sub.created_at }}</td>
                            <td>{{ sub.is_trial }}</td>
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

REFUNDS_LIST_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Refunds - Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Refunds Management</h1>
        
        <div class="card mt-4">
            <div class="card-header">
                <h5>Refund History</h5>
            </div>
            <div class="card-body">
                <table class="table">
                    <thead>
                        <tr>
                            <th>User</th>
                            <th>Amount</th>
                            <th>Date</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {% for refund in refunds %}
                        <tr>
                            <td>{{ refund.email }}</td>
                            <td>${{ refund.amount_cents / 100 }}</td>
                            <td>{{ refund.created_at }}</td>
                            <td><span class="badge bg-warning">{{ refund.status }}</span></td>
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

AUDIT_LOGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Audit Logs - Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Audit Logs</h1>
        
        <div class="card">
            <div class="card-body">
                <p><strong>Period:</strong> Last 30 days</p>
                <p><strong>New Users:</strong> {{ summary.new_users }}</p>
                <p><strong>Refunds Processed:</strong> {{ summary.refunds_processed }}</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

ADMIN_SETTINGS_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Settings - Admin</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <h1>Admin Settings</h1>
        
        <div class="card">
            <div class="card-header">
                <h5>System Configuration</h5>
            </div>
            <div class="card-body">
                <p>Admin settings panel goes here.</p>
            </div>
        </div>
    </div>
</body>
</html>
'''

NOT_FOUND_TEMPLATE = '''
<!DOCTYPE html>
<html>
<head>
    <title>Not Found</title>
    <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
</head>
<body class="bg-light">
    <div class="container mt-4">
        <div class="alert alert-danger">
            <h4>Not Found</h4>
            <p>The requested resource was not found.</p>
        </div>
    </div>
</body>
</html>
'''
