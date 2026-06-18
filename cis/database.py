# Database schema and initialization for CIS billing system
import sqlite3
import os
from datetime import datetime, timedelta
from typing import Optional, Dict

DB_PATH = os.path.expanduser("~/.cis_billing.db")

def get_db_connection():
    """Get database connection with row factory."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_database():
    """Initialize database schema."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Users table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            organization TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            is_active BOOLEAN DEFAULT 1
        )
    ''')
    
    # Subscriptions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS subscriptions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            plan TEXT NOT NULL,
            status TEXT DEFAULT 'active',
            trial_start_date TIMESTAMP,
            trial_end_date TIMESTAMP,
            subscription_start_date TIMESTAMP,
            subscription_end_date TIMESTAMP,
            is_trial BOOLEAN DEFAULT 1,
            stripe_customer_id TEXT,
            stripe_subscription_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Endpoints table (for tracking endpoint usage)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS endpoints (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            endpoint_name TEXT NOT NULL,
            endpoint_id TEXT UNIQUE NOT NULL,
            registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_heartbeat TIMESTAMP,
            status TEXT DEFAULT 'active',
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # Alerts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS alerts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            alert_type TEXT NOT NULL,
            severity TEXT,
            message TEXT,
            endpoint_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(id)
        )
    ''')
    
    # Feature usage table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feature_usage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            feature_name TEXT NOT NULL,
            usage_count INTEGER DEFAULT 0,
            last_used TIMESTAMP,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    # Payment records table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subscription_id INTEGER NOT NULL,
            amount_cents INTEGER,
            currency TEXT DEFAULT 'USD',
            status TEXT DEFAULT 'pending',
            stripe_charge_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(subscription_id) REFERENCES subscriptions(id)
        )
    ''')
    
    conn.commit()
    conn.close()

def create_trial_user(email: str, username: str, password_hash: str, organization: str = None) -> Dict:
    """Create a new trial user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        cursor.execute('''
            INSERT INTO users (email, username, password_hash, organization)
            VALUES (?, ?, ?, ?)
        ''', (email, username, password_hash, organization))
        
        user_id = cursor.lastrowid
        
        # Create free trial subscription (14 days)
        trial_start = datetime.now()
        trial_end = trial_start + timedelta(days=14)
        
        cursor.execute('''
            INSERT INTO subscriptions 
            (user_id, plan, status, trial_start_date, trial_end_date, is_trial)
            VALUES (?, ?, ?, ?, ?, 1)
        ''', (user_id, 'free_trial', 'active', trial_start.isoformat(), trial_end.isoformat()))
        
        subscription_id = cursor.lastrowid
        conn.commit()
        
        return {
            'user_id': user_id,
            'subscription_id': subscription_id,
            'email': email,
            'plan': 'free_trial',
            'trial_end_date': trial_end.isoformat(),
            'is_trial': True
        }
    except sqlite3.IntegrityError as e:
        conn.close()
        raise ValueError(f"User creation failed: {str(e)}")
    finally:
        conn.close()

def get_user_subscription(user_id: int) -> Optional[Dict]:
    """Get active subscription for user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT * FROM subscriptions 
        WHERE user_id = ? AND status = 'active'
        ORDER BY created_at DESC LIMIT 1
    ''', (user_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def check_trial_status(subscription_id: int) -> Dict:
    """Check if trial is still active."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('''
        SELECT is_trial, trial_end_date, status FROM subscriptions WHERE id = ?
    ''', (subscription_id,))
    
    row = cursor.fetchone()
    conn.close()
    
    if not row:
        return {'valid': False, 'message': 'Subscription not found'}
    
    is_trial = row['is_trial']
    status = row['status']
    trial_end = row['trial_end_date']
    
    if status != 'active':
        return {'valid': False, 'message': 'Subscription is not active'}
    
    if is_trial:
        trial_end_dt = datetime.fromisoformat(trial_end)
        if datetime.now() > trial_end_dt:
            # Trial expired
            cursor = conn.cursor()
            cursor.execute('''
                UPDATE subscriptions SET status = 'expired' WHERE id = ?
            ''', (subscription_id,))
            conn.commit()
            conn.close()
            return {'valid': False, 'message': 'Free trial has expired', 'days_remaining': 0}
        
        days_remaining = (trial_end_dt - datetime.now()).days
        return {'valid': True, 'message': 'Trial active', 'days_remaining': days_remaining, 'is_trial': True}
    
    return {'valid': True, 'message': 'Subscription active', 'is_trial': False}

def register_endpoint(subscription_id: int, endpoint_name: str, endpoint_id: str) -> Dict:
    """Register an endpoint for monitoring."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check plan endpoint limits
    subscription = get_subscription_by_id(subscription_id)
    if not subscription:
        conn.close()
        raise ValueError("Subscription not found")
    
    plan_limits = {
        'free_trial': 5,
        'pro': 50,
        'enterprise': float('inf')
    }
    
    max_endpoints = plan_limits.get(subscription['plan'], 0)
    
    # Count existing endpoints
    cursor.execute('''
        SELECT COUNT(*) as count FROM endpoints WHERE subscription_id = ? AND status = 'active'
    ''', (subscription_id,))
    
    current_count = cursor.fetchone()['count']
    
    if current_count >= max_endpoints:
        conn.close()
        raise ValueError(f"Endpoint limit ({max_endpoints}) reached for {subscription['plan']} plan")
    
    try:
        cursor.execute('''
            INSERT INTO endpoints (subscription_id, endpoint_name, endpoint_id, last_heartbeat)
            VALUES (?, ?, ?, ?)
        ''', (subscription_id, endpoint_name, endpoint_id, datetime.now().isoformat()))
        
        conn.commit()
        
        return {
            'endpoint_id': endpoint_id,
            'registered': True,
            'endpoints_used': current_count + 1,
            'endpoints_limit': max_endpoints
        }
    except sqlite3.IntegrityError:
        conn.close()
        raise ValueError("Endpoint already registered")
    finally:
        conn.close()

def get_subscription_by_id(subscription_id: int) -> Optional[Dict]:
    """Get subscription by ID."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        return dict(row)
    return None

def upgrade_subscription(subscription_id: int, new_plan: str, stripe_subscription_id: str = None) -> Dict:
    """Upgrade subscription from trial to paid plan."""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    subscription_start = datetime.now()
    subscription_end = subscription_start + timedelta(days=30)
    
    cursor.execute('''
        UPDATE subscriptions 
        SET plan = ?, status = 'active', is_trial = 0, 
            subscription_start_date = ?, subscription_end_date = ?,
            stripe_subscription_id = ?, updated_at = CURRENT_TIMESTAMP
        WHERE id = ?
    ''', (new_plan, subscription_start.isoformat(), subscription_end.isoformat(), 
          stripe_subscription_id, subscription_id))
    
    conn.commit()
    conn.close()
    
    return {
        'subscription_id': subscription_id,
        'plan': new_plan,
        'upgraded': True,
        'subscription_start': subscription_start.isoformat(),
        'subscription_end': subscription_end.isoformat()
    }

# Initialize database on import
if not os.path.exists(DB_PATH):
    init_database()
