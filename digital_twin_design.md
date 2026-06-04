# Digital Twin Design & Rollback Strategy

## Purpose
Provide a safe, isolated environment (digital twin) to validate automated remediations and to perform tested rollbacks when changes are applied to production systems. The twin enables dry-runs, counterfactual simulations, and evidence-backed rollbacks.

## Components
- Twin runtime: lightweight virtual machines (Firecracker) or container sandboxes.
- Snapshot store: immutable snapshot artifacts (metadata + filesystem/state dump) in object storage or local snapshots directory.
- Orchestrator: service to create, validate, stage, and apply snapshots.
- Validator: automated test harness that runs health checks and counterfactual simulations against snapshots.

## Snapshot Strategy
- Snapshot contents: metadata.json, filesystem manifest (files/dirs of interest), process list (if available), configuration, and a human-readable README.
- Snapshot cadence: take pre-change snapshot and post-change snapshot for any automated remediation. Also periodic snapshots for critical systems (configurable).
- Retention: keep N latest snapshots per host (configurable), archive older snapshots to cold storage.

## Orchestration Flow
1. Create pre-change snapshot (name: `pre-<change-id>`).
2. Stage remediation in twin: apply proposed change in twin and run validation tests.
3. If validation passes, apply remediation to production; create post-change snapshot (`post-<change-id>`).
4. If production shows divergence or failure, rollback using the last known-good snapshot.

## Validation Tests
- Smoke tests: service health endpoints, process liveness, file presence checks.
- Counterfactual simulation: simulate killing suspicious PIDs and measure residual behavior (uses `CounterfactualSimulator` when available).
- Behavioral checks: ensure no unexpected file-write storms, CPU/power anomalies, or service crashes.

## Acceptance Criteria
- Snapshots can be created and listed via the orchestrator CLI.
- Validator can run smoke tests against a snapshot and return PASS/FAIL.
- Rollback can be staged and simulated without modifying production state.

## Quickstart (local prototype)
Create a snapshot, validate it, and run a rollback test using the orchestrator CLI in `scripts/`.

```bash
python scripts/snapshot_orchestrator.py create demo-snap
python scripts/snapshot_orchestrator.py list
python scripts/snapshot_orchestrator.py validate demo-snap
python scripts/snapshot_orchestrator.py rollback demo-snap --dry-run
```
