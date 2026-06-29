#!/usr/bin/env python3
import os
from datetime import datetime, timedelta

from cis.auth import hash_password
from cis.database import get_db_connection

EMAIL = 'screenshot_user@example.com'
USERNAME = 'screenshot_user'
PASSWORD = 'TestPass123!'

conn = get_db_connection()
cursor = conn.cursor()

# Check if user exists
cursor.execute('SELECT id FROM users WHERE username = ? OR email = ?', (USERNAME, EMAIL))
row = cursor.fetchone()
if row:
    user_id = row['id']
    print('User exists with id', user_id)
    # update password
    password_hash = hash_password(PASSWORD)
    cursor.execute('UPDATE users SET password_hash = ? WHERE id = ?', (password_hash, user_id))
    conn.commit()
else:
    password_hash = hash_password(PASSWORD)
    cursor.execute('INSERT INTO users (email, username, password_hash, organization) VALUES (?, ?, ?, ?)',
                   (EMAIL, USERNAME, password_hash, 'Automation'))
    user_id = cursor.lastrowid
    conn.commit()
    print('Created user id', user_id)

# Check if subscription exists
cursor.execute('SELECT id FROM subscriptions WHERE user_id = ?', (user_id,))
sub = cursor.fetchone()
now = datetime.now()
start = now.isoformat()
end = (now + timedelta(days=30)).isoformat()
if sub:
    sub_id = sub['id']
    cursor.execute('''UPDATE subscriptions SET plan = ?, status = 'active', is_trial = 0, subscription_start_date = ?, subscription_end_date = ?, billing_period = ?, endpoints = ? WHERE id = ?''',
                   ('pro', start, end, 'monthly', 10, sub_id))
    conn.commit()
    print('Updated subscription', sub_id)
else:
    cursor.execute('''INSERT INTO subscriptions (user_id, plan, status, is_trial, subscription_start_date, subscription_end_date, billing_period, endpoints) VALUES (?, ?, 'active', 0, ?, ?, ?, ?)''',
                   (user_id, 'pro', start, end, 'monthly', 10))
    sub_id = cursor.lastrowid
    conn.commit()
    print('Created subscription', sub_id)

conn.close()
print('Done. Login with:', USERNAME, PASSWORD)