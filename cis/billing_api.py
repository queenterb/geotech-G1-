# API Routes for CIS Billing, Auth, and Account Management
from flask import Flask, Blueprint, request, jsonify, render_template_string
from functools import wraps
from datetime import datetime

try:
    from .auth import register_free_trial, create_session_token, validate_session_token, ValidationError, AuthenticationError
    from .license_check import check_license, LicenseError, TrialExpiredError, PlanLimitExceededError
    from .stripe_integration import StripePaymentProcessor, StripeError, get_plan_pricing
    from .feature_gating import FeatureGate
    from .database import get_user_subscription, upgrade_subscription, register_endpoint
except ImportError:
    from auth import register_free_trial, create_session_token, ValidationError, AuthenticationError
    from license_check import check_license, LicenseError, PlanLimitExceededError
    from stripe_integration import StripePaymentProcessor, StripeError, get_plan_pricing
    from feature_gating import FeatureGate
    from database import get_user_subscription, upgrade_subscription, register_endpoint

# Create Blueprint for billing routes
billing_bp = Blueprint('billing', __name__, url_prefix='/api/billing')

def require_license(f):
    """Decorator to require valid license."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        subscription_id = request.headers.get('X-Subscription-ID')
        
        if not subscription_id:
            return jsonify({'error': 'Missing subscription ID'}), 401
        
        try:
            license_info = check_license(int(subscription_id))
            request.license = license_info
            return f(*args, **kwargs)
        except LicenseError as e:
            return jsonify({'error': str(e)}), 403
    
    return decorated_function

# ============================================================================
# PUBLIC ROUTES (No authentication required)
# ============================================================================

@billing_bp.route('/signup', methods=['POST'])
def signup():
    """
    Register a new user for free trial.
    
    Request body:
    {
        "email": "user@example.com",
        "username": "username",
        "password": "SecurePass123",
        "organization": "Company Name"
    }
    """
    data = request.get_json() or {}
    
    try:
        result = register_free_trial(
            email=data.get('email'),
            username=data.get('username'),
            password=data.get('password'),
            organization=data.get('organization')
        )
        
        # Create session token
        session = create_session_token(
            result['user_id'],
            result['subscription_id']
        )
        
        return jsonify({
            'success': True,
            'message': result['message'],
            'user_id': result['user_id'],
            'subscription_id': result['subscription_id'],
            'email': result['email'],
            'plan': result['plan'],
            'trial_end_date': result['trial_end_date'],
            'session_token': session['token']
        }), 201
        
    except ValidationError as e:
        return jsonify({'error': str(e)}), 400
    except AuthenticationError as e:
        return jsonify({'error': str(e)}), 409

@billing_bp.route('/plans', methods=['GET'])
def get_plans():
    """Get available plans and pricing."""
    plans_info = {}
    
    for plan in ['free_trial', 'pro', 'enterprise']:
        pricing = get_plan_pricing(plan, endpoints=1)
        gate = FeatureGate(plan)
        summary = gate.get_plan_summary()
        
        plans_info[plan] = {
            'pricing': pricing,
            'summary': summary
        }
    
    return jsonify(plans_info), 200

@billing_bp.route('/features/comparison', methods=['GET'])
def feature_comparison():
    """Get feature comparison across plans."""
    from .feature_gating import get_feature_comparison
    
    comparison = get_feature_comparison()
    
    return jsonify({
        'comparison': comparison,
        'generated_at': datetime.now().isoformat()
    }), 200

# ============================================================================
# PROTECTED ROUTES (Require valid license)
# ============================================================================

@billing_bp.route('/subscription', methods=['GET'])
@require_license
def get_subscription():
    """Get current subscription info."""
    subscription_id = request.headers.get('X-Subscription-ID')
    
    subscription = get_user_subscription(int(subscription_id))
    
    if not subscription:
        return jsonify({'error': 'Subscription not found'}), 404
    
    gate = FeatureGate(subscription['plan'])
    
    return jsonify({
        'subscription_id': subscription_id,
        'plan': subscription['plan'],
        'status': subscription['status'],
        'is_trial': subscription['is_trial'],
        'created_at': subscription['created_at'],
        'summary': gate.get_plan_summary(),
        'license': request.license
    }), 200

@billing_bp.route('/upgrade', methods=['POST'])
@require_license
def upgrade_plan():
    """
    Upgrade from trial to paid plan.
    
    Request body:
    {
        "plan": "pro",
        "endpoints": 10,
        "payment_method": {
            "name": "Cardholder Name",
            "email": "user@example.com",
            "card_number": "4242424242424242",
            "exp_month": "12",
            "exp_year": "34",
            "cvc": "123"
        }
    }
    """
    data = request.get_json() or {}
    subscription_id = int(request.headers.get('X-Subscription-ID'))
    
    plan = data.get('plan')
    endpoints = data.get('endpoints', 1)
    payment_method = data.get('payment_method', {})
    
    if plan not in ['pro', 'enterprise']:
        return jsonify({'error': 'Invalid plan'}), 400
    
    if endpoints < 1:
        return jsonify({'error': 'Invalid endpoint count'}), 400
    
    if not payment_method.get('name') or not payment_method.get('email') or not payment_method.get('card_number'):
        return jsonify({'error': 'Payment details are required'}), 400
    
    try:
        processor = StripePaymentProcessor()
        subscription = get_user_subscription(subscription_id)
        
        customer_id = processor.create_customer(
            payment_method.get('email'),
            payment_method.get('name')
        )

        plan_pricing = get_plan_pricing(plan, endpoints)
        amount_cents = plan_pricing['total_price_cents']

        payment_intent = processor.create_payment_intent(
            customer_id,
            amount_cents,
            payment_method,
            description=f"Upgrade to {plan} plan"
        )

        if payment_intent.get('status') != 'succeeded':
            return jsonify({'error': 'Payment could not be completed'}), 400
        
        stripe_sub = processor.create_subscription(customer_id, plan, endpoints)
        
        result = upgrade_subscription(
            subscription_id,
            plan,
            stripe_sub['subscription_id']
        )
        
        return jsonify({
            'success': True,
            'message': f'Successfully upgraded to {plan} plan',
            'subscription_id': subscription_id,
            'plan': plan,
            'endpoints': endpoints,
            'stripe_subscription_id': stripe_sub['subscription_id'],
            'amount_per_month': stripe_sub['amount_cents'] / 100
        }), 200
        
    except StripeError as e:
        return jsonify({'error': f'Payment processing failed: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': f'Upgrade failed: {str(e)}'}), 400

@billing_bp.route('/endpoints', methods=['POST'])
@require_license
def register_new_endpoint():
    """
    Register a new endpoint for monitoring.
    
    Request body:
    {
        "endpoint_name": "Production Server 1",
        "endpoint_id": "srv-001"
    }
    """
    data = request.get_json() or {}
    subscription_id = int(request.headers.get('X-Subscription-ID'))
    
    endpoint_name = data.get('endpoint_name')
    endpoint_id = data.get('endpoint_id')
    
    if not endpoint_name or not endpoint_id:
        return jsonify({'error': 'Missing required fields'}), 400
    
    try:
        result = register_endpoint(subscription_id, endpoint_name, endpoint_id)
        
        return jsonify({
            'success': True,
            'message': 'Endpoint registered successfully',
            'endpoint_id': result['endpoint_id'],
            'endpoints_used': result['endpoints_used'],
            'endpoints_limit': result['endpoints_limit']
        }), 201
        
    except PlanLimitExceededError as e:
        return jsonify({'error': str(e)}), 402
    except ValueError as e:
        return jsonify({'error': str(e)}), 400

@billing_bp.route('/features', methods=['GET'])
@require_license
def get_available_features():
    """Get features available for current subscription."""
    subscription_id = int(request.headers.get('X-Subscription-ID'))
    subscription = get_user_subscription(subscription_id)
    
    gate = FeatureGate(subscription['plan'])
    
    return jsonify({
        'plan': subscription['plan'],
        'features': gate.get_available_features(),
        'summary': gate.get_plan_summary()
    }), 200

@billing_bp.route('/check-feature', methods=['GET'])
@require_license
def check_feature():
    """
    Check if subscription has access to a feature.
    
    Query params:
    - feature: Feature name to check
    """
    feature = request.args.get('feature')
    subscription_id = int(request.headers.get('X-Subscription-ID'))
    
    if not feature:
        return jsonify({'error': 'Missing feature parameter'}), 400
    
    subscription = get_user_subscription(subscription_id)
    gate = FeatureGate(subscription['plan'])
    
    result = gate.check_feature(feature)
    
    return jsonify(result), 200

# ============================================================================
# HTML PAGES
# ============================================================================

@billing_bp.route('/trial-signup', methods=['GET'])
def trial_signup_page():
    """Free trial signup page."""
    email = request.args.get('email', '')
    return render_template_string('''
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Start Free Trial - CIS</title>
        <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css">
        <style>
            body { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); min-height: 100vh; }
            .signup-container { max-width: 500px; margin: 5rem auto; background: white; padding: 2rem; border-radius: 10px; box-shadow: 0 10px 25px rgba(0,0,0,0.2); }
            .trial-badge { background: #28a745; color: white; padding: 0.5rem 1rem; border-radius: 5px; display: inline-block; margin-bottom: 1rem; }
        </style>
    </head>
    <body>
        <div class="signup-container">
            <h2>Start Your Free Trial</h2>
            <div class="trial-badge">14 Days • All Features</div>
            
            <form id="signupForm">
                <div class="mb-3">
                    <label class="form-label">Email Address</label>
                    <input type="email" class="form-control" id="email" name="email" value="{{ email|e }}" required>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Username</label>
                    <input type="text" class="form-control" id="username" name="username" required>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Password</label>
                    <input type="password" class="form-control" id="password" name="password" required>
                    <small class="text-muted">At least 8 characters, 1 uppercase, 1 lowercase, 1 number</small>
                </div>
                
                <div class="mb-3">
                    <label class="form-label">Organization (Optional)</label>
                    <input type="text" class="form-control" id="organization" name="organization">
                </div>
                
                <button type="submit" class="btn btn-primary w-100">Start Free Trial</button>
            </form>
            
            <div id="message" class="mt-3"></div>
        </div>
        
        <script>
            document.getElementById('signupForm').addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const data = {
                    email: document.getElementById('email').value,
                    username: document.getElementById('username').value,
                    password: document.getElementById('password').value,
                    organization: document.getElementById('organization').value
                };
                
                try {
                    const response = await fetch('/api/billing/signup', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(data)
                    });
                    
                    const result = await response.json();
                    const messageDiv = document.getElementById('message');
                    
                    if (result.success) {
                        messageDiv.innerHTML = `<div class="alert alert-success">Success! Your trial starts now. Subscription ID: ${result.subscription_id}</div>`;
                        localStorage.setItem('subscription_id', result.subscription_id);
                        localStorage.setItem('session_token', result.session_token);
                        setTimeout(() => window.location.href = '/dashboard', 2000);
                    } else {
                        messageDiv.innerHTML = `<div class="alert alert-danger">${result.error}</div>`;
                    }
                } catch (error) {
                    document.getElementById('message').innerHTML = `<div class="alert alert-danger">Error: ${error.message}</div>`;
                }
            });
        </script>
    </body>
    </html>
    '''), 200

# Register blueprint
def register_billing_routes(app: Flask):
    """Register billing routes with Flask app."""
    app.register_blueprint(billing_bp)
