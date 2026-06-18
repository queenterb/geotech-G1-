
from __future__ import annotations
import requests
import smtplib
from email.message import EmailMessage

import argparse
import asyncio
import json
import logging
import os
import platform
import queue
import socket
import threading
import time
import sys
from dataclasses import dataclass
from logging.handlers import RotatingFileHandler
from typing import Optional

import numpy as np
try:
    import torch
except Exception:  # pragma: no cover - optional runtime dependency
    torch = None

try:
    from .digital_twin_controller import CounterfactualSimulator, FirecrackerTwin
    from .immune_memory import ImmuneMemory
    from .intervention_engine import InterventionEngine
    from .side_channel_daemon import SideChannelAcquirer
    from .license_check import check_license, LicenseError, TrialExpiredError
    from .feature_gating import FeatureGate
    from .alert_explanation import explain_alert
except ImportError:
    from digital_twin_controller import CounterfactualSimulator, FirecrackerTwin
    from immune_memory import ImmuneMemory
    from intervention_engine import InterventionEngine
    from side_channel_daemon import SideChannelAcquirer
    from license_check import check_license, LicenseError, TrialExpiredError
    from feature_gating import FeatureGate
    from alert_explanation import explain_alert


PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


CONFIG = {
    "platform": platform.system(),
    "ebpf_socket_path": "/tmp/cis_ebpf_events.sock" if platform.system() != "Windows" else None,
    "snapshot_interval": 5.0,
    "prediction_window": 5.0,
    "divergence_threshold": 0.35,
    "heuristic_write_threshold": 120,
    "counterfactual_lookback_ms": 50,
    "encryption_threshold": 0.3,
    "model_path": os.path.join(PROJECT_ROOT, "models", "lstm_gnn_scripted.pt"),
    "alerts_file": os.path.join(os.environ.get("TEMP", "/tmp"), "cis_alerts.jsonl"),
    "status_file": os.path.join(os.environ.get("TEMP", "/tmp"), "cis_status.json"),
    "heartbeat_file": os.path.join(os.environ.get("TEMP", "/tmp"), "cis_heartbeat"),
    "immune_memory_path": os.path.join(PROJECT_ROOT, "models", "immune_memory.pkl"),
    "log_file": os.path.join(os.environ.get("TEMP", "/tmp"), "cis_main.log"),
    "log_max_bytes": 5_000_000,
    "log_backup_count": 5,
}


ALLOWED_OP_TYPES = {1, 2, 3, 4}


def build_logger(config: dict) -> logging.Logger:
    logger = logging.getLogger("cis.main")
    if logger.handlers:
        return logger
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s %(levelname)s %(message)s")
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)
    logger.addHandler(stream_handler)

    log_file = str(config.get("log_file", "/tmp/cis_main.log"))
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=int(config.get("log_max_bytes", 5_000_000)),
        backupCount=int(config.get("log_backup_count", 5)),
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
    return logger


def validate_event_payload(payload: dict) -> Optional[SoftwareEvent]:
    required = {"pid", "timestamp", "filename", "op_type"}
    if not required.issubset(payload.keys()):
        return None
    try:
        pid = int(payload["pid"])
        uid = int(payload.get("uid", 0))
        ts = float(payload["timestamp"])
        comm = str(payload.get("comm", ""))[:15]
        filename = str(payload["filename"])[:255]
        op_type = int(payload["op_type"])
    except Exception:
        return None

    if pid <= 0 or ts <= 0:
        return None
    if op_type not in ALLOWED_OP_TYPES:
        return None
    if not filename:
        return None

    return SoftwareEvent(
        pid=pid,
        uid=uid,
        timestamp=ts,
        comm=comm,
        filename=filename,
        op_type=op_type,
    )


@dataclass
class SoftwareEvent:
    pid: int
    uid: int
    timestamp: float
    comm: str
    filename: str
    op_type: int


