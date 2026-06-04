# CIS Investigation UI (Prototype)

Run the API and open `http://127.0.0.1:8000/` to view the prototype investigation workspace.

Endpoints used:
- `GET /alerts` — returns recent alerts (reads `CIS_ALERTS_FILE` or default path)
- `POST /explain` — returns explanation for an alert payload
- `GET /playbooks` — lists available playbooks
- `POST /run_playbook` — executes a playbook (dry-run by default)
