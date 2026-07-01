import asyncio
import os
import threading
import time

from .main_detector import CISMain, load_config
from .run_portal import create_app


def build_service_config() -> dict:
    preferred_paths = []
    explicit_path = os.environ.get("CIS_CONFIG_PATH")
    if explicit_path:
        preferred_paths.append(explicit_path)

    for candidate in [
        os.path.join(os.getcwd(), "config.json"),
        os.path.join(os.getcwd(), "cis", "config.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "cis", "config.json"),
        os.path.join(os.getcwd(), "config.example.json"),
        os.path.join(os.getcwd(), "cis", "config.example.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "config.example.json"),
        os.path.join(os.path.dirname(os.path.dirname(__file__)), "cis", "config.example.json"),
    ]:
        if candidate not in preferred_paths:
            preferred_paths.append(candidate)

    config_path = None
    for candidate in preferred_paths:
        if candidate and os.path.exists(candidate):
            config_path = candidate
            break

    config = load_config(config_path)

    config["ebpf_socket_path"] = os.environ.get("CIS_EBPF_SOCKET_PATH", config.get("ebpf_socket_path"))
    config["alerts_file"] = os.environ.get("CIS_ALERTS_FILE", config.get("alerts_file"))
    config["status_file"] = os.environ.get("CIS_STATUS_FILE", config.get("status_file"))
    config["heartbeat_file"] = os.environ.get("CIS_HEARTBEAT_FILE", config.get("heartbeat_file"))
    config["log_file"] = os.environ.get("CIS_LOG_FILE", config.get("log_file"))
    config["immune_memory_path"] = os.environ.get("CIS_IMMUNE_MEMORY_PATH", config.get("immune_memory_path"))
    config["resource_log_file"] = os.environ.get("CIS_RESOURCE_LOG_FILE", config.get("resource_log_file", os.path.join(os.environ.get("TEMP", "/tmp"), "cis_resource_usage.log")))
    config["subscription_id"] = os.environ.get("CIS_SUBSCRIPTION_ID", config.get("subscription_id"))
    return config


class DetectorThread(threading.Thread):
    def __init__(self, config: dict):
        super().__init__(daemon=True)
        self.config = config
        self.cis_main = CISMain(config)

    def run(self):
        try:
            asyncio.run(self.cis_main.start())
        except Exception as exc:
            self.cis_main.logger.exception("CIS detector thread exited unexpectedly: %s", exc)

    def stop(self):
        self.cis_main.running = False
        try:
            asyncio.run(self.cis_main.stop())
        except Exception:
            pass


def run_service():
    config = build_service_config()
    detector = DetectorThread(config)
    detector.start()

    app = create_app()
    host = os.environ.get("CIS_HOST", "127.0.0.1")
    port = int(os.environ.get("CIS_PORT", "8000"))
    debug = os.environ.get("CIS_DEBUG", "false").lower() in ("1", "true", "yes")

    try:
        app.run(host=host, port=port, debug=debug)
    finally:
        detector.stop()
        # Give the detector thread time to stop gracefully
        time.sleep(1)


if __name__ == "__main__":
    run_service()
