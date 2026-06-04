# CIS Billing System - Quick Start Guide

## 🚀 Get Started in 5 Minutes

### Step 1: Initialize the Billing Database
```bash
cd c:\Users\TECHWAVE\Desktop\GEOTECH(G1)
python -c "from cis.database import init_database; init_database(); print('✓ Database initialized')"
```

### Step 2: Start the Dashboard Server
```bash
set CIS_DASHBOARD_SECRET=test_secret_key_12345
python -m cis.dashboard_new
```

**Output should show**:
```
* Running on http://127.0.0.1:5000
```

### Step 3: Create Your First Free Trial Account
**Option A - Use the Web Form:**
1. Open browser: http://localhost:5000/api/billing/trial-signup
2. Fill in:
   - Email: test@example.com
   - Username: testuser
   - Password: TestPass123
   - Organization: Test Company
3. Click "Start Free Trial"
4. You'll be redirected to the dashboard

**Option B - Use API curl:**
```bash
curl -X POST http://localhost:5000/api/billing/signup ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"test@example.com\",\"username\":\"testuser\",\"password\":\"TestPass123\",\"organization\":\"Test Company\"}"
```

**Response:**
```json
{
  "success": true,
  "subscription_id": 1,
  "plan": "free_trial",
  "trial_end_date": "2026-06-16T12:34:56.789012",
  "days_trial": 14,
  "message": "Free trial account created successfully!"
}
```

### Step 4: Login to Dashboard
1. Go to: http://localhost:5000/login
2. Enter:
   - Email: test@example.com
   - Password: TestPass123
3. Click "Login"
4. You'll see your dashboard with:
   - Current plan (Free Trial)
   - Features available
   - Days remaining
   - System status

### Step 5: Explore Billing Pages
- **Dashboard**: http://localhost:5000/dashboard
- **Billing**: http://localhost:5000/billing
- **Alerts**: http://localhost:5000/alerts
- **Logout**: http://localhost:5000/logout

---

## 📊 Test Scenarios

### Test 1: Check Trial Status
```python
from cis.license_check import check_license

license_info = check_license(subscription_id=1)
print(f"✓ Plan: {license_info['plan']}")
print(f"✓ Days Remaining: {license_info['days_remaining']}")
print(f"✓ Max Endpoints: {license_info['endpoints_limit']}")
```

### Test 2: Register an Endpoint
```python
from cis.database import register_endpoint

result = register_endpoint(
    subscription_id=1,
    endpoint_name='Production Server 1',
    endpoint_id='srv-001'
)
print(f"✓ Endpoints Used: {result['endpoints_used']}/{result['endpoints_limit']}")
```

### Test 3: Try Exceeding Endpoint Limit
```python
from cis.database import register_endpoint

# Free trial allows 5 endpoints
for i in range(1, 7):
    try:
        result = register_endpoint(
            subscription_id=1,
            endpoint_name=f'Server {i}',
            endpoint_id=f'srv-{i:03d}'
        )
        print(f"✓ Endpoint {i} registered")
    except ValueError as e:
        print(f"✗ Endpoint {i} failed: {e}")
```

### Test 4: Check Feature Access
```python
from cis.feature_gating import FeatureGate

gate = FeatureGate('free_trial')

features_to_check = [
    'basic_detection',
    'alerts',
    'api_access',
    'causal_trace'
]

for feature in features_to_check:
    has_access = gate.has_feature(feature)
    status = '✓' if has_access else '✗'
    print(f"{status} {feature}")
```

### Test 5: Compare Plans
```python
from cis.feature_gating import get_feature_comparison
import json

comparison = get_feature_comparison()
print(json.dumps(comparison, indent=2))
```

### Test 6: Upgrade to Pro Plan
```bash
curl -X POST http://localhost:5000/api/billing/upgrade ^
  -H "Content-Type: application/json" ^
  -H "X-Subscription-ID: 1" ^
  -d "{\"plan\":\"pro\",\"endpoints\":10}"
```

**Response:**
```json
{
  "success": true,
  "plan": "pro",
  "endpoints": 10,
  "amount_per_month": 60.0,
  "message": "Successfully upgraded to pro plan"
}
```

---

## 🔑 API Endpoints Reference

### Public Endpoints

#### Get Available Plans
```bash
curl http://localhost:5000/api/billing/plans
```

#### Feature Comparison
```bash
curl http://localhost:5000/api/billing/features/comparison
```

#### Signup
```bash
curl -X POST http://localhost:5000/api/billing/signup \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","username":"john","password":"Pass123"}'
```

