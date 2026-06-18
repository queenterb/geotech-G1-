# Usage Tracking & Analytics for CIS
import os
from datetime import datetime, timedelta
from typing import Dict, List

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

class UsageTracker:
    """Track and analyze feature and resource usage."""
    
    USAGE_DIR = os.path.expanduser("~/.cis_usage")
    
    def __init__(self):
        os.makedirs(self.USAGE_DIR, exist_ok=True)
    
    @staticmethod
    def track_api_call(subscription_id: int, endpoint: str, method: str, response_time_ms: int) -> None:
        """Track an API call."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feature_usage (subscription_id, feature_name, usage_count, last_used)
            VALUES (?, ?, 1, CURRENT_TIMESTAMP)
            ON CONFLICT(subscription_id, feature_name) DO UPDATE SET
                usage_count = usage_count + 1,
                last_used = CURRENT_TIMESTAMP
        ''', (subscription_id, f'api:{method}:{endpoint}'))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def track_feature_usage(subscription_id: int, feature_name: str, count: int = 1) -> None:
        """Track feature usage."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO feature_usage (subscription_id, feature_name, usage_count, last_used)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT(subscription_id, feature_name) DO UPDATE SET
                usage_count = usage_count + ?,
                last_used = CURRENT_TIMESTAMP
        ''', (subscription_id, feature_name, count, count))
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def track_endpoint_heartbeat(endpoint_id: str, subscription_id: int) -> None:
        """Track endpoint heartbeat."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            'UPDATE endpoints SET last_heartbeat = CURRENT_TIMESTAMP WHERE endpoint_id = ?',
            (endpoint_id,)
        )
        
        conn.commit()
        conn.close()
    
    @staticmethod
    def get_usage_stats(subscription_id: int) -> Dict:
        """Get usage statistics for a subscription."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get all feature usage
        cursor.execute(
            'SELECT feature_name, usage_count, last_used FROM feature_usage WHERE subscription_id = ?',
            (subscription_id,)
        )
        
        usage_data = {}
        for row in cursor.fetchall():
            usage_data[row['feature_name']] = {
                'count': row['usage_count'],
                'last_used': row['last_used']
            }
        
        # Get endpoint stats
        cursor.execute(
            '''SELECT COUNT(*) as active_endpoints, 
                      MAX(last_heartbeat) as last_active 
               FROM endpoints WHERE subscription_id = ? AND status = "active"''',
            (subscription_id,)
        )
        endpoint_stats = cursor.fetchone()
        
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'feature_usage': usage_data,
            'active_endpoints': endpoint_stats['active_endpoints'],
            'last_active': endpoint_stats['last_active'],
            'tracked_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def get_daily_usage(subscription_id: int, days: int = 30) -> List[Dict]:
        """Get daily usage breakdown for past N days."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        cursor.execute('''
            SELECT 
                DATE(last_used) as date,
                COUNT(*) as operations,
                SUM(usage_count) as total_usage
            FROM feature_usage
            WHERE subscription_id = ? AND last_used >= ?
            GROUP BY DATE(last_used)
            ORDER BY date
        ''', (subscription_id, start_date))
        
        daily_data = []
        for row in cursor.fetchall():
            daily_data.append({
                'date': row['date'],
                'operations': row['operations'],
                'total_usage': row['total_usage']
            })
        
        conn.close()
        return daily_data
    
    @staticmethod
    def get_endpoint_health(subscription_id: int) -> Dict:
        """Get health status of all endpoints."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute(
            '''SELECT endpoint_id, endpoint_name, status, registered_at, last_heartbeat
               FROM endpoints WHERE subscription_id = ? ORDER BY registered_at DESC''',
            (subscription_id,)
        )
        
        endpoints = []
        healthy = 0
        
        for row in cursor.fetchone():
            endpoint_data = dict(row)
            
            # Check if healthy (last heartbeat within last hour)
            if row['last_heartbeat']:
                last_beat = datetime.fromisoformat(row['last_heartbeat'])
                is_healthy = (datetime.now() - last_beat).total_seconds() < 3600
            else:
                is_healthy = False
            
            if is_healthy:
                healthy += 1
            
            endpoint_data['is_healthy'] = is_healthy
            endpoints.append(endpoint_data)
        
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'total_endpoints': len(endpoints),
            'healthy_endpoints': healthy,
            'health_percentage': round((healthy / len(endpoints) * 100), 2) if endpoints else 0,
            'endpoints': endpoints
        }
    
    @staticmethod
    def get_top_features(subscription_id: int, limit: int = 10) -> List[Dict]:
        """Get most used features."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT feature_name, usage_count
            FROM feature_usage
            WHERE subscription_id = ?
            ORDER BY usage_count DESC
            LIMIT ?
        ''', (subscription_id, limit))
        
        features = []
        for row in cursor.fetchall():
            features.append({
                'feature': row['feature_name'],
                'usage_count': row['usage_count']
            })
        
        conn.close()
        return features
    
    @staticmethod
    def estimate_usage_cost(subscription_id: int, plan: str) -> Dict:
        """Estimate monthly cost based on usage."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get endpoint count
        cursor.execute(
            'SELECT COUNT(*) as count FROM endpoints WHERE subscription_id = ? AND status = "active"',
            (subscription_id,)
        )
        endpoint_count = cursor.fetchone()['count']
        
        # Calculate cost
        plan_pricing = {
            'pro': 6.00,
            'enterprise': 12.00
        }
        
        price_per_endpoint = plan_pricing.get(plan, 0)
        monthly_cost = endpoint_count * price_per_endpoint
        
        conn.close()
        
        return {
            'subscription_id': subscription_id,
            'plan': plan,
            'active_endpoints': endpoint_count,
            'price_per_endpoint': price_per_endpoint,
            'estimated_monthly_cost': round(monthly_cost, 2),
            'calculated_at': datetime.now().isoformat()
        }


class AnalyticsEngine:
    """Generate analytics and insights."""
    
    @staticmethod
    def get_platform_analytics() -> Dict:
        """Get platform-wide analytics."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # User analytics
        cursor.execute('SELECT COUNT(*) as count FROM users WHERE is_active = 1')
        total_users = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE is_trial = 1 AND status = "active"')
        trial_users = cursor.fetchone()['count']
        
        cursor.execute('SELECT COUNT(*) as count FROM subscriptions WHERE is_trial = 0 AND status = "active"')
        paid_users = cursor.fetchone()['count']
        
        # Endpoint analytics
        cursor.execute('SELECT COUNT(*) as count FROM endpoints WHERE status = "active"')
        total_endpoints = cursor.fetchone()['count']
        
        # Revenue analytics
        cursor.execute('SELECT SUM(amount_cents) as total FROM payments WHERE status = "completed"')
        revenue = cursor.fetchone()['total'] or 0
        
        # Feature usage
        cursor.execute('SELECT SUM(usage_count) as total FROM feature_usage')
        total_feature_usage = cursor.fetchone()['total'] or 0
        
        # Plan distribution
        cursor.execute('''
            SELECT plan, COUNT(*) as count FROM subscriptions
            WHERE status = "active"
            GROUP BY plan
        ''')
        plan_dist = {row['plan']: row['count'] for row in cursor.fetchall()}
        
        conn.close()
        
        return {
            'total_users': total_users,
            'trial_users': trial_users,
            'paid_users': paid_users,
            'conversion_rate': round((paid_users / total_users * 100), 2) if total_users > 0 else 0,
            'total_endpoints': total_endpoints,
            'total_revenue_dollars': revenue / 100,
            'arpu': round((revenue / 100 / paid_users), 2) if paid_users > 0 else 0,  # Average Revenue Per User
            'total_feature_usage': total_feature_usage,
            'plan_distribution': plan_dist,
            'generated_at': datetime.now().isoformat()
        }
    
    @staticmethod
    def get_trend_analysis(days: int = 30) -> Dict:
        """Analyze trends over time."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # User growth
        cursor.execute('''
            SELECT DATE(created_at) as date, COUNT(*) as new_users
            FROM users
            WHERE created_at >= ?
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (start_date,))
        
        user_trend = [{'date': row['date'], 'new_users': row['new_users']} 
                     for row in cursor.fetchall()]
        
        # Revenue trend
        cursor.execute('''
            SELECT DATE(created_at) as date, SUM(amount_cents) as revenue
            FROM payments
            WHERE created_at >= ? AND status = "completed"
            GROUP BY DATE(created_at)
            ORDER BY date
        ''', (start_date,))
        
        revenue_trend = [{'date': row['date'], 'revenue_cents': row['revenue']} 
                        for row in cursor.fetchall()]
        
        conn.close()
        
        return {
            'period_days': days,
            'user_trend': user_trend,
            'revenue_trend': revenue_trend,
            'analyzed_at': datetime.now().isoformat()
        }
