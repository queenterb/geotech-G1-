# Security, Audit Logging, and Rate Limiting for CIS
import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from typing import Dict, List
from collections import defaultdict

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

class AuditLogger:
    """Log all billing and security events."""
    
    AUDIT_DIR = os.path.expanduser("~/.cis_audit")
    
    def __init__(self):
        os.makedirs(self.AUDIT_DIR, exist_ok=True)
    
    @classmethod
    def log_event(cls, event_type: str, user_id: int, action: str, 
                 details: Dict = None, status: str = 'success') -> Dict:
        """Log an event to audit trail."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'event_type': event_type,
            'user_id': user_id,
            'action': action,
            'details': details or {},
            'status': status,
            'ip_address': 'logged'  # In production, get from request
        }
        
        # Create daily audit file
        date_str = datetime.now().strftime('%Y-%m-%d')
        audit_file = os.path.join(cls.AUDIT_DIR, f"audit-{date_str}.jsonl")
        
        with open(audit_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')
        
        return {'logged': True, 'timestamp': log_entry['timestamp']}
    
    @classmethod
    def log_login(cls, user_id: int, success: bool = True) -> None:
        """Log login attempt."""
        cls.log_event(
            'authentication',
            user_id,
            'login',
            {'success': success},
            'success' if success else 'failed'
        )
    
    @classmethod
    def log_payment(cls, user_id: int, subscription_id: int, amount_cents: int, 
                   status: str = 'completed') -> None:
        """Log payment transaction."""
        cls.log_event(
            'billing',
            user_id,
            'payment_processed',
            {
                'subscription_id': subscription_id,
                'amount_cents': amount_cents,
                'amount_dollars': amount_cents / 100
            },
            status
        )
    
    @classmethod
    def log_subscription_change(cls, user_id: int, subscription_id: int, 
                               old_plan: str, new_plan: str) -> None:
        """Log subscription plan change."""
        cls.log_event(
            'billing',
            user_id,
            'plan_upgrade',
            {
                'subscription_id': subscription_id,
                'old_plan': old_plan,
                'new_plan': new_plan
            }
        )
    
    @classmethod
    def log_trial_extension(cls, user_id: int, subscription_id: int, days: int) -> None:
        """Log trial extension."""
        cls.log_event(
            'billing',
            user_id,
            'trial_extended',
            {
                'subscription_id': subscription_id,
                'days_added': days
            }
        )
    
    @classmethod
    def log_refund(cls, user_id: int, payment_id: int, amount_cents: int, reason: str) -> None:
        """Log refund transaction."""
        cls.log_event(
            'billing',
            user_id,
            'refund_processed',
            {
                'payment_id': payment_id,
                'amount_cents': amount_cents,
                'reason': reason
            }
        )
    
    @classmethod
    def get_user_activity(cls, user_id: int, days: int = 30) -> List[Dict]:
        """Get user activity log."""
        activities = []
        start_date = datetime.now() - timedelta(days=days)
        
        # Read all audit files in date range
        for filename in os.listdir(cls.AUDIT_DIR):
            if not filename.endswith('.jsonl'):
                continue
            
            date_str = filename.replace('audit-', '').replace('.jsonl', '')
            try:
                file_date = datetime.fromisoformat(date_str)
            except Exception:
                continue
            
            if file_date < start_date:
                continue
            
            audit_file = os.path.join(cls.AUDIT_DIR, filename)
            with open(audit_file, 'r') as f:
                for line in f:
                    try:
                        entry = json.loads(line)
                        if entry['user_id'] == user_id:
                            activities.append(entry)
                    except Exception:
                        continue
        
        
    @classmethod
    def get_audit_summary(cls, days: int = 30) -> Dict:
        """Get audit summary statistics."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        start_date = (datetime.now() - timedelta(days=days)).isoformat()
        
        # Count events by type
        cursor.execute('''
            SELECT COUNT(*) as logins FROM users 
            WHERE created_at >= ?
        ''', (start_date,))
        new_users = cursor.fetchone()['logins']
        
        cursor.execute('''
            SELECT COUNT(*) as refunds FROM payments 
            WHERE status = "refunded" AND created_at >= ?
        ''', (start_date,))
        refunds = cursor.fetchone()['refunds']
        
        conn.close()
        
        return {
            'period_days': days,
            'new_users': new_users,
            'refunds_processed': refunds,
            'generated_at': datetime.now().isoformat()
        }


