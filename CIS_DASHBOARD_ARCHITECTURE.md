# CIS Dashboard Architecture and Implementation Plan

This document defines the proposed modern CIS dashboard implementation aligned with the CIS vision and the current repository.

## Proposed Architecture

### Frontend
- React + TypeScript
- Tailwind CSS for styling
- Framer Motion for UI animation
- React Router for navigation
- Recharts or Apache ECharts for charts
- Mapbox GL or Leaflet for world map visualization
- React Query for data fetching and caching

### Backend
- FastAPI for REST and WebSocket APIs
- SQLAlchemy for ORM and PostgreSQL access
- Redis for caching, session storage, and task queueing
- JWT-based authentication with role-based access control
- WebSocket endpoints for live event streaming and status updates
- Optional Celery worker for asynchronous AI scoring and incident tasks

### Database
- PostgreSQL database schema for:
  - users and roles
  - sessions and auth tokens
  - alerts and telemetry
  - incidents and playbook actions
  - process inventory and host status
  - model predictions and explainability logs

### Deployment
- Docker Compose orchestration
- Nginx reverse proxy for API and frontend
- Separate containers for frontend, backend, PostgreSQL, Redis, and optional Celery worker

### AI / Telemetry
- Python AI engine using PyTorch/TensorFlow/ONNX runtime
- eBPF collector providing software telemetry to the detection pipeline
- Threat intelligence ingestion and enrichment
- Model explanations surfaced in the UI

## Dashboard Pages

1. Dashboard
2. Live Events
3. Threat Intelligence
4. AI Prediction
5. Attack Map
6. Process Monitor
7. Quarantine
8. Reports
9. Digital Twin
10. Playbooks
11. User Management
12. Alert History
13. System Settings
14. Analytics & Logs
15. Incident Response

## User Interface Components

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
- User and role management
- Notification / webhook configuration

## Proposed Repo Layout

```
cis-dashboard/
├── frontend/
│   ├── src/
│   ├── components/
│   ├── pages/
│   ├── hooks/
│   ├── services/
│   └── styles/
├── backend/
│   ├── api/
│   ├── models/
│   ├── websocket/
│   ├── auth/
│   ├── detection/
│   ├── ai/
│   └── database/
├── docker-compose.yml
├── nginx/
└── README.md
```

## Integration with Existing CIS

This modern dashboard should complement the existing `cis/` runtime and the current Flask-based `cis/dashboard_new.py` prototype.

### Integration points
- Alerts and status data from `cis/main_detector.py`
- Explainability and playbook APIs already present in `cis/`
- eBPF telemetry ingestion and detection outputs
- Existing user and billing management modules for auth and roles

## Recommended Next Steps

1. Create a dedicated `frontend/` scaffold for the React dashboard.
2. Build a FastAPI backend with preliminary user, auth, and alert APIs.
3. Add PostgreSQL schema and `cis/` integration for alert persistence.
4. Add Redis caching and session support.
5. Add WebSocket event streaming support for live updates.
6. Create initial dashboard pages for system overview, alerts, and live events.
7. Add authentication, role-based access control, and deployment assets.
8. Migrate or integrate the existing Flask prototype to the new stack.
