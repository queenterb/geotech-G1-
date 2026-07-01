# CIS Investigation UI (Prototype)

This folder contains the current prototype investigation UI for CIS. It is a lightweight, browser-based frontend that communicates with CIS backend endpoints to show alerts, explain detections, and execute playbooks.

Current prototype usage:
- `GET /alerts` — returns recent alerts (reads `CIS_ALERTS_FILE` or default path)
- `POST /explain` — returns explanation for an alert payload
- `GET /playbooks` — lists available playbooks
- `POST /run_playbook` — executes a playbook (dry-run by default)

Planned full-stack dashboard:
- Frontend: React + TypeScript + Tailwind CSS + Framer Motion
- Backend: FastAPI + SQLAlchemy + WebSockets
- Data store: PostgreSQL
- Cache/queue: Redis
- Authentication: JWT + Role-Based Access Control
- Visualization: Recharts or Apache ECharts; Mapbox GL or Leaflet
- Deployment: Docker Compose + Nginx

Proposed dashboard components:
- Sidebar navigation
- Top status bar
- Live event feed
- Threat level cards
- World attack map
- Attack timeline
- Resource monitoring charts
- Process table
- Alert drawer
- Quarantine management
- Reports and settings

For the full design and implementation roadmap, see `../CIS_DASHBOARD_ARCHITECTURE.md`.
