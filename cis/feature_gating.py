# Feature Gating for CIS Plans
from typing import List, Dict
from enum import Enum

class Feature(Enum):
    """Available features in CIS."""
    BASIC_DETECTION = "basic_detection"
    ALERTS = "alerts"
    CAUSAL_TRACE = "causal_trace"
    API_ACCESS = "api_access"
    ADVANCED_ANALYTICS = "advanced_analytics"
    CUSTOM_RULES = "custom_rules"
    SLA_SUPPORT = "sla_support"
    PRIORITY_SUPPORT = "priority_support"
    CUSTOM_INTEGRATION = "custom_integration"

# Plan capabilities
PLAN_FEATURES = {
    'free_trial': {
        'endpoints_limit': 5,
        'retention_days': 7,
        'features': [
            Feature.BASIC_DETECTION.value,
            Feature.ALERTS.value
        ],
        'api_calls_per_day': 1000,
        'support_level': 'community'
    },
    'pro': {
        'endpoints_limit': 50,
        'retention_days': 30,
        'features': [
            Feature.BASIC_DETECTION.value,
            Feature.ALERTS.value,
            Feature.CAUSAL_TRACE.value,
            Feature.API_ACCESS.value,
            Feature.ADVANCED_ANALYTICS.value
        ],
        'api_calls_per_day': 100000,
        'support_level': 'email'
    },
    'enterprise': {
        'endpoints_limit': float('inf'),
        'retention_days': 90,
        'features': [
            Feature.BASIC_DETECTION.value,
            Feature.ALERTS.value,
            Feature.CAUSAL_TRACE.value,
            Feature.API_ACCESS.value,
            Feature.ADVANCED_ANALYTICS.value,
            Feature.CUSTOM_RULES.value,
            Feature.SLA_SUPPORT.value,
            Feature.PRIORITY_SUPPORT.value,
            Feature.CUSTOM_INTEGRATION.value
        ],
        'api_calls_per_day': float('inf'),
        'support_level': 'sla'
    }
}

class FeatureGate:
    """Check feature access based on plan."""
    
    def __init__(self, plan: str):
        """
        Initialize feature gate for a plan.
        
        Args:
            plan: Plan type ('free_trial', 'pro', 'enterprise')
        """
        if plan not in PLAN_FEATURES:
            raise ValueError(f"Invalid plan: {plan}")
        
        self.plan = plan
        self.config = PLAN_FEATURES[plan]
    
    def has_feature(self, feature: str) -> bool:
        """Check if plan has access to a feature."""
        return feature in self.config['features']
    
    def check_feature(self, feature: str) -> Dict:
        """
        Check feature access with detailed response.
        
        Returns:
            Dict with feature access info
        """
        has_access = self.has_feature(feature)
        
        result = {
            'feature': feature,
            'has_access': has_access,
            'plan': self.plan
        }
        
        if not has_access:
            result['message'] = f"Feature '{feature}' is not available in {self.plan} plan"
            result['upgrade_required'] = True
        
        return result
    
    def get_endpoints_limit(self) -> int:
        """Get endpoint limit for plan."""
        limit = self.config['endpoints_limit']
        return int(limit) if limit != float('inf') else float('inf')
    
    def get_data_retention_days(self) -> int:
        """Get data retention period in days."""
        return self.config['retention_days']
    
    def get_api_calls_limit(self) -> int:
        """Get API calls per day limit."""
        limit = self.config['api_calls_per_day']
        return int(limit) if limit != float('inf') else float('inf')
    
    def get_support_level(self) -> str:
        """Get support level for plan."""
        return self.config['support_level']
    
    def get_available_features(self) -> List[str]:
        """Get list of available features."""
        return self.config['features']
    
    def check_endpoint_limit(self, current_endpoints: int) -> Dict:
        """Check if adding another endpoint would exceed limit."""
        limit = self.get_endpoints_limit()
        
        if limit == float('inf'):
            return {
                'can_add': True,
                'current_endpoints': current_endpoints,
                'limit': 'unlimited',
                'message': 'No endpoint limit for this plan'
            }
        
        can_add = current_endpoints < limit
        
        return {
            'can_add': can_add,
            'current_endpoints': current_endpoints,
            'limit': int(limit),
            'remaining': int(limit) - current_endpoints,
            'message': f"{int(limit) - current_endpoints} endpoint slots remaining" if can_add else "Endpoint limit reached"
        }
    
    def get_plan_summary(self) -> Dict:
        """Get complete plan summary."""
        limit = self.get_endpoints_limit()
        
        return {
            'plan': self.plan,
            'endpoints_limit': 'unlimited' if limit == float('inf') else int(limit),
            'data_retention_days': self.get_data_retention_days(),
            'api_calls_per_day': 'unlimited' if self.get_api_calls_limit() == float('inf') else int(self.get_api_calls_limit()),
            'support_level': self.get_support_level(),
            'features': self.get_available_features(),
            'total_features': len(self.get_available_features())
        }

def get_feature_comparison() -> Dict:
    """Get feature comparison across all plans."""
    all_features = set()
    
    for plan_config in PLAN_FEATURES.values():
        all_features.update(plan_config['features'])
    
    comparison = {}
    
    for feature in sorted(all_features):
        comparison[feature] = {}
        for plan, config in PLAN_FEATURES.items():
            comparison[feature][plan] = feature in config['features']
    
    return comparison

def suggest_upgrade(plan: str, feature: str) -> Dict:
    """Suggest upgrade path when feature unavailable."""
    if plan not in PLAN_FEATURES:
        return {'error': 'Invalid plan'}
    
    # Find minimum plan that has the feature
    for target_plan, config in PLAN_FEATURES.items():
        if feature in config['features'] and target_plan != plan:
            return {
                'current_plan': plan,
                'requested_feature': feature,
                'minimum_plan': target_plan,
                'message': f"Upgrade to {target_plan} plan to access {feature}",
                'upgrade_required': True
            }
    
    return {'error': 'Feature not available in any plan'}