class FileSystemState:
    def __init__(self):
        self.encryption_indicator = 0.0
        self.entropy = 0.0
        self.modified_files_count = 0

    def update_from_events(self, events: list[SoftwareEvent], window_sec: float = 5.0):
        now = time.time()
        recent = [e for e in events if now - e.timestamp <= window_sec]
        writes = sum(1 for e in recent if e.op_type == 2)
        self.modified_files_count = writes
        self.encryption_indicator = min(1.0, writes / 1000.0)
        self.entropy = min(8.0, 5.0 + writes / 500.0)


class AnticipatoryModel:
    def __init__(self, model_path: str):
        self.device = "cpu"
        self.model = None
        if torch is not None:
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        if torch is not None and os.path.exists(model_path):
            self.model = torch.jit.load(model_path, map_location=self.device)
            self.model.eval()
        self.history: list[np.ndarray] = []

    def add_observation(self, features: np.ndarray):
        self.history.append(features)
        if len(self.history) > 100:
            self.history = self.history[-100:]

    def predict_future_state(self, current_fs: FileSystemState) -> Optional[FileSystemState]:
        if torch is None or self.model is None or len(self.history) < 50:
            return None
        seq = np.stack(self.history[-50:]).astype(np.float32)
        seq_tensor = torch.tensor(seq, device=self.device).unsqueeze(0)
        adj = torch.eye(100, device=self.device).unsqueeze(0).unsqueeze(0)
        with torch.no_grad():
            pred = self.model(seq_tensor, adj).cpu().numpy()[0]
        out = FileSystemState()
        out.encryption_indicator = float(np.clip(pred[0], 0.0, 1.0))
        out.entropy = float(current_fs.entropy + pred[1])
        out.modified_files_count = int(current_fs.modified_files_count + pred[2])
        return out


class EBpfCollector:
    def __init__(self, socket_path: str, logger: logging.Logger):
        self.socket_path = socket_path
        self.logger = logger
        self.sock = None
        self.event_queue: queue.Queue[SoftwareEvent] = queue.Queue(maxsize=50000)
        self.use_tcp = False  # Will be set to True on Windows
        self.tcp_port = 9999
        self.active_connections = 0
        self.active_remote_ips: dict[str, int] = {}
        self._connection_lock = threading.Lock()

    def start(self):
        import platform
        is_windows = platform.system() == "Windows"
        if is_windows:
            self.use_tcp = True
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(("127.0.0.1", self.tcp_port))
            self.logger.info(f"listening on TCP 127.0.0.1:{self.tcp_port}")
        else:
            os.makedirs(os.path.dirname(self.socket_path) or ".", exist_ok=True)
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
            self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            self.sock.bind(self.socket_path)
            self.logger.info(f"listening on Unix socket {self.socket_path}")
        self.sock.listen(5)
        # Always run accept loop in a dedicated thread
        self.accept_thread = threading.Thread(target=self._accept_loop, daemon=True)
        self.accept_thread.start()

    def stop(self):
        try:
            if self.sock:
                self.sock.close()
        except Exception:
            pass
        try:
            if os.path.exists(self.socket_path):
                os.unlink(self.socket_path)
        except Exception:
            pass

    def _accept_loop(self):
        while True:
            try:
                self.logger.info("Waiting for connection in _accept_loop...")
                conn, addr = self.sock.accept()
                self.logger.info(f"Accepted new connection from {addr} in _accept_loop.")
                self._track_connection(addr)
            except OSError as e:
                self.logger.error(f"OSError in _accept_loop: {e}")
                break
            except Exception as e:
                self.logger.error(f"Exception in _accept_loop: {e}")
                continue
            threading.Thread(target=self._handle_conn, args=(conn, addr), daemon=True).start()

    def _track_connection(self, addr):
        with self._connection_lock:
            self.active_connections += 1
            if isinstance(addr, tuple) and addr:
                ip = str(addr[0])
            else:
                ip = str(addr)
            self.active_remote_ips[ip] = self.active_remote_ips.get(ip, 0) + 1

    def _release_connection(self, addr):
        with self._connection_lock:
            self.active_connections = max(0, self.active_connections - 1)
            if isinstance(addr, tuple) and addr:
                ip = str(addr[0])
            else:
                ip = str(addr)
            count = self.active_remote_ips.get(ip, 0) - 1
            if count <= 0:
                self.active_remote_ips.pop(ip, None)
            else:
                self.active_remote_ips[ip] = count

    def _handle_conn(self, conn: socket.socket, addr=None):
        buf = b""
        event_count = 0
        try:
            self.logger.info("_handle_conn started for new connection.")
            while True:
                try:
                    chunk = conn.recv(4096)
                    if not chunk:
                        self.logger.info("No more data from connection; breaking loop.")
                        break
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        try:
                            d = json.loads(line.decode("utf-8"))
                            self.logger.info(f"DEBUG RAW EVENT RECEIVED: {d}")
                            ev = validate_event_payload(d)
                            if ev is None:
                                self.logger.warning("dropping invalid event payload")
                                continue
                            if self.event_queue.full():
                                _ = self.event_queue.get_nowait()
                            self.event_queue.put(ev)
                            self.logger.info(f"DEBUG EVENT QUEUED: pid={ev.pid}, op_type={ev.op_type}, filename={ev.filename}, timestamp={ev.timestamp}")
                            event_count += 1
                        except Exception as e:
                            self.logger.warning(f"dropping malformed JSON event line: {e}")
                            continue
                except Exception as e:
                    self.logger.error(f"Exception during recv/processing: {e}")
                    break
        except Exception as e:
            self.logger.error(f"Exception in _handle_conn outer: {e}")
        finally:
            self.logger.info(f"Connection closed, received {event_count} events from simulator.")
            try:
                conn.close()
            except Exception as e:
                self.logger.error(f"Exception closing connection: {e}")
            self._release_connection(addr)


