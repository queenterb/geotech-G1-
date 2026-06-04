# CIS Billing System - Complete Implementation Guide

## Overview

A comprehensive billing and licensing system has been implemented for CIS with the following features:

- ✅ **Free Trial Management** (14-day trials with automatic expiration)
- ✅ **User Registration & Authentication** (password hashing, validation)
- ✅ **License Validation** (per-subscription license checking)
- ✅ **Feature Gating** (plan-based feature access control)
- ✅ **Endpoint Management** (plan-based endpoint limits)
- ✅ **Payment Integration** (Stripe integration ready)
- ✅ **Dashboard Integration** (billing pages, subscription info)
- ✅ **Database Schema** (SQLite with users, subscriptions, endpoints, payments)

---

## New Files Created

### 1. `cis/database.py` - Database Schema & Management
**Purpose**: SQLite database schema and user/subscription management

**Key Functions**:
- `init_database()` - Initialize database schema
- `create_trial_user(email, username, password_hash)` - Create free trial user
- `get_user_subscription(user_id)` - Get active subscription
- `check_trial_status(subscription_id)` - Check trial expiration
- `register_endpoint(subscription_id, endpoint_name, endpoint_id)` - Register endpoint with plan limits
- `upgrade_subscription(subscription_id, new_plan)` - Upgrade from trial to paid plan

**Database Tables**:
- `users` - User accounts
- `subscriptions` - User subscriptions and plans
- `endpoints` - Registered endpoints per subscription
- `alerts` - Alert records
- `feature_usage` - Feature usage tracking
- `payments` - Payment records

---

### 2. `cis/auth.py` - Authentication & User Management
**Purpose**: User registration, password hashing, session management

**Key Functions**:
- `hash_password(password)` - PBKDF2 password hashing
- `verify_password(password, hash)` - Verify password
- `validate_email(email)` - Email format validation
- `validate_password(password)` - Password strength validation
- `validate_username(username)` - Username validation
- `register_free_trial(email, username, password)` - Register free trial
- `create_session_token()` - Create auth token

**Validation Rules**:
- Email: Standard email format
- Username: 3-30 chars, alphanumeric + hyphens/underscores
- Password: 8+ chars, 1 uppercase, 1 lowercase, 1 digit

---

### 3. `cis/license_check.py` - License & Trial Management
**Purpose**: License validation, trial checking, feature access

**Key Functions**:
- `check_license(subscription_id)` - Validate license and return info
- `save_license_file(user_id, subscription_id, plan)` - Cache license locally
- `validate_endpoint_registration()` - Check endpoint limits
- `check_feature_access(subscription_id, feature)` - Check feature availability

**Exceptions**:
- `LicenseError` - General license error
- `TrialExpiredError` - Trial has expired
- `PlanLimitExceededError` - Plan limits exceeded

---

### 4. `cis/feature_gating.py` - Feature Access Control
**Purpose**: Plan-based feature gating and plan management

**Key Classes**:
- `FeatureGate(plan)` - Feature access controller per plan

**Plan Features**:

| Feature | Free Trial | Pro | Enterprise |
|---------|-----------|-----|------------|
| Endpoints Limit | 5 | 50 | Unlimited |
| Data Retention | 7 days | 30 days | 90 days |
| API Calls/Day | 1,000 | 100,000 | Unlimited |
| Basic Detection | ✓ | ✓ | ✓ |
| Alerts | ✓ | ✓ | ✓ |
| Causal Trace | ✗ | ✓ | ✓ |
| API Access | ✗ | ✓ | ✓ |
| Advanced Analytics | ✗ | ✓ | ✓ |
| Custom Rules | ✗ | ✗ | ✓ |
| SLA Support | ✗ | ✗ | ✓ |

---

### 5. `cis/stripe_integration.py` - Payment Processing
**Purpose**: Stripe payment gateway integration

**Key Classes**:
- `StripePaymentProcessor` - Stripe operations

**Key Functions**:
- `create_customer(email, name)` - Create Stripe customer
- `create_subscription(customer_id, plan, endpoints)` - Create subscription
- `create_payment_intent()` - Create payment
- `get_plan_pricing(plan, endpoints)` - Get pricing info

**Plans & Pricing**:
- **Pro**: $6.00/endpoint/month
- **Enterprise**: $12.00/endpoint/month

---

### 6. `cis/billing_api.py` - REST API Endpoints
**Purpose**: Billing API endpoints for signup, subscription, upgrades

**Public Endpoints** (No auth required):

