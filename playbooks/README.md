# Playbook Format

Playbooks are YAML files with the following top-level keys:

- `id`: unique identifier
- `name`: human-friendly name
- `description`: details about intent and scope
- `triggers`: list of alert conditions that should invoke the playbook
- `actions`: ordered list of actions to execute

Supported action types (prototype):
- `snapshot_pre` / `snapshot_post`: create named snapshots using `snapshot_orchestrator.py`.
- `kill_process`: kill a PID in the twin (in prototype this is simulated).
- `isolate_network`: simulate network isolation for a duration.
- `notify`: send a notification (prototype prints/logs).

Templates: fields may include `{{pid}}` or `{{change_id}}` which are filled at runtime.
