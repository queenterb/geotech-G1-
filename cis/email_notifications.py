# Email Notifications System for CIS
import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta
from typing import Dict, Optional

try:
    from .database import get_db_connection, get_user_subscription
except ImportError:
    from database import get_db_connection, get_user_subscription

class EmailNotifier:
    """Handle all email notifications."""
    
    SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    SMTP_PORT = int(os.environ.get('SMTP_PORT', 587))
    SMTP_USER = os.environ.get('SMTP_USER', 'noreply@cis-security.com')
    SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', '')
    FROM_EMAIL = os.environ.get('FROM_EMAIL', 'noreply@cis-security.com')
    FROM_NAME = os.environ.get('FROM_NAME', 'CIS Security')
    
    @classmethod
    def _send_email(cls, to_email: str, subject: str, html_body: str, 
                   text_body: str = None) -> bool:
        """Send email via SMTP."""
        try:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = f"{cls.FROM_NAME} <{cls.FROM_EMAIL}>"
            msg['To'] = to_email
            
            if text_body:
                msg.attach(MIMEText(text_body, 'plain'))
            msg.attach(MIMEText(html_body, 'html'))
            
            # In production, use real SMTP
            # For now, just log it
            print(f"[EMAIL] To: {to_email}, Subject: {subject}")
            
            return True
        except Exception as e:
            print(f"[EMAIL ERROR] Failed to send email: {e}")
            return False
    
    @classmethod
    def send_welcome_email(cls, user_email: str, username: str, trial_days: int = 14) -> bool:
        """Send welcome email to new user."""
        subject = "Welcome to CIS - Your Free Trial is Active!"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Welcome, {username}!</h2>
            <p>Your CIS free trial has been activated.</p>
            
            <h3>What's Included in Your Trial:</h3>
            <ul>
                <li>✓ {trial_days} days of free access</li>
                <li>✓ 5 endpoints for monitoring</li>
                <li>✓ Real-time ransomware detection</li>
                <li>✓ Causal trace analysis (basic)</li>
                <li>✓ Community support</li>
            </ul>
            
            <p><strong>Trial Expires:</strong> {(datetime.now() + timedelta(days=trial_days)).strftime('%B %d, %Y')}</p>
            
            <p>
                <a href="https://cis-security.com/dashboard" style="
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                ">Go to Dashboard</a>
            </p>
            
            <p>Questions? Contact us at <a href="mailto:support@cis-security.com">support@cis-security.com</a></p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                © 2026 CIS Security. All rights reserved.
            </p>
        </body>
        </html>
        '''
        
        text_body = f"""
        Welcome, {username}!
        
        Your CIS free trial has been activated for {trial_days} days.
        
        Trial Expires: {(datetime.now() + timedelta(days=trial_days)).strftime('%B %d, %Y')}
        
        Go to dashboard: https://cis-security.com/dashboard
        
        Questions? Contact support@cis-security.com
        """
        
        return cls._send_email(user_email, subject, html_body, text_body)
    
    @classmethod
    def send_trial_ending_warning(cls, user_email: str, username: str, 
                                 days_remaining: int) -> bool:
        """Send warning that trial is ending soon."""
        subject = f"⚠️  Your CIS Trial Expires in {days_remaining} Days"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Your Trial Expires Soon!</h2>
            <p>Hi {username},</p>
            
            <p style="font-size: 16px; color: #d73a49;">
                Your free CIS trial expires in <strong>{days_remaining} days</strong>.
            </p>
            
            <p>To continue using CIS and protect your systems, upgrade to a paid plan:</p>
            
            <h3>Available Plans:</h3>
            <ul>
                <li><strong>Pro:</strong> $6/endpoint/month - Great for small teams</li>
                <li><strong>Enterprise:</strong> $12/endpoint/month - Full features + SLA</li>
            </ul>
            
            <p>
                <a href="https://cis-security.com/billing" style="
                    display: inline-block;
                    background-color: #28a745;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                ">Upgrade Now</a>
            </p>
            
            <p>Or contact us for custom pricing: <a href="mailto:sales@cis-security.com">sales@cis-security.com</a></p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                © 2026 CIS Security. All rights reserved.
            </p>
        </body>
        </html>
        '''
        
        return cls._send_email(user_email, subject, html_body)
    
    @classmethod
    def send_payment_confirmation(cls, user_email: str, username: str, 
                                 amount_dollars: float, plan: str) -> bool:
        """Send payment confirmation email."""
        subject = f"Payment Received - CIS {plan.upper()} Plan"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Payment Confirmed!</h2>
            <p>Hi {username},</p>
            
            <p>Thank you for upgrading to the <strong>{plan.upper()} plan</strong>.</p>
            
            <h3>Invoice Details:</h3>
            <table style="border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px;"><strong>Plan:</strong></td>
                    <td style="padding: 10px;">{plan.upper()}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Amount:</strong></td>
                    <td style="padding: 10px;">${amount_dollars:.2f}/month</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Date:</strong></td>
                    <td style="padding: 10px;">{datetime.now().strftime('%B %d, %Y')}</td>
                </tr>
            </table>
            
            <p>Your new features are now active. You can:</p>
            <ul>
                <li>Register more endpoints</li>
                <li>Access advanced features</li>
                <li>Get priority support</li>
            </ul>
            
            <p>
                <a href="https://cis-security.com/dashboard" style="
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                ">Go to Dashboard</a>
            </p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                © 2026 CIS Security. All rights reserved.
            </p>
        </body>
        </html>
        '''
        
        return cls._send_email(user_email, subject, html_body)
    
    @classmethod
    def send_refund_notification(cls, user_email: str, username: str, 
                                amount_dollars: float, reason: str) -> bool:
        """Send refund notification email."""
        subject = "Refund Processed - CIS Billing"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2>Refund Processed</h2>
            <p>Hi {username},</p>
            
            <p>A refund has been processed on your CIS account.</p>
            
            <h3>Refund Details:</h3>
            <table style="border-collapse: collapse;">
                <tr>
                    <td style="padding: 10px;"><strong>Amount:</strong></td>
                    <td style="padding: 10px;">${amount_dollars:.2f}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Reason:</strong></td>
                    <td style="padding: 10px;">{reason}</td>
                </tr>
                <tr>
                    <td style="padding: 10px;"><strong>Date:</strong></td>
                    <td style="padding: 10px;">{datetime.now().strftime('%B %d, %Y')}</td>
                </tr>
            </table>
            
            <p>The refund may take 3-5 business days to appear in your account.</p>
            
            <p>If you have any questions, contact us at <a href="mailto:support@cis-security.com">support@cis-security.com</a></p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                © 2026 CIS Security. All rights reserved.
            </p>
        </body>
        </html>
        '''
        
        return cls._send_email(user_email, subject, html_body)
    
    @classmethod
    def send_account_disabled_notice(cls, user_email: str, username: str, 
                                    reason: str = "Unpaid invoice") -> bool:
        """Send account disabled notification."""
        subject = "Action Required - CIS Account Status"
        
        html_body = f'''
        <html>
        <body style="font-family: Arial, sans-serif;">
            <h2 style="color: #d73a49;">Account Access Suspended</h2>
            <p>Hi {username},</p>
            
            <p>Your CIS account has been temporarily suspended.</p>
            
            <p><strong>Reason:</strong> {reason}</p>
            
            <h3>To Restore Access:</h3>
            <ol>
                <li>Log in to your account</li>
                <li>Go to Billing section</li>
                <li>Update your payment method</li>
                <li>Process payment to restore access</li>
            </ol>
            
            <p>
                <a href="https://cis-security.com/login" style="
                    display: inline-block;
                    background-color: #667eea;
                    color: white;
                    padding: 10px 20px;
                    text-decoration: none;
                    border-radius: 5px;
                ">Log In to Account</a>
            </p>
            
            <p>Questions? Contact us immediately: <a href="mailto:support@cis-security.com">support@cis-security.com</a></p>
            
            <hr>
            <p style="color: #666; font-size: 12px;">
                © 2026 CIS Security. All rights reserved.
            </p>
        </body>
        </html>
        '''
        
        return cls._send_email(user_email, subject, html_body)