```
POST /api/billing/signup
  - Register free trial account
  - Request: {email, username, password, organization}
  - Response: {subscription_id, session_token, trial_end_date}

GET /api/billing/plans
  - Get available plans and pricing

GET /api/billing/features/comparison
  - Compare features across plans

GET /api/billing/trial-signup
  - Free trial signup page
```

**Protected Endpoints** (Requires subscription ID header):

```
GET /api/billing/subscription
  - Get current subscription info
  - Header: X-Subscription-ID: <id>

POST /api/billing/upgrade
  - Upgrade plan
  - Header: X-Subscription-ID: <id>
  - Request: {plan, endpoints, payment_method_id}

POST /api/billing/endpoints
  - Register endpoint
  - Header: X-Subscription-ID: <id>
  - Request: {endpoint_name, endpoint_id}

GET /api/billing/features
  - Get available features
  - Header: X-Subscription-ID: <id>

GET /api/billing/check-feature?feature=<name>
  - Check feature availability
  - Header: X-Subscription-ID: <id>
```

---

### 7. `cis/dashboard_new.py` - Updated Dashboard
**Purpose**: New dashboard with full billing integration

**Routes**:
- `/` - Home (redirects to dashboard)
- `/login` - Login page
- `/logout` - Logout
- `/dashboard` - Main dashboard with license info
- `/billing` - Billing & plan management
- `/alerts` - Alerts page (license required)
- `/status` - System status (license required)
- `/trial-expired` - Trial expiration notice

**Features**:
- User authentication
- License validation
- Plan display with current plan highlight
- Trial countdown warning
- System status & alerts
- Responsive Bootstrap UI

---

## Updated Files

### `cis/main_detector.py`
**Changes**:
- Added license check imports
- License validation at startup
- Trial expiration enforcement
- Feature gate initialization
- Graceful shutdown on license failure

**Usage**:
```python
# Set subscription ID via config or environment
config['subscription_id'] = 123
# OR
os.environ['CIS_SUBSCRIPTION_ID'] = '123'

# Start detector (will validate license)
detector = CISMain(config)
```

---

## Setup Instructions

### 1. Initialize Database
```python
from cis.database import init_database
init_database()  # Creates ~/.cis_billing.db
```

### 2. Configure Flask App
```python
from cis.dashboard_new import app

# Set environment variables
os.environ['CIS_DASHBOARD_SECRET'] = 'your-secure-secret'
os.environ['STRIPE_API_KEY'] = 'sk_test_...'  # Optional, for production

# Run app
app.run(host='0.0.0.0', port=5000)
```

### 3. Register User for Free Trial
**Option A - Via API**:
```bash
curl -X POST http://localhost:5000/api/billing/signup \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "username": "john_doe",
    "password": "SecurePass123",
    "organization": "Acme Corp"
  }'
```

**Option B - Via Web Form**:
- Navigate to `/api/billing/trial-signup`
- Fill in the form
- Submit to create account

### 4. Login to Dashboard
- Navigate to `/login`
- Enter email and password
- Redirected to dashboard with license info

---

## Integration with Main Detector

### Running with License Check
```python
import os
from cis.main_detector import CISMain

os.environ['CIS_SUBSCRIPTION_ID'] = '1'  # User's subscription ID

config = {
    'subscription_id': 1,
    'ebpf_socket_path': '/tmp/cis_ebpf_events.sock',
    # ... other config
}

detector = CISMain(config)
# License is validated at init
# Gracefully exits if license invalid or trial expired
```

### Checking Feature Access
```python
from cis.license_check import check_feature_access

if check_feature_access(subscription_id=1, feature_name='api_access'):
    # Feature is available
    pass
else:
    # Feature not available for this plan
    pass
```

### Registering Endpoints
```python
from cis.database import register_endpoint

try:
    result = register_endpoint(
        subscription_id=1,
        endpoint_name='Production Server 1',
        endpoint_id='srv-001'
    )
    print(f"Registered! {result['endpoints_used']}/{result['endpoints_limit']} endpoints used")
except ValueError as e:
    print(f"Registration failed: {e}")  # Might be plan limit exceeded
```

---

## Plan Upgrades

### Upgrade from Trial to Paid Plan
```bash
curl -X POST http://localhost:5000/api/billing/upgrade \
  -H "Content-Type: application/json" \
  -H "X-Subscription-ID: 1" \
  -d '{
    "plan": "pro",
    "endpoints": 10
  }'
```

---

## Environment Variables

