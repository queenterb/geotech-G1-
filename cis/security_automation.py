import os
import json
import random
from datetime import datetime
from typing import Dict, List, Any

try:
    from .security_audit import AuditLogger
except ImportError:
    from security_audit import AuditLogger


class ThreatIntelligenceEngine:
    """Threat intelligence engine for CIS."""

    def __init__(self):
        self.context = {
            'global_feed': [
                {
                    'name': 'Suspicious C2 activity',
                    'confidence': 'high',
                    'source': 'Global threat feed',
                    'description': 'Detected remote command-and-control traffic patterns matching known adversary infrastructure.'
                },
                {
                    'name': 'Supply chain vulnerability',
                    'confidence': 'medium',
                    'source': 'Vendor advisory feed',
                    'description': 'A critical library dependency has a newly disclosed exploit affecting file monitoring agents.'
                },
                {
                    'name': 'Credential access campaign',
                    'confidence': 'high',
                    'source': 'Dark web intelligence',
                    'description': 'A targeted credential-stuffing campaign is active against enterprise admin accounts.'
                }
            ]
        }

    def get_global_threat_feed(self) -> List[Dict[str, Any]]:
        return self.context['global_feed']

    def predict_risk_score(self, system_state: Dict[str, Any]) -> int:
        score = 20
        score += min(40, int(system_state.get('suspicious_ips', 0)) * 8)
        score += min(30, int(system_state.get('divergence', 0)) * 5)
        if system_state.get('immune_alarm'):
            score += 20
        if system_state.get('heuristic_alarm'):
            score += 15
        if system_state.get('event_buffer', 0) > 50:
            score += 10
        return min(100, max(0, score))

    def get_predicted_attack_path(self, system_state: Dict[str, Any]) -> str:
        if system_state.get('immune_alarm') and system_state.get('suspicious_ips', 0) > 2:
            return 'Lateral movement via exposed admin shares'
        if system_state.get('divergence', 0) > 2.5:
            return 'Ransomware encryption chain activation'
        if system_state.get('suspicious_ips', 0) > 0:
            return 'Command-and-control beaconing to known threat hosts'
        return 'No active attack path predicted'

    def get_business_impact(self, risk_score: int) -> str:
        if risk_score >= 80:
            return 'High business impact: active disruption and data loss likely.'
        if risk_score >= 50:
            return 'Moderate business impact: critical operations may be affected.'
        return 'Low business impact: monitoring and containment recommended.'

    def get_recommendations(self, risk_score: int) -> List[str]:
        if risk_score >= 80:
            return [
                'Enforce containment on all suspicious hosts',
                'Initiate incident response playbook',
                'Enable emergency endpoint quarantine'
            ]
        if risk_score >= 50:
            return [
                'Harden remote access controls',
                'Review elevated session activity',
                'Increase network segmentation for critical assets'
            ]
        return [
            'Continue monitoring threat telemetry',
            'Validate endpoint security posture',
            'Ensure MFA is enforced for all admin accounts'
        ]


class SelfHealingEngine:
    """Self-healing automation engine for sample CIS system."""

    AUDIT_DIR = os.path.expanduser('~/.cis_self_healing')

    def __init__(self):
        os.makedirs(self.AUDIT_DIR, exist_ok=True)
        self.available_actions = [
            {
                'id': 'isolate_host',
                'title': 'Isolate suspicious host',
                'description': 'Isolates the host from the network to stop lateral movement and data exfiltration.',
                'risk_reduction': 25
            },
            {
                'id': 'revoke_admin',
                'title': 'Revoke elevated credentials',
                'description': 'Revoke temporary elevated credentials and force re-authentication.',
                'risk_reduction': 20
            },
            {
                'id': 'quarantine_files',
                'title': 'Quarantine malicious files',
                'description': 'Move detected malicious files to a secure quarantine and block execution.',
                'risk_reduction': 30
            }
        ]

    def evaluate_status(self, system_state: Dict[str, Any]) -> List[Dict[str, Any]]:
        actions = []
        if system_state.get('immune_alarm') or system_state.get('heuristic_alarm'):
            actions.extend(self.available_actions)
        elif system_state.get('suspicious_ips', 0) >= 2:
            actions.append(self.available_actions[0])
            actions.append(self.available_actions[1])
        else:
            actions.append(self.available_actions[2])
        return actions

    def perform_action(self, action_id: str, user_id: int) -> Dict[str, Any]:
        action = next((a for a in self.available_actions if a['id'] == action_id), None)
        if not action:
            return {'success': False, 'message': 'Unknown remediation action.'}

        result = {
            'timestamp': datetime.now().isoformat(),
            'action_id': action_id,
            'title': action['title'],
            'result': 'executed',
            'risk_reduction': action['risk_reduction'],
            'message': f"Action '{action['title']}' completed successfully."
        }
        self._log_action(user_id, result)
        return {'success': True, 'message': result['message'], 'action': result}

    def _log_action(self, user_id: int, result: Dict[str, Any]) -> None:
        AuditLogger.log_event(
            'automation',
            user_id,
            'self_healing_action',
            {
                'action_id': result['action_id'],
                'result': result['result'],
                'risk_reduction': result['risk_reduction']
            }
        )
        audit_file = os.path.join(self.AUDIT_DIR, 'actions.jsonl')
        with open(audit_file, 'a') as f:
            f.write(json.dumps(result) + '\n')

    def get_action_history(self) -> List[Dict[str, Any]]:
        history = []
        action_file = os.path.join(self.AUDIT_DIR, 'actions.jsonl')
        if not os.path.exists(action_file):
            return history

        with open(action_file, 'r') as f:
            for line in f:
                try:
                    history.append(json.loads(line))
                except Exception:
                    continue

        return sorted(history, key=lambda x: x.get('timestamp', ''), reverse=True)
