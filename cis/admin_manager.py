# Admin Dashboard System for CIS Billing
import os
import json
from datetime import datetime, timedelta
from typing import Dict, List, Optional

try:
    from .database import get_db_connection, get_user_subscription
except ImportError:
    from database import get_db_connection, get_user_subscription

class AdminManager:
    """Manage admin operations and user accounts."""
    
    @staticmethod
    def get_all_users() -> List[Dict]:
        """Get all users."""
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT id, email, username, organization, created_at FROM users ORDER BY created_at DESC')
        rows = cursor.fetchall()
        conn.close()
        return [dict(row) for row in rows]
    
    @staticmethod
    def get_user_details(user_id: int) -> Optional[Dict]:
        """Get detailed user information."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get user info
        cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))
        user_row = cursor.fetchone()
        
        if not user_row:
            conn.close()
            return None
        
        user_data = dict(user_row)
        
        # Get subscription info
        cursor.execute('SELECT * FROM subscriptions WHERE user_id = ? ORDER BY created_at DESC', (user_id,))
        subs = cursor.fetchall()
        user_data['subscriptions'] = [dict(s) for s in subs]
        
        # Get endpoints
        if user_data['subscriptions']:
            cursor.execute(
                'SELECT * FROM endpoints WHERE subscription_id = ? ORDER BY registered_at DESC',
                (user_data['subscriptions'][0]['id'],)
            )
            endpoints = cursor.fetchall()
            user_data['endpoints'] = [dict(e) for e in endpoints]
        
        # Get payments
        if user_data['subscriptions']:
            cursor.execute(
                'SELECT * FROM payments WHERE subscription_id = ? ORDER BY created_at DESC',
                (user_data['subscriptions'][0]['id'],)
            )
            payments = cursor.fetchall()
            user_data['payments'] = [dict(p) for p in payments]
        
        conn.close()
        return user_data
    
    @staticmethod
    def extend_trial(subscription_id: int, days: int = 14) -> Dict:
        """Extend trial period."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT trial_end_date FROM subscriptions WHERE id = ?', (subscription_id,))
        row = cursor.fetchone()
        
        if not row:
            conn.close()
            return {'error': 'Subscription not found'}
        
        old_end = datetime.fromisoformat(row['trial_end_date'])
        new_end = old_end + timedelta(days=days)
        
        cursor.execute(
            'UPDATE subscriptions SET trial_end_date = ? WHERE id = ?',
            (new_end.isoformat(), subscription_id)
        )
        conn.commit()
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'extended': True,
            'old_end_date': old_end.isoformat(),
            'new_end_date': new_end.isoformat(),
            'days_added': days
        }
    
    @staticmethod
    def get_billing_stats() -> Dict:
        """Get billing statistics."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Total users
        cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1')
        total_users = cursor.fetchone()['count']
        
        # Trial users
        cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE is_trial = 1 AND status = "active"')
        trial_users = cursor.fetchone()['count']
        
        # Paid users
        cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE is_trial = 0 AND status = "active"')
        paid_users = cursor.fetchone()['count']
        
        # Total endpoints
        cursor.execute('SELECT COUNT(*) as count FROM endpoints WHERE status = "active"')
        total_endpoints = cursor.fetchone()['count']
        
        # Revenue (sum of payments)
        cursor.execute('SELECT SUM(amount_cents) as total FROM payments WHERE status = "completed"')
        revenue_row = cursor.fetchone()
        revenue_cents = revenue_row['total'] or 0
        
        # Subscriptions by plan
        cursor.execute('''
            SELECT plan, COUNT(*) as count 
            FROM subscriptions 
            WHERE status = "active" 
            GROUP BY plan
        ''')
        plan_distribution = {row['plan']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_users': total_users,
            'trial_users': trial_users,
            'paid_users': paid_users,
            'trial_conversion_rate': round((paid_users / total_users * 100), 2) if total_users > 0 else 0,
            'total_endpoints': total_endpoints,
            'total_revenue_cents': revenue_cents,
            'total_revenue_dollars': revenue_cents / 100,
            'plan_distribution': plan_distribution,
            'generated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def disable_user(user_id: int) -> Dict:
        """Disable a user account."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('UPDATE users SET is_active = 0 WHERE id = ?', (user_id,))
        cursor.execute('UPDATE subscriptions SET status = "disabled" WHERE user_id = ?', (user_id,))
        
        conn.commit()
        conn.close()
        
        return {'user_id': user_id, 'disabled': True}
    
    @staticmethod
    def process_refund(payment_id: int, reason: str = "") -> Dict:
        """Process a refund for a payment."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM payments WHERE id = ?', (payment_id,))
        payment = cursor.fetchone()
        
        if not payment:
            conn.close()
            return {'error': 'Payment not found'}
        
        cursor.execute(
            'UPDATE payments SET status = "refunded" WHERE id = ?',
            (payment_id,)
        )
        
        # Log refund
        refund_log = {
            'payment_id': payment_id,
            'reason': reason,
            'refunded_at': datetime.now().isoformat(),
            'amount_cents': payment['amount_cents']
        }
        
        conn.commit()
        conn.close()
        
        return {
            'payment_id': payment_id,
            'refunded': True,
            'amount_dollars': payment['amount_cents'] / 100,
            'reason': reason
        }
    
    @staticmethod
    def get_recent_activity(limit: int = 50) -> List[Dict]:
        """Get recent billing activity."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get recent payments
        cursor.execute('''
            SELECT 'payment' as type, created_at, amount_cents as value, status
            FROM payments
            ORDER BY created_at DESC
            LIMIT ?
        ''', (limit,))
        
        activities = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return sorted(activities, key=lambda x: x['created_at'], reverse=True)[:limit]
    
    @staticmethod
    def get_subscription_details(subscription_id: int) -> Optional[Dict]:
        """Get subscription details."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
        sub = cursor.fetchone()
        
        if not sub:
            conn.close()
            return None
        
        sub_dict = dict(sub)
        
        # Get endpoints
        cursor.execute('SELECT * FROM endpoints WHERE subscription_id = ?', (subscription_id,))
        endpoints = cursor.fetchall()
        sub_dict['endpoints'] = [dict(e) for e in endpoints]
        
        # Get usage
        cursor.execute('SELECT * FROM feature_usage WHERE subscription_id = ?', (subscription_id,))
        usage = cursor.fetchall()
        sub_dict['feature_usage'] = [dict(u) for u in usage]
        
        conn.close()
        return sub_dict
    
    @staticmethod
    def update_subscription_status(subscription_id: int, new_status: str) -> Dict:
        """Update subscription status."""
        valid_statuses = ['active', 'suspended', 'cancelled', 'expired', 'disabled']
        
        if new_status not in valid_statuses:
            return {'error': f'Invalid status. Must be one of: {", ".join(valid_statuses)}'}
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE subscriptions SET status = ? WHERE id = ?',
            (new_status, subscription_id)
        )
        
        conn.commit()
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'new_status': new_status,
            'updated_at': datetime.now().isoformat()
        }