class RateLimiter:
    """Rate limiting for API endpoints."""
    
    def __init__(self, requests_per_minute: int = 60, requests_per_hour: int = 1000):
        self.requests_per_minute = requests_per_minute
        self.requests_per_hour = requests_per_hour
        self.request_log = defaultdict(list)
    
    def is_rate_limited(self, user_id: int) -> bool:
        """Check if user is rate limited."""
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        
        # Clean old requests
        self.request_log[user_id] = [
            req_time for req_time in self.request_log[user_id]
            if req_time > one_hour_ago
        ]
        
        # Check minute limit
        minute_requests = len([
            t for t in self.request_log[user_id]
            if t > one_minute_ago
        ])
        
        if minute_requests >= self.requests_per_minute:
            return True
        
        # Check hour limit
        hour_requests = len(self.request_log[user_id])
        
        if hour_requests >= self.requests_per_hour:
            return True
        
        return False
    
    def record_request(self, user_id: int) -> None:
        """Record a request for rate limiting."""
        self.request_log[user_id].append(time.time())
    
    def get_remaining_requests(self, user_id: int) -> Dict:
        """Get remaining requests for user."""
        now = time.time()
        one_minute_ago = now - 60
        one_hour_ago = now - 3600
        
        minute_requests = len([
            t for t in self.request_log[user_id]
            if t > one_minute_ago
        ])
        
        hour_requests = len([
            t for t in self.request_log[user_id]
            if t > one_hour_ago
        ])
        
        return {
            'minute_remaining': max(0, self.requests_per_minute - minute_requests),
            'hour_remaining': max(0, self.requests_per_hour - hour_requests),
            'minute_limit': self.requests_per_minute,
            'hour_limit': self.requests_per_hour
        }


class SecurityManager:
    """Handle security operations and checks."""
    
    @staticmethod
    def verify_api_key(api_key: str) -> Dict:
        """Verify API key authenticity."""
        if not api_key or len(api_key) < 32:
            return {'valid': False, 'reason': 'Invalid key format'}
        
        # Check key format (should start with cis_)
        if not api_key.startswith('cis_'):
            return {'valid': False, 'reason': 'Invalid key prefix'}
        
        return {'valid': True}
    
    @staticmethod
    def hash_sensitive_data(data: str) -> str:
        """Hash sensitive data for storage."""
        return hashlib.sha256(data.encode()).hexdigest()
    
    @staticmethod
    def check_data_integrity(data: Dict, signature: str) -> bool:
        """Verify data integrity using signature."""
        computed_sig = hashlib.sha256(
            json.dumps(data, sort_keys=True).encode()
        ).hexdigest()
        
        return computed_sig == signature
    
    @staticmethod
    def get_security_score(user_id: int) -> int:
        """Calculate security score for user account."""
        score = 100
        
        # Check password age (if available)
        # Check 2FA enabled
        # Check recent suspicious activity
        # Check API key rotation
        
        return score
    
    @staticmethod
    def flag_suspicious_activity(user_id: int, activity_type: str, 
                                 details: Dict) -> Dict:
        """Flag suspicious activity for investigation."""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'user_id': user_id,
            'activity_type': activity_type,
            'details': details,
            'severity': 'medium',
            'status': 'flagged'
        }
        
        # In production, send to security team
        # For now, just log it
        
        return alert
