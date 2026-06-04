# Stripe Payment Integration for CIS
import os
import json
from typing import Dict, Optional
from datetime import datetime

# This would normally use: import stripe
# For now, we'll create a mock integration that can be replaced

STRIPE_API_KEY = os.environ.get("STRIPE_API_KEY", "sk_test_placeholder")
STRIPE_WEBHOOK_SECRET = os.environ.get("STRIPE_WEBHOOK_SECRET", "whsec_placeholder")

PLANS = {
    'pro': {
        'name': 'Pro',
        'price': 600,  # $6.00 per endpoint/month in cents
        'currency': 'usd',
        'billing_period': 'monthly',
        'endpoints': 50,
        'features': ['basic_detection', 'alerts', 'causal_trace', 'api_access']
    },
    'enterprise': {
        'name': 'Enterprise',
        'price': 1200,  # $12.00 per endpoint/month in cents
        'currency': 'usd',
        'billing_period': 'monthly',
        'endpoints': float('inf'),
        'features': ['all']
    }
}

class StripeError(Exception):
    """Raised when Stripe operation fails."""
    pass

class StripePaymentProcessor:
    """Handles Stripe payment processing."""
    
    @staticmethod
    def create_customer(email: str, name: str) -> str:
        """
        Create a Stripe customer.
        
        Returns:
            Customer ID
        """
        try:
            # In production: stripe.Customer.create(email=email, name=name)
            customer_id = f"cus_{email.split('@')[0]}_{int(datetime.now().timestamp())}"
            
            return customer_id
        except Exception as e:
            raise StripeError(f"Failed to create customer: {str(e)}")
    
    @staticmethod
    def create_subscription(customer_id: str, plan: str, endpoints: int = 1) -> Dict:
        """
        Create a Stripe subscription.
        
        Args:
            customer_id: Stripe customer ID
            plan: Plan type ('pro' or 'enterprise')
            endpoints: Number of endpoints to bill for
            
        Returns:
            Dict with subscription info
        """
        if plan not in PLANS:
            raise StripeError(f"Invalid plan: {plan}")
        
        plan_config = PLANS[plan]
        
        try:
            # Calculate price based on endpoints
            price_cents = plan_config['price'] * endpoints
            
            # In production:
            # subscription = stripe.Subscription.create(
            #     customer=customer_id,
            #     items=[{
            #         'price_data': {
            #             'currency': plan_config['currency'],
            #             'product_data': {'name': plan_config['name']},
            #             'unit_amount': price_cents,
            #             'recurring': {'interval': 'month'}
            #         },
            #         'quantity': endpoints
            #     }]
            # )
            
            subscription_id = f"sub_{customer_id}_{plan}_{int(datetime.now().timestamp())}"
            
            return {
                'subscription_id': subscription_id,
                'customer_id': customer_id,
                'plan': plan,
                'endpoints': endpoints,
                'amount_cents': price_cents,
                'currency': plan_config['currency'],
                'status': 'active',
                'created_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise StripeError(f"Failed to create subscription: {str(e)}")
    
    @staticmethod
    def create_payment_intent(customer_id: str, amount_cents: int, payment_method: dict = None, description: str = None) -> Dict:
        """
        Create a Stripe payment intent.
        
        Returns:
            Dict with payment intent info
        """
        if not payment_method:
            raise StripeError('Missing payment method details')

        required_fields = ['name', 'email', 'card_number', 'exp_month', 'exp_year', 'cvc']
        for field in required_fields:
            if not payment_method.get(field):
                raise StripeError(f'Missing payment field: {field}')

        card_number = str(payment_method.get('card_number')).replace(' ', '')
        if len(card_number) < 12 or len(card_number) > 19 or not card_number.isdigit():
            raise StripeError('Invalid card number')

        try:
            exp_month = int(payment_method.get('exp_month'))
            exp_year = int(payment_method.get('exp_year'))
            cvc = str(payment_method.get('cvc'))
        except ValueError:
            raise StripeError('Invalid expiration date or CVC')

        if exp_month < 1 or exp_month > 12:
            raise StripeError('Invalid expiration month')

        if len(cvc) < 3 or len(cvc) > 4 or not cvc.isdigit():
            raise StripeError('Invalid CVC')

        try:
            # In production:
            # intent = stripe.PaymentIntent.create(
            #     customer=customer_id,
            #     amount=amount_cents,
            #     currency='usd',
            #     payment_method_data={
            #         'type': 'card',
            #         'card': {
            #             'number': card_number,
            #             'exp_month': exp_month,
            #             'exp_year': exp_year,
            #             'cvc': cvc
            #         }
            #     },
            #     description=description,
            #     confirm=True
            # )
            
            intent_id = f"pi_{customer_id}_{int(datetime.now().timestamp())}"
            
            return {
                'client_secret': f"{intent_id}_secret_{int(datetime.now().timestamp())}",
                'payment_intent_id': intent_id,
                'customer_id': customer_id,
                'amount_cents': amount_cents,
                'currency': 'usd',
                'status': 'succeeded',
                'card_last4': card_number[-4:],
                'description': description
            }
        except Exception as e:
            raise StripeError(f"Failed to create payment intent: {str(e)}")
    
    @staticmethod
    def cancel_subscription(subscription_id: str) -> Dict:
        """Cancel a Stripe subscription."""
        try:
            # In production: stripe.Subscription.delete(subscription_id)
            
            return {
                'subscription_id': subscription_id,
                'status': 'canceled',
                'canceled_at': datetime.now().isoformat()
            }
        except Exception as e:
            raise StripeError(f"Failed to cancel subscription: {str(e)}")

def get_plan_pricing(plan: str, endpoints: int = 1) -> Dict:
    """Get pricing for a plan."""
    if plan not in PLANS:
        raise StripeError(f"Invalid plan: {plan}")
    
    config = PLANS[plan]
    price_cents = config['price'] * endpoints
    
    return {
        'plan': plan,
        'endpoints': endpoints,
        'price_per_endpoint_cents': config['price'],
        'total_price_cents': price_cents,
        'total_price_dollars': price_cents / 100,
        'currency': config['currency'],
        'billing_period': config['billing_period'],
        'features': config['features']
    }

def validate_webhook_signature(payload: str, signature: str) -> bool:
    """Validate Stripe webhook signature."""
    # In production:
    # try:
    #     stripe.Webhook.construct_event(payload, signature, STRIPE_WEBHOOK_SECRET)
    #     return True
    # except Exception:
    #     return False
    
    return signature and STRIPE_WEBHOOK_SECRET in signature
