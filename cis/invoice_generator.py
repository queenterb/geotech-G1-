# Invoice Generation System for CIS
import os
import json
from datetime import datetime, timedelta
from typing import Dict, Optional

try:
    from .database import get_db_connection
except ImportError:
    from database import get_db_connection

class InvoiceGenerator:
    """Generate and manage invoices."""
    
    INVOICE_DIR = os.path.expanduser("~/.cis_invoices")
    
    def __init__(self):
        os.makedirs(self.INVOICE_DIR, exist_ok=True)
    
    @staticmethod
    def generate_invoice_number(user_id: int, subscription_id: int) -> str:
        """Generate unique invoice number."""
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        return f"INV-{user_id:05d}-{subscription_id:05d}-{timestamp}"
    
    @classmethod
    def create_invoice(cls, subscription_id: int, amount_cents: int, 
                      description: str = "Monthly Subscription", 
                      period_start: str = None, period_end: str = None) -> Dict:
        """Create a new invoice."""
        if not period_start:
            period_start = datetime.now().replace(day=1).isoformat()
        if not period_end:
            period_end = (datetime.now().replace(day=1) + timedelta(days=32)).replace(day=1).isoformat()
        
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Get subscription and user info
        cursor.execute('SELECT * FROM subscriptions WHERE id = ?', (subscription_id,))
        sub = cursor.fetchone()
        
        if not sub:
            conn.close()
            return {'error': 'Subscription not found'}
        
        cursor.execute('SELECT * FROM users WHERE id = ?', (sub['user_id'],))
        user = cursor.fetchone()
        
        invoice_number = cls.generate_invoice_number(user['id'], subscription_id)
        invoice_date = datetime.now().isoformat()
        due_date = (datetime.now() + timedelta(days=30)).isoformat()
        
        invoice_data = {
            'invoice_number': invoice_number,
            'subscription_id': subscription_id,
            'user_id': user['id'],
            'user_email': user['email'],
            'user_organization': user['organization'],
            'amount_cents': amount_cents,
            'amount_dollars': amount_cents / 100,
            'currency': 'USD',
            'description': description,
            'period_start': period_start,
            'period_end': period_end,
            'invoice_date': invoice_date,
            'due_date': due_date,
            'status': 'issued',
            'payment_status': 'pending'
        }
        
        # Save to file
        invoice_file = os.path.join(cls.INVOICE_DIR, f"{invoice_number}.json")
        with open(invoice_file, 'w') as f:
            json.dump(invoice_data, f, indent=2)
        
        conn.close()
        
        return {
            'invoice_number': invoice_number,
            'created': True,
            'created_at': invoice_date,
            'amount_dollars': amount_cents / 100,
            'file_path': invoice_file
        }
    
    @classmethod
    def get_invoice(cls, invoice_number: str) -> Optional[Dict]:
        """Retrieve an invoice."""
        invoice_file = os.path.join(cls.INVOICE_DIR, f"{invoice_number}.json")
        
        if not os.path.exists(invoice_file):
            return None
        
        with open(invoice_file, 'r') as f:
            return json.load(f)
    
    @classmethod
    def list_invoices(cls, user_id: int = None, subscription_id: int = None) -> List[Dict]:
        """List invoices, optionally filtered."""
        invoices = []
        
        for filename in os.listdir(cls.INVOICE_DIR):
            if not filename.endswith('.json'):
                continue
            
            invoice_file = os.path.join(cls.INVOICE_DIR, filename)
            with open(invoice_file, 'r') as f:
                invoice = json.load(f)
            
            # Filter if requested
            if user_id and invoice['user_id'] != user_id:
                continue
            if subscription_id and invoice['subscription_id'] != subscription_id:
                continue
            
            invoices.append(invoice)
        
        return sorted(invoices, key=lambda x: x['invoice_date'], reverse=True)
    
    @classmethod
    def mark_invoice_paid(cls, invoice_number: str) -> Dict:
        """Mark invoice as paid."""
        invoice = cls.get_invoice(invoice_number)
        
        if not invoice:
            return {'error': 'Invoice not found'}
        
        invoice['payment_status'] = 'paid'
        invoice['paid_date'] = datetime.now().isoformat()
        
        # Save updated invoice
        invoice_file = os.path.join(cls.INVOICE_DIR, f"{invoice_number}.json")
        with open(invoice_file, 'w') as f:
            json.dump(invoice, f, indent=2)
        
        return {
            'invoice_number': invoice_number,
            'payment_status': 'paid',
            'paid_at': invoice['paid_date']
        }
    
    @classmethod
    def generate_html_invoice(cls, invoice_number: str) -> str:
        """Generate HTML representation of invoice."""
        invoice = cls.get_invoice(invoice_number)
        
        if not invoice:
            return '<h1>Invoice not found</h1>'
        
        html = f'''
        <html>
        <head>
            <title>Invoice {invoice_number}</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ text-align: center; margin-bottom: 40px; }}
                .invoice-number {{ font-size: 24px; font-weight: bold; }}
                .details {{ margin: 20px 0; }}
                .amount {{ font-size: 20px; font-weight: bold; color: #667eea; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                td, th {{ border: 1px solid #ddd; padding: 10px; text-align: left; }}
                th {{ background-color: #667eea; color: white; }}
                .footer {{ text-align: center; margin-top: 40px; color: #666; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>CIS Invoice</h1>
                <div class="invoice-number">Invoice #{invoice_number}</div>
            </div>
            
            <div class="details">
                <h3>Bill To:</h3>
                <p>
                    {invoice['user_organization']}<br>
                    {invoice['user_email']}
                </p>
            </div>
            
            <table>
                <tr>
                    <th>Description</th>
                    <th>Period</th>
                    <th>Amount</th>
                </tr>
                <tr>
                    <td>{invoice['description']}</td>
                    <td>{invoice['period_start']} to {invoice['period_end']}</td>
                    <td>${invoice['amount_dollars']:.2f}</td>
                </tr>
            </table>
            
            <div>
                <h3>Total Amount Due:</h3>
                <div class="amount">${invoice['amount_dollars']:.2f} {invoice['currency']}</div>
            </div>
            
            <div class="details">
                <p><strong>Invoice Date:</strong> {invoice['invoice_date']}</p>
                <p><strong>Due Date:</strong> {invoice['due_date']}</p>
                <p><strong>Status:</strong> {invoice['payment_status'].upper()}</p>
            </div>
            
            <div class="footer">
                <p>Thank you for using CIS Security!</p>
                <p>Contact support@cis-security.com for questions</p>
            </div>
        </body>
        </html>
        '''
        
        return html
    
    @classmethod
    def get_invoice_summary(cls) -> Dict:
        """Get invoice statistics."""
        invoices = cls.list_invoices()
        
        total_issued = len(invoices)
        total_amount = sum(inv['amount_cents'] for inv in invoices) / 100
        paid_invoices = len([inv for inv in invoices if inv['payment_status'] == 'paid'])
        pending_invoices = total_issued - paid_invoices
        
        return {
            'total_invoices_issued': total_issued,
            'total_amount_dollars': round(total_amount, 2),
            'paid_invoices': paid_invoices,
            'pending_invoices': pending_invoices,
            'collection_rate': round((paid_invoices / total_issued * 100), 2) if total_issued > 0 else 0,
            'generated_at': datetime.now().isoformat()
        }
