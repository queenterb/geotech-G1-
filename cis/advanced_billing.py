# Advanced Billing Features for CIS
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

class AdvancedBilling:
    """Advanced billing features like discounts, refunds, and custom pricing."""
    
    DISCOUNT_DIR = os.path.expanduser("~/.cis_discounts")
    INVOICE_DIR = os.path.expanduser("~/.cis_invoices")
    
    def __init__(self):
        os.makedirs(self.DISCOUNT_DIR, exist_ok=True)
    
    @classmethod
    def create_discount_code(cls, code: str, discount_percent: int, 
                            max_uses: int = None, expires_at: str = None) -> Dict:
        """Create a discount code."""
        if discount_percent < 1 or discount_percent > 100:
            return {'error': 'Discount must be between 1 and 100'}
        
        if not expires_at:
            expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        
        discount_data = {
            'code': code,
            'discount_percent': discount_percent,
            'max_uses': max_uses,
            'current_uses': 0,
            'created_at': datetime.now().isoformat(),
            'expires_at': expires_at,
            'active': True
        }
        
        file_path = os.path.join(cls.DISCOUNT_DIR, f"{code}.json")
        with open(file_path, 'w') as f:
            json.dump(discount_data, f, indent=2)
        
        return {
            'code': code,
            'created': True,
            'discount_percent': discount_percent,
            'expires_at': expires_at
        }
    
    @classmethod
    def apply_discount(cls, subscription_id: int, discount_code: str) -> Dict:
        """Apply discount code to subscription."""
        discount_file = os.path.join(cls.DISCOUNT_DIR, f"{discount_code}.json")
        
        if not os.path.exists(discount_file):
            return {'error': 'Discount code not found'}
        
        with open(discount_file, 'r') as f:
            discount = json.load(f)
        
        # Check if expired
        expires_at = datetime.fromisoformat(discount['expires_at'])
        if datetime.now() > expires_at:
            return {'error': 'Discount code has expired'}
        
        # Check if max uses exceeded
        if discount['max_uses'] and discount['current_uses'] >= discount['max_uses']:
            return {'error': 'Discount code has reached max uses'}
        
        # Apply discount
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Store discount application
        cursor.execute('''
            INSERT INTO feature_usage (subscription_id, feature_name, usage_count)
            VALUES (?, ?, 1)
        ''', (subscription_id, f'discount:{discount_code}'))
        
        conn.commit()
        conn.close()
        
        # Increment usage
        discount['current_uses'] += 1
        with open(discount_file, 'w') as f:
            json.dump(discount, f, indent=2)
        
        return {
            'subscription_id': subscription_id,
            'discount_code': discount_code,
            'discount_percent': discount['discount_percent'],
            'applied': True,
            'applied_at': datetime.now().isoformat()
        }
    
    @classmethod
    def create_annual_discount(cls, discount_percent: int = 20) -> str:
        """Create annual payment discount."""
        annual_code = f"ANNUAL{datetime.now().strftime('%Y')}"
        
        expires_at = (datetime.now() + timedelta(days=365)).isoformat()
        
        cls.create_discount_code(
            code=annual_code,
            discount_percent=discount_percent,
            max_uses=None,  # Unlimited uses
            expires_at=expires_at
        )
        
        return annual_code
    
    @classmethod
    def list_active_discounts(cls) -> List[Dict]:
        """List all active discount codes."""
        discounts = []
        
        for filename in os.listdir(cls.DISCOUNT_DIR):
            if not filename.endswith('.json'):
                continue
            
            file_path = os.path.join(cls.DISCOUNT_DIR, filename)
            with open(file_path, 'r') as f:
                discount = json.load(f)
            
            # Check if still active
            if discount['active']:
                expires_at = datetime.fromisoformat(discount['expires_at'])
                if datetime.now() < expires_at:
                    discounts.append(discount)
        
        return sorted(discounts, key=lambda x: x['created_at'], reverse=True)
    
    @classmethod
    def get_subscription_pricing(cls, plan: str, endpoints: int, discount_percent: int = 0) -> Dict:
        """Calculate subscription pricing with discounts."""
        plan_pricing = {
            'pro': 6.00,
            'enterprise': 12.00
        }
        
        base_price = plan_pricing.get(plan, 0) * endpoints
        discount_amount = base_price * (discount_percent / 100)
        final_price = base_price - discount_amount
        
        return {
            'plan': plan,
            'endpoints': endpoints,
            'base_price_per_endpoint': plan_pricing.get(plan),
            'subtotal': round(base_price, 2),
            'discount_percent': discount_percent,
            'discount_amount': round(discount_amount, 2),
            'total': round(final_price, 2),
            'currency': 'USD',
            'billing_period': 'monthly'
        }
    
    @classmethod
    def process_refund_request(cls, payment_id: int, reason: str, 
                             refund_percent: int = 100) -> Dict:
        """Process refund request."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
        payment = cursor.fetchone()
        
        if not payment:
            conn.close()
            return {'error': 'Payment not found'}
        
        # Calculate refund amount
        refund_amount = payment['amount_cents'] * (refund_percent / 100)
        
        # Update payment status
        cursor.execute(
            'UPDATE payments SET status = ? WHERE id = ?',
            ('refunded', payment_id)
        )
        
        # Log refund
        conn.commit()
        conn.close()
        
        return {
            'payment_id': payment_id,
            'original_amount': payment['amount_cents'] / 100,
            'refund_percent': refund_percent,
            'refund_amount': round(refund_amount / 100, 2),
            'reason': reason,
            'processed_at': datetime.now().isoformat(),
            'refunded': True
        }
    
    @classmethod
    def get_usage_based_pricing(cls, subscription_id: int, plan: str) -> Dict:
        """Calculate usage-based pricing."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get endpoint count
        cursor.execute(
            'SELECT COUNT(*) as count FROM endpoints WHERE subscription_id = ? AND status = "active"',
            (subscription_id,)
        )
        endpoint_count = cursor.fetchone()['count']
        
        # Get API usage (count feature_usage entries)
        cursor.execute(
            'SELECT SUM(usage_count) as total FROM feature_usage WHERE subscription_id = ?',
            (subscription_id,)
        )
        api_usage = cursor.fetchone()['total'] or 0
        
        conn.close()
        
        # Base pricing
        plan_pricing = {
            'pro': 6.00,
            'enterprise': 12.00
        }
        
        base_cost = endpoint_count * plan_pricing.get(plan, 0)
        
        # Usage overage charges (if applicable)
        plan_limits = {
            'pro': 100000,
            'enterprise': float('inf')
        }
        
        overage_limit = plan_limits.get(plan, 100000)
        overage_usage = max(0, api_usage - overage_limit)
        overage_cost = overage_usage * 0.001  # $0.001 per API call overage
        
        total_cost = base_cost + overage_cost
        
        return {
            'subscription_id': subscription_id,
            'plan': plan,
            'base_cost': round(base_cost, 2),
            'endpoint_count': endpoint_count,
            'api_usage': api_usage,
            'api_limit': int(overage_limit) if overage_limit != float('inf') else 'unlimited',
            'overage_usage': overage_usage,
            'overage_cost': round(overage_cost, 2),
            'total_monthly_cost': round(total_cost, 2),
            'currency': 'USD'
        }
    
    @classmethod
    def create_custom_pricing(cls, subscription_id: int, monthly_cost: float, 
                             reason: str = "") -> Dict:
        """Create custom pricing for enterprise customers."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Store custom pricing in feature_usage
        cursor.execute('''
            INSERT INTO feature_usage (subscription_id, feature_name, usage_count)
            VALUES (?, ?, ?)
        ''', (subscription_id, f'custom_pricing:{reason}', int(monthly_cost * 100)))
        
        conn.commit()
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'monthly_cost': monthly_cost,
            'reason': reason,
            'custom_pricing_applied': True,
            'effective_date': datetime.now().isoformat()
        }
    
    @classmethod
    def get_discount_stats(cls) -> Dict:
        """Get discount statistics."""
        discounts = cls.list_active_discounts()
        
        total_uses = sum(d['current_uses'] for d in discounts)
        avg_discount = sum(d['discount_percent'] for d in discounts) / len(discounts) if discounts else 0
        
        return {
            'total_active_codes': len(discounts),
            'total_uses': total_uses,
            'avg_discount_percent': round(avg_discount, 2),
            'generated_at': datetime.now().isoformat()
        }