```bash
# Dashboard
CIS_DASHBOARD_SECRET=your-secret-key

# Database
CIS_DB_PATH=~/.cis_billing.db

# Stripe (Optional, for production)
STRIPE_API_KEY=sk_live_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Main Detector
CIS_SUBSCRIPTION_ID=1

# Logging
CIS_ALERTS_FILE=/tmp/cis_alerts.jsonl
CIS_STATUS_FILE=/tmp/cis_status.json
```

---

## Testing Trial Features

### Create Test Trial User
```python
from cis.database import init_database, create_trial_user

init_database()
user = create_trial_user(
    email='test@example.com',
    username='testuser',
    password_hash=hash_password('TestPass123'),
    organization='Test Corp'
)
print(f"User ID: {user['user_id']}")
print(f"Subscription ID: {user['subscription_id']}")
print(f"Trial Expires: {user['trial_end_date']}")
```

### Check Trial Status
```python
from cis.license_check import check_license

license_info = check_license(subscription_id=1)
print(f"Plan: {license_info['plan']}")
print(f"Days Remaining: {license_info['days_remaining']}")
print(f"Endpoints Limit: {license_info['endpoints_limit']}")
```

### Test Feature Gating
```python
from cis.feature_gating import FeatureGate

gate = FeatureGate('free_trial')
print(f"Has API Access: {gate.has_feature('api_access')}")  # False
print(f"Has Basic Detection: {gate.has_feature('basic_detection')}")  # True

gate_pro = FeatureGate('pro')
print(f"Pro Has API Access: {gate_pro.has_feature('api_access')}")  # True
```

---

## Error Handling

### Trial Expired
```python
from cis.license_check import TrialExpiredError, check_license

try:
    check_license(subscription_id=999)
except TrialExpiredError as e:
    print(f"Trial expired: {e}")
    # Redirect user to upgrade page
```

### Plan Limit Exceeded
```python
from cis.database import register_endpoint
from cis.license_check import PlanLimitExceededError

try:
    register_endpoint(subscription_id=1, endpoint_name='new', endpoint_id='ep-99')
except PlanLimitExceededError as e:
    print(f"Endpoint limit reached: {e}")
    # Show upgrade prompt
```

---

## Security Notes

1. **Password Hashing**: Uses PBKDF2 with 100,000 iterations
2. **License Files**: Stored in `~/.cis_license.json` (user home directory)
3. **Database**: SQLite at `~/.cis_billing.db` - should be backed up
4. **API Keys**: Never commit Stripe keys to repo
5. **HTTPS**: Use HTTPS in production for all API endpoints
6. **Session Tokens**: Implement session expiration (24hrs default)

---

## Production Checklist

- [ ] Replace Stripe mock with real Stripe API (currently mocked)
- [ ] Set secure `CIS_DASHBOARD_SECRET` (use `secrets` module)
- [ ] Configure HTTPS/TLS certificates
- [ ] Set up database backups
- [ ] Configure email for password reset (optional)
- [ ] Set up payment webhooks for Stripe
- [ ] Configure SMTP for trial expiration notifications
- [ ] Test payment processing end-to-end
- [ ] Implement rate limiting on API endpoints
- [ ] Set up audit logging for billing operations
- [ ] Configure database encryption at rest

---

## Troubleshooting

### Issue: "No subscription ID found"
**Solution**: Set `CIS_SUBSCRIPTION_ID` environment variable or pass in config

### Issue: "Trial expired" error on startup
**Solution**: Check trial_end_date in database, upgrade plan via billing page

### Issue: "Endpoint limit reached"
**Solution**: User needs to upgrade plan for more endpoints

### Issue: Database locked
**Solution**: SQLite is single-writer, ensure only one detector instance running

---

## Next Steps

1. **Deploy to Production**:
   - Set up Stripe live keys
   - Configure HTTPS
   - Set up database backups

2. **Configure Notifications**:
   - Trial expiration emails
   - Subscription renewal reminders
   - Payment failure alerts

3. **Analytics**:
   - Track trial conversions
   - Monitor plan upgrades
   - Payment success rates

4. **Customer Support**:
   - Upgrade assistance
   - Trial extension requests
   - Payment troubleshooting

---

## Contact & Support

For issues or questions:
- Email: support@cis-security.com
- Dashboard: https://cis-security.com/support
- Docs: https://docs.cis-security.com

---

**Implementation Date**: 2026-06-02  
**Version**: 2.0 (Billing System)  
**Status**: ✅ Complete & Ready for Testing