class CISMain:
    def _forward_alert(self, payload: dict):
        siem_log_file = self.config.get("siem_log_file")
        siem_http_endpoint = self.config.get("siem_http_endpoint")
        # Forward to external log file
        if siem_log_file:
            try:
                with open(siem_log_file, "a", encoding="utf-8") as f:
                    f.write(json.dumps(payload) + "\n")
                self.logger.info(f"Alert forwarded to SIEM log file: {siem_log_file}")
            except Exception as e:
                self.logger.warning(f"Failed to forward alert to SIEM log file: {e}")
        # Forward to HTTP endpoint
        if siem_http_endpoint:
            try:
                resp = requests.post(siem_http_endpoint, json=payload, timeout=5)
                self.logger.info(f"Alert forwarded to SIEM HTTP endpoint: {siem_http_endpoint} (status {resp.status_code})")
            except Exception as e:
                self.logger.warning(f"Failed to forward alert to SIEM HTTP endpoint: {e}")

    def _send_email_alert(self, subject: str, body: str):
        smtp_server = self.config.get("smtp_server")
        smtp_port = self.config.get("smtp_port", 587)
        smtp_user = self.config.get("smtp_user")
        smtp_password = self.config.get("smtp_password")
        alert_email_to = self.config.get("alert_email_to")
        alert_email_from = self.config.get("alert_email_from", smtp_user)
        if not (smtp_server and smtp_user and smtp_password and alert_email_to):
            self.logger.warning("Email alert not sent: SMTP config incomplete.")
            return
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = alert_email_from
        msg["To"] = alert_email_to
        msg.set_content(body)
        try:
            with smtplib.SMTP(smtp_server, smtp_port) as server:
                server.starttls()
                server.login(smtp_user, smtp_password)
                server.send_message(msg)
            self.logger.info("Alert email sent to %s", alert_email_to)
        except Exception as e:
            self.logger.warning(f"Failed to send alert email: {e}")
    def __init__(self, config: dict):
        self.config = config
        # Load policy config if present
        self.policy = config.get("policy", {})
        self.logger = build_logger(config)
        
        # ============================================================================
        # LICENSE VALIDATION
        # ============================================================================
        subscription_id = config.get("subscription_id") or os.environ.get("CIS_SUBSCRIPTION_ID")
        
        if subscription_id:
            try:
                self.logger.info(f"Checking license for subscription {subscription_id}")
                license_info = check_license(int(subscription_id))
                self.subscription_id = int(subscription_id)
                self.license_info = license_info
                self.feature_gate = FeatureGate(license_info['plan'])
                
                self.logger.info(f"✓ License validated successfully. Plan: {license_info['plan'].upper()}")
                
                if license_info.get('is_trial') and license_info.get('days_remaining'):
                    self.logger.warning(f"⚠️  Free trial expires in {license_info['days_remaining']} days")
                
            except TrialExpiredError as e:
                self.logger.error(f"✗ License check failed: {str(e)}")
                self.logger.error("Your free trial has expired. Please upgrade to a paid plan at https://cis-security.com/billing/upgrade")
                raise SystemExit(f"License validation failed: {str(e)}")
            except LicenseError as e:
                self.logger.warning(f"License check failed (non-critical): {str(e)}")
                self.logger.warning("Running in unlicensed mode with limited features")
                self.subscription_id = None
                self.license_info = None
                self.feature_gate = None
        else:
            self.logger.warning("No subscription ID found. Run in trial mode with limited features.")
            self.logger.info("Sign up for free trial: https://cis-security.com/billing/trial-signup")
            self.subscription_id = None
            self.license_info = None
            self.feature_gate = None
        
        # ============================================================================
        # INITIALIZE DETECTOR COMPONENTS
        # ============================================================================
        self.ebpf = EBpfCollector(config["ebpf_socket_path"], self.logger)
        self.side = SideChannelAcquirer()
        self.model = AnticipatoryModel(config["model_path"])
        self.immune = ImmuneMemory.load_or_create(config["immune_memory_path"])
        self.intervention = InterventionEngine()
        self.twin = FirecrackerTwin()
        self.causal = CounterfactualSimulator(self.twin)
        self.fs_state = FileSystemState()
        self.events: list[SoftwareEvent] = []
        self.side_samples = []
        self.running = True
        self.last_snapshot = time.time()
        self.last_net_bytes = None
        self.last_net_ts = None
        # Load alert rules from alert_rules.json if present
        self.alert_rules = []
        rules_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alert_rules.json")
        if os.path.exists(rules_path):
            try:
                with open(rules_path, "r", encoding="utf-8") as f:
                    self.alert_rules = json.load(f)
                self.logger.info(f"Loaded {len(self.alert_rules)} alert rules from {rules_path}")
            except Exception as e:
                self.logger.warning(f"Failed to load alert rules: {e}")

    def _log_resource_usage(self):
        try:
            import psutil
        except ImportError:
            return  # psutil not installed
        proc = psutil.Process(os.getpid())
        cpu = psutil.cpu_percent(interval=None)
        mem = proc.memory_info().rss / (1024 * 1024)  # MB
        log_path = self.config.get("resource_log_file", os.path.join(os.environ.get("TEMP", "/tmp"), "cis_resource_usage.log"))
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps({
                "timestamp": time.time(),
                "cpu_percent": cpu,
                "mem_mb": mem
            }) + "\n")

    async def start(self):
        # Always start ebpf collector in a dedicated thread
        threading.Thread(target=self.ebpf.start, daemon=True).start()
        self.logger.info("cis main started")
        threading.Thread(target=self.side.run, args=(0.1,), daemon=True).start()
        await self.twin.start_vm()

        while self.running:
            await asyncio.sleep(0.1)
            self._log_resource_usage()
            self._drain_inputs()
            self.fs_state.update_from_events(self.events)
            features = self._build_feature_vector()
            if features is not None:
                self.model.add_observation(features)

            if time.time() - self.last_snapshot >= self.config["snapshot_interval"]:
                self.intervention.take_snapshot()
                self.last_snapshot = time.time()
                self.logger.info("snapshot captured")

            predicted = self.model.predict_future_state(self.fs_state)
            divergence = 0.0
            if predicted is not None:
                divergence = abs(predicted.encryption_indicator - self.fs_state.encryption_indicator)

            immune_alarm = bool(features is not None and self.immune.detect(features))
            heuristic_alarm = self.fs_state.modified_files_count > int(self.config["heuristic_write_threshold"])

            # --- Customizable Alert Rules Engine ---
            rule_triggered = False
            rule_triggered_name = None
            rule_triggered_pid = None
            if self.alert_rules:
                for rule in self.alert_rules:
                    field = rule.get("field")
                    op = rule.get("op")
                    value = rule.get("value")
                    rule.get("action", "alert")
                    # Get the value from fs_state
                    field_value = getattr(self.fs_state, field, None)
                    if field_value is not None:
                        if op == ">" and field_value > value:
                            rule_triggered = True
                        elif op == ">=" and field_value >= value:
                            rule_triggered = True
                        elif op == "<" and field_value < value:
                            rule_triggered = True
                        elif op == "<=" and field_value <= value:
                            rule_triggered = True
                        elif op == "==" and field_value == value:
                            rule_triggered = True
                        elif op == "!=" and field_value != value:
                            rule_triggered = True
                        if rule_triggered:
                            rule_triggered_name = rule.get("name", "unnamed")
                            rule_triggered_pid = self._find_suspicious_pid()
                            self.logger.warning(f"Custom alert rule triggered: {rule_triggered_name} ({field} {op} {value})")
                            break

            self._write_status(divergence=divergence, immune_alarm=immune_alarm, heuristic_alarm=heuristic_alarm)

            # Use policy overrides if present
            self.policy.get("divergence_threshold", self.config["divergence_threshold"])
            self.policy.get("encryption_threshold", self.config["encryption_threshold"])
            self.policy.get("heuristic_write_threshold", self.config["heuristic_write_threshold"])
            self.policy.get("auto_isolate", True)
            auto_rollback_enabled = self.policy.get("auto_rollback", True)

            # --- If a rule is triggered, fire alert ---
            if rule_triggered and rule_triggered_pid is not None:
                future_enc = await self.causal.simulate_kill(
                    rule_triggered_pid,
                    lookback_ms=self.config["counterfactual_lookback_ms"],
                    ahead_sec=self.config["prediction_window"],
                )
                rollback_needed = auto_rollback_enabled and self.fs_state.encryption_indicator > 0.7
                intervention = self.intervention.intervene(
                    rule_triggered_pid,
                    rollback_needed=rollback_needed,
                )
                if features is not None:
                    self.immune.clonal_selection([features], [1])
                # Pass rule name in alert for traceability
                self._alert(
                    rule_triggered_pid,
                    divergence,
                    future_enc,
                    immune_alarm,
                    heuristic_alarm,
                    intervention,
                    rule_name=rule_triggered_name,
                )

    async def stop(self):
        self.running = False
        self.side.stop()
        self.ebpf.stop()
        self.immune.save(self.config["immune_memory_path"])
        await self.twin.stop_vm()
        self.logger.info("cis main stopped")

    def _drain_inputs(self):
        now = time.time()
        drained = 0
        while not self.ebpf.event_queue.empty():
            ev = self.ebpf.event_queue.get_nowait()
            self.events.append(ev)
            self.causal.record_event(
                {
                    "timestamp": ev.timestamp,
                    "pid": ev.pid,
                    "op_type": ev.op_type,
                    "path": ev.filename,
                }
            )
            self.logger.info(f"DEBUG EVENT: pid={ev.pid}, op_type={ev.op_type}, filename={ev.filename}, timestamp={ev.timestamp}")
            drained += 1
        if drained > 0:
            self.logger.info(f"_drain_inputs: Drained {drained} events from ebpf.event_queue. Total events in buffer: {len(self.events)}")
        else:
            self.logger.info("_drain_inputs: No events drained from ebpf.event_queue.")
        side_drained = 0
        while not self.side.sample_queue.empty():
            self.side_samples.append(self.side.sample_queue.get_nowait())
            side_drained += 1
        if side_drained > 0:
            self.logger.info(f"_drain_inputs: Drained {side_drained} events from side.sample_queue.")
        cutoff = now - 60.0
        self.events = [e for e in self.events if e.timestamp > cutoff]
        self.side_samples = [s for s in self.side_samples if s.timestamp > cutoff]

    def _build_feature_vector(self) -> Optional[np.ndarray]:
        if not self.events:
            return None
        now = time.time()
        recent_events = [e for e in self.events if now - e.timestamp <= 1.0]
        recent_side = [s for s in self.side_samples if now - s.timestamp <= 1.0]

        write_rate = float(sum(1 for e in recent_events if e.op_type == 2))
        avg_power = float(np.mean([s.power_pkg_watts for s in recent_side])) if recent_side else 0.0
        avg_acoustic = float(np.mean([s.acoustic_intensity for s in recent_side])) if recent_side else 0.0
        avg_temp = float(np.mean([s.cpu_temp_c for s in recent_side])) if recent_side else 0.0
        base = np.array([write_rate, self.fs_state.entropy, 0.0, avg_power, avg_acoustic, avg_temp], dtype=np.float32)

        expanded = np.tile(base, 43)[:256]
        return expanded

    def _find_suspicious_pid(self) -> Optional[int]:
        now = time.time()
        counts: dict[int, int] = {}
        for e in self.events:
            if now - e.timestamp <= 2.0 and e.op_type == 2:
                counts[e.pid] = counts.get(e.pid, 0) + 1
        if not counts:
            return None
        return max(counts, key=counts.get)

    def _compute_network_output(self) -> float:
        try:
            import psutil
        except ImportError:
            return 0.0
        now = time.time()
        counters = psutil.net_io_counters()
        bytes_sent = getattr(counters, 'bytes_sent', 0)
        if self.last_net_bytes is None or self.last_net_ts is None:
            self.last_net_bytes = bytes_sent
            self.last_net_ts = now
            return 0.0
        elapsed = max(1e-6, now - self.last_net_ts)
        rate_kbps = (bytes_sent - self.last_net_bytes) / elapsed / 1024.0
        self.last_net_bytes = bytes_sent
        self.last_net_ts = now
        return max(0.0, rate_kbps)

    def _count_false_positives(self) -> int:
        count = 0
        alerts_file = self.config.get('alerts_file')
        if not alerts_file:
            return 0
        try:
            with open(alerts_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if not line.strip():
                        continue
                    try:
                        alert = json.loads(line)
                    except Exception:
                        continue
                    if alert.get('false_positive'):
                        count += 1
        except Exception:
            pass
        return count

    def _write_status(self, divergence: float, immune_alarm: bool, heuristic_alarm: bool) -> None:
        status = {
            "timestamp": time.time(),
            "event_buffer": len(self.events),
            "side_buffer": len(self.side_samples),
            "encryption_indicator": self.fs_state.encryption_indicator,
            "modified_files_count": self.fs_state.modified_files_count,
            "modifications_per_min": sum(1 for e in self.events if e.op_type == 2),
            "divergence": divergence,
            "immune_alarm": immune_alarm,
            "heuristic_alarm": heuristic_alarm,
            "connections": getattr(self.ebpf, 'active_connections', 0),
            "suspicious_ips": len(getattr(self.ebpf, 'active_remote_ips', {})),
            "out_kbps": float(self._compute_network_output()),
            "renames_per_min": sum(1 for e in self.events if e.op_type == 3),
            "false_positive_count": self._count_false_positives(),
        }
        try:
            with open(self.config["status_file"], "w", encoding="utf-8") as f:
                json.dump(status, f)
            with open(self.config["heartbeat_file"], "w", encoding="utf-8") as f:
                f.write(str(status["timestamp"]))
        except Exception:
            pass


    def _alert(
        self,
        pid: int,
        divergence: float,
        future_enc: float,
        immune_alarm: bool,
        heuristic_alarm: bool,
        intervention,
        rule_name: str = None,
    ):
        # Gather actionable context
        proc_name = None
        file_affected = None
        for e in self.events:
            if e.pid == pid:
                proc_name = getattr(e, "comm", None)
                file_affected = getattr(e, "filename", None)
                break
        # Actionable alert payload
        payload = {
            "event": "counterfactual_trigger",
            "pid": pid,
            "process_name": proc_name,
            "file_affected": file_affected,
            "divergence": divergence,
            "future_encryption": future_enc,
            "current_encryption": self.fs_state.encryption_indicator,
            "immune_alarm": immune_alarm,
            "heuristic_alarm": heuristic_alarm,
            "intervention": {
                "isolated": intervention.isolated,
                "snapshot": intervention.snapshot,
                "rolled_back": intervention.rolled_back,
            },
            "timestamp": time.time(),
            "actionable": {
                "what_happened": "Suspicious encryption or file modification detected.",
                "what_to_do": "Review the process and file. Isolate or rollback if unauthorized.",
            },
            "false_positive": False,  # Can be set by dashboard acknowledgement
        }
        if rule_name:
            payload["rule_name"] = rule_name
        payload["explanation"] = explain_alert(payload)
        os.makedirs(os.path.dirname(self.config["alerts_file"]) or ".", exist_ok=True)
        with open(self.config["alerts_file"], "a", encoding="utf-8") as f:
            f.write(json.dumps(payload) + "\n")
        self.logger.warning("alert=%s", json.dumps(payload))

        # Send email notification for critical alerts
        email_subject = f"CIS ALERT: Suspicious Activity Detected (PID {pid})"
        if rule_name:
            email_subject = f"CIS ALERT: Rule Triggered - {rule_name} (PID {pid})"

        body = (
            f"A critical alert was triggered by the CIS system.\n\n"
            f"PID: {pid}\n"
            f"Process: {proc_name}\n"
            f"File: {file_affected}\n"
            f"Rule: {rule_name or 'N/A'}\n"
            f"Divergence: {divergence}\n"
            f"Future Encryption: {future_enc}\n"
            f"Current Encryption: {self.fs_state.encryption_indicator}\n"
            f"Immune Alarm: {immune_alarm}\n"
            f"Heuristic Alarm: {heuristic_alarm}\n"
            f"Intervention: {payload['intervention']}\n"
            f"Timestamp: {payload['timestamp']}\n\n"
            f"Summary: {payload['explanation']['summary']}\n"
            f"Root Cause: {payload['explanation']['root_cause']}\n"
            f"Impact: {payload['explanation']['impact']}\n"
            f"Recommendation: {payload['explanation']['recommended_action']}\n"
            f"Confidence: {payload['explanation']['confidence']}\n"
        )
        self._send_email_alert(email_subject, body)
        self._forward_alert(payload)


def load_config(path: Optional[str]) -> dict:
    cfg = dict(CONFIG)
    if path:
        with open(path, "r", encoding="utf-8") as f:
            override = json.load(f)
        cfg.update(override)
    return cfg


async def main(config: dict):
    cis = CISMain(config)
    try:
        await cis.start()
    finally:
        await cis.stop()


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser()
    p.add_argument("--config", default="")
    p.add_argument("--alerts-file", default="")
    return p.parse_args()


if __name__ == "__main__":
    args = parse_args()
    cfg = load_config(args.config or None)
    if args.alerts_file:
        cfg["alerts_file"] = args.alerts_file

    try:
        if platform.system() == "Windows":
            asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        asyncio.run(main(cfg))
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"ERROR: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