### Protected Endpoints (Require Header)

#### Get Current Subscription
```bash
curl http://localhost:5000/api/billing/subscription \
  -H "X-Subscription-ID: 1"
```

#### Check Feature Access
```bash
curl "http://localhost:5000/api/billing/check-feature?feature=api_access" \
  -H "X-Subscription-ID: 1"
```

#### Get Available Features
```bash
curl http://localhost:5000/api/billing/features \
  -H "X-Subscription-ID: 1"
```

#### Register Endpoint
```bash
curl -X POST http://localhost:5000/api/billing/endpoints \
  -H "Content-Type: application/json" \
  -H "X-Subscription-ID: 1" \
  -d '{"endpoint_name":"Server 1","endpoint_id":"srv-001"}'
```

---

## 📱 User Flows

### Flow 1: Free Trial User
```
1. Visit http://localhost:5000/api/billing/trial-signup
2. Register with email/password
3. 14-day free trial created automatically
4. Access dashboard immediately
5. Limited to 5 endpoints and basic features
6. Can upgrade anytime
```

### Flow 2: Paid Plan User
```
1. Start with free trial
2. Click "Upgrade" in billing page
3. Select Pro or Enterprise plan
4. Enter payment info (Stripe in production)
5. Upgrade processed
6. Increased limits and features unlocked
7. Monthly billing starts
```

### Flow 3: Trial Expiration
```
1. User is in free trial
2. 3 days before expiration -> warning banner shows
3. On expiration date -> license check fails
4. User sees "Trial Expired" page
5. Must upgrade to continue using system
```

---

## 🗂️ File Structure
```
GEOTECH(G1)/
├── cis/
│   ├── database.py                    ← Database schema
│   ├── auth.py                        ← User authentication
│   ├── license_check.py               ← License validation
│   ├── feature_gating.py              ← Plan features
│   ├── stripe_integration.py          ← Payment processing
│   ├── billing_api.py                 ← REST API endpoints
│   ├── dashboard_new.py               ← Updated dashboard
│   ├── main_detector.py               ← Updated with license check
│   └── ...
├── BILLING_SYSTEM_IMPLEMENTATION.md   ← Full documentation
└── BILLING_QUICK_START.md             ← This file
```

---

## 🔧 Troubleshooting

### Database Error: "database is locked"
**Cause**: Multiple processes accessing SQLite simultaneously  
**Solution**: Close other instances and try again

### 404 Error on API endpoints
**Cause**: Route not registered  
**Solution**: Ensure `register_billing_routes(app)` is called in dashboard_new.py

### "No subscription ID found"
**Cause**: User not in database or subscription deleted  
**Solution**: Create new trial user or check database integrity

### Payment failures
**Cause**: Stripe keys not configured  
**Solution**: Currently uses mock Stripe. For production, add real keys to env

---

## ✅ Verification Checklist

After setup, verify:
- [ ] Database created at `~/.cis_billing.db`
- [ ] Can signup via `/api/billing/trial-signup`
- [ ] Can login with created account
- [ ] Dashboard shows correct plan and features
- [ ] Can register endpoints (up to limit)
- [ ] Cannot register more endpoints than plan allows
- [ ] Trial countdown warning appears at 3 days
- [ ] Can view pricing and plans
- [ ] Can initiate upgrade
- [ ] API endpoints return correct data with subscription ID header

---

## 📞 Common Questions

**Q: How long is the free trial?**  
A: 14 days with all features

**Q: How many endpoints can I monitor?**  
A: Free Trial: 5, Pro: 50, Enterprise: Unlimited

**Q: Can I upgrade mid-trial?**  
A: Yes, anytime from the billing page

**Q: What happens after trial expires?**  
A: System stops working until upgraded

**Q: Can I extend my trial?**  
A: Contact support for 14-day extension (contact support@cis-security.com)

**Q: Is data deleted after trial expires?**  
A: No, data is preserved. Purchase plan to restore access.

---

## 🚀 Next Steps

1. **Test the flows** above
2. **Check the main_detector.py integration** - Add `subscription_id` to config
3. **Review the database schema** - See `cis/database.py`
4. **Configure Stripe for production** - Replace mock with real keys
5. **Deploy to production** - Follow deployment guide

---

**Ready to test?** Start with Step 1 above! 🎉

For detailed documentation, see: [BILLING_SYSTEM_IMPLEMENTATION.md](BILLING_SYSTEM_IMPLEMENTATION.md)