class NotificationScheduler:
    """Schedule automatic notifications."""
    
    @classmethod
    def send_trial_expiration_warnings(cls) -> Dict:
        """Send warnings to users with expiring trials."""
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get users with trial expiring in 3 days
        cursor.execute('''
            SELECT u.email, u.username, s.trial_end_date
            FROM subscriptions s
            JOIN users u ON u.id = s.user_id
            WHERE s.is_trial = 1 AND s.status = "active"
        ''')
        
        users = cursor.fetchall()
        sent_count = 0
        
        for user in users:
            trial_end = datetime.fromisoformat(user['trial_end_date'])
            days_remaining = (trial_end - datetime.now()).days
            
            # Send warning if 3 days or less remaining
            if 0 <= days_remaining <= 3:
                success = EmailNotifier.send_trial_ending_warning(
                    user['email'],
                    user['username'],
                    days_remaining
                )
                if success:
                    sent_count += 1
        
        conn.close()
        
        return {
            'warnings_sent': sent_count,
            'sent_at': datetime.now().isoformat()
        }
    
    @classmethod
    def send_payment_reminders(cls) -> Dict:
        """Send payment reminders for overdue invoices."""
        # Implementation would send reminders for unpaid invoices
        return {
            'reminders_sent': 0,
            'sent_at': datetime.now().isoformat()
        }
