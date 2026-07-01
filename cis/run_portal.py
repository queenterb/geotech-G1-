"""Run a local CIS portal with billing routes for testing.

Run with: python -m cis.run_portal
"""
from __future__ import annotations

import os

from . import dashboard_new as dashboard
from .customer_portal import create_customer_portal


def create_app():
    app = dashboard.app

    # Register customer portal blueprint
    customer_bp = create_customer_portal()
    app.register_blueprint(customer_bp)

    return app


if __name__ == "__main__":
    app = create_app()
    host = os.environ.get("CIS_HOST", "127.0.0.1")
    port = int(os.environ.get("CIS_PORT", "8000"))
    debug = os.environ.get("CIS_DEBUG", "false").lower() in ("1", "true", "yes")
    print(f"Starting CIS portal with billing on http://{host}:{port}")
    app.run(host=host, port=port, debug=debug)
