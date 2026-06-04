"""Run a local CIS portal with billing routes for testing.

Run with: python -m cis.run_portal
"""
from __future__ import annotations

from . import dashboard
from .customer_portal import create_customer_portal
from .billing_api import register_billing_routes


def create_app():
    app = dashboard.app

    # Register customer portal blueprint
    customer_bp = create_customer_portal()
    app.register_blueprint(customer_bp)

    # Register billing routes
    register_billing_routes(app)

    return app


if __name__ == "__main__":
    app = create_app()
    print("Starting CIS portal with billing on http://127.0.0.1:8000")
    app.run(host="127.0.0.1", port=8000, debug=True)
