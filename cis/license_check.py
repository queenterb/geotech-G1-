# Comprehensive Licensing and Trial Management for CIS
import os
import json
from datetime import datetime
from typing import Dict, Optional

try:
    from .database import (
        get_user_subscription, 
        check_trial_status, 
        get_subscription_by_id,
        register_endpoint
    )
except ImportError:
    from database import (
        check_trial_status, 
        get_subscription_by_id,
        register_endpoint
    )

LICENSE_FILE = os.path.expanduser("~/.cis_license.json")
LICENSE_SERVER = "https://api.cis-security.com/license/check"

class LicenseError(Exception):
    """Raised when license validation fails."""
    pass

class TrialExpiredError(LicenseError):
    """Raised when free trial has expired."""
    pass

class PlanLimitExceededError(LicenseError):
    """Raised when plan limits are exceeded."""
    pass

def save_license_file(user_id: int, subscription_id: int, plan: str) -> None:
    """Save license information locally."""
    license_data = {
        "user_id": user_id,
        "subscription_id": subscription_id,
        "plan": plan,
        "saved_at": datetime.now().isoformat(),
        "version": "2.0"
    }
    
    with open(LICENSE_FILE, "w") as f:
        json.dump(license_data, f, indent=2)

def load_license_file() -> Optional[Dict]:
    """Load license from local file."""
    if not os.path.exists(LICENSE_FILE):
        return None
    
    try:
        with open(LICENSE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return None

def check_license(subscription_id: int = None) -> Dict:
    """
    Check license status with database validation.
    
    Returns:
        Dict with license info including:
        - valid (bool): Whether license is valid
        - plan (str): Plan type (free_trial, pro, enterprise)
        - days_remaining (int): Days left for trial (if applicable)
        - message (str): Status message
        - endpoints_limit (int): Max endpoints allowed
    """
    
    # Try to load cached license file first
    cached_license = load_license_file()
    
    if cached_license and subscription_id is None:
        subscription_id = cached_license.get("subscription_id")
    
    if subscription_id is None:
        raise LicenseError("No subscription ID provided and no cached license found. Please register for a free trial.")
    
    # Check subscription in database
    subscription = get_subscription_by_id(subscription_id)
    
    if not subscription:
        raise LicenseError("Subscription not found in database.")
    
    # Check trial status if applicable
    if subscription.get('is_trial'):
        trial_status = check_trial_status(subscription_id)
        
        if not trial_status.get('valid'):
            raise TrialExpiredError(f"Free trial expired. {trial_status.get('message')} Please upgrade to a paid plan.")
        
        days_remaining = trial_status.get('days_remaining', 0)
        
        if days_remaining <= 3:
            print(f"⚠️  WARNING: Your free trial expires in {days_remaining} days. Consider upgrading.")
    
    # Check subscription expiry if not trial
    if subscription.get('status') != 'active':
        raise LicenseError(f"Subscription is {subscription.get('status')}. Please renew your subscription.")
    
    plan = subscription.get('plan', 'free_trial')
    
    # Get plan limits
    plan_limits = {
        'free_trial': {'endpoints': 5, 'features': ['basic_detection', 'alerts']},
        'pro': {'endpoints': 50, 'features': ['basic_detection', 'alerts', 'causal_trace', 'api_access']},
        'enterprise': {'endpoints': float('inf'), 'features': ['all']}
    }
    
    limits = plan_limits.get(plan, plan_limits['free_trial'])
    
    return {
        'valid': True,
        'plan': plan,
        'subscription_id': subscription_id,
        'status': subscription.get('status'),
        'is_trial': subscription.get('is_trial'),
        'days_remaining': trial_status.get('days_remaining') if subscription.get('is_trial') else None,
        'endpoints_limit': limits['endpoints'],
        'available_features': limits['features'],
        'message': f"License valid. Plan: {plan.upper()}"
    }

def validate_endpoint_registration(subscription_id: int, endpoint_name: str, endpoint_id: str) -> Dict:
    """
    Validate and register an endpoint.
    
    Returns:
        Dict with registration info
        
    Raises:
        PlanLimitExceededError: If endpoint limit reached
        TrialExpiredError: If trial expired
    """
    # Check license first
    lic = check_license(subscription_id)
    
    if not lic['valid']:
        raise LicenseError("License validation failed")
    
    # Register endpoint with limit checking
    try:
        result = register_endpoint(subscription_id, endpoint_name, endpoint_id)
        return result
    except ValueError as e:
        if "limit" in str(e).lower():
            raise PlanLimitExceededError(str(e))
        raise

def check_feature_access(subscription_id: int, feature_name: str) -> bool:
    """Check if subscription has access to a specific feature."""
    lic = check_license(subscription_id)
    
    if not lic['valid']:
        return False
    
    features = lic.get('available_features', [])
    
    if 'all' in features:
        return True
    
    return feature_name in features

# Backward compatibility
def check_license_legacy() -> Dict:
    """Legacy license check (for backward compatibility)."""
    try:
        license_data = load_license_file()
        if license_data:
            subscription_id = license_data.get('subscription_id')
            return check_license(subscription_id)
        else:
            raise LicenseError("No license file found")
    except Exception as e:
        raise LicenseError(f"License check failed: {str(e)}")
