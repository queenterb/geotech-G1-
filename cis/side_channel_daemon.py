from __future__ import annotations

import queue
import threading
import time
from dataclasses import dataclass

import psutil


@dataclass
class SideChannelSample:
    timestamp: float
    power_pkg_watts: float
    power_cores_watts: float
    power_dram_watts: float
    cpu_temp_c: float
    acoustic_intensity: float
    acoustic_spectral_centroid: float


class SideChannelAcquirer:
    """Prototype acquirer with no hard dependency on audio/RAPL libs."""

    def __init__(self):
        self.sample_queue: queue.Queue[SideChannelSample] = queue.Queue(maxsize=1000)
        self.running = False
        self._last_disk = psutil.disk_io_counters()
        self._last_t = time.time()

    def _safe_cpu_temp(self) -> float:
        sensor_reader = getattr(psutil, "sensors_temperatures", None)
        if sensor_reader is None:
            return 0.0
        try:
            temps = sensor_reader()
        except Exception:
            return 0.0
        for key in ("coretemp", "k10temp", "cpu_thermal"):
            if key in temps and temps[key]:
                return float(temps[key][0].current)
        return 0.0

    def _pseudo_power(self) -> tuple[float, float, float]:
        # Approximation for environments where RAPL is unavailable.
        cpu = psutil.cpu_percent(interval=None)
        pkg = 20.0 + cpu * 0.8
        cores = pkg * 0.7
        dram = pkg * 0.1
        return pkg, cores, dram

    def _acoustic_fallback(self) -> tuple[float, float]:
        current = psutil.disk_io_counters()
        now = time.time()
        dt = max(1e-6, now - self._last_t)
        read_rate = (current.read_bytes - self._last_disk.read_bytes) / dt
        write_rate = (current.write_bytes - self._last_disk.write_bytes) / dt
        self._last_disk = current
        self._last_t = now

        intensity = min(1.0, (read_rate + write_rate) / (100 * 1024 * 1024))
        centroid = float(1000 + min(5000, write_rate / (10 * 1024 * 1024) * 5000))
        return intensity, centroid

    def acquire_sample(self) -> SideChannelSample:
        pkg, cores, dram = self._pseudo_power()
        temp = self._safe_cpu_temp()
        rms, centroid = self._acoustic_fallback()
        return SideChannelSample(
            timestamp=time.time(),
            power_pkg_watts=pkg,
            power_cores_watts=cores,
            power_dram_watts=dram,
            cpu_temp_c=temp,
            acoustic_intensity=rms,
            acoustic_spectral_centroid=centroid,
        )

    def run(self, interval_sec: float = 0.1):
        self.running = True
        while self.running:
            sample = self.acquire_sample()
            if self.sample_queue.full():
                _ = self.sample_queue.get_nowait()
            self.sample_queue.put(sample)
            time.sleep(interval_sec)

    def stop(self):
        self.running = False


if __name__ == "__main__":
    acquirer = SideChannelAcquirer()
    t = threading.Thread(target=acquirer.run, args=(0.1,), daemon=True)
    t.start()
    try:
        while True:
            s = acquirer.sample_queue.get(timeout=1)
            print(
                f"power={s.power_pkg_watts:.2f}W temp={s.cpu_temp_c:.1f}C "
                f"acoustic={s.acoustic_intensity:.3f}"
            )
    except KeyboardInterrupt:
        acquirer.stop()
