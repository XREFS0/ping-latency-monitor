import time
from typing import Dict, List, Optional
from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool, QTimer
from monitor.models import Host, PingResult, HostStats, AppSettings
from monitor.ping import PingService

class WorkerSignals(QObject):
    completed = Signal(str, object)

class PingWorker(QRunnable):
    def __init__(self, host_id: str, address: str, timeout_ms: int, service: PingService) -> None:
        super().__init__()
        self.host_id = host_id
        self.address = address
        self.timeout_ms = timeout_ms
        self.service = service
        self.signals = WorkerSignals()

    def run(self) -> None:
        result = self.service.ping(self.address, self.timeout_ms)
        self.signals.completed.emit(self.host_id, result)

class MonitorEngine(QObject):
    ping_completed = Signal(str, PingResult)
    stats_updated = Signal(str, HostStats)
    alert_triggered = Signal(str, str, str)

    def __init__(self, settings: AppSettings) -> None:
        super().__init__()
        self.settings = settings
        self.ping_service = PingService()
        self.hosts: Dict[str, Host] = {}
        self.stats: Dict[str, HostStats] = {}
        self.timers: Dict[str, QTimer] = {}
        self.thread_pool = QThreadPool.globalInstance()
        self.is_monitoring = False
        self.unreachable_hosts: set = set()

    def add_host(self, host: Host) -> None:
        self.hosts[host.id] = host
        self.stats[host.id] = HostStats(host_id=host.id)
        if self.is_monitoring and host.enabled:
            self._start_timer(host)

    def remove_host(self, host_id: str) -> None:
        self._stop_timer(host_id)
        self.hosts.pop(host_id, None)
        self.stats.pop(host_id, None)
        self.unreachable_hosts.discard(host_id)

    def update_host(self, updated_host: Host) -> None:
        self.hosts[updated_host.id] = updated_host
        self._stop_timer(updated_host.id)
        if self.is_monitoring and updated_host.enabled:
            self._start_timer(updated_host)

    def set_settings(self, settings: AppSettings) -> None:
        self.settings = settings
        if self.is_monitoring:
            for host_id, timer in list(self.timers.items()):
                host = self.hosts.get(host_id)
                if host and host.enabled:
                    self._start_timer(host)

    def start(self) -> None:
        if self.is_monitoring:
            return
        self.is_monitoring = True
        for host in self.hosts.values():
            if host.enabled:
                self._start_timer(host)

    def stop(self) -> None:
        if not self.is_monitoring:
            return
        self.is_monitoring = False
        for host_id in list(self.timers.keys()):
            self._stop_timer(host_id)
        self.thread_pool.waitForDone(1000)

    def clear_history(self, host_id: str) -> None:
        stats = self.stats.get(host_id)
        if stats:
            stats.packets_sent = 0
            stats.packets_received = 0
            stats.consecutive_failures = 0
            stats.min_latency = None
            stats.max_latency = None
            stats.avg_latency = None
            stats.latency_history.clear()
            stats.results_history.clear()
            stats.uptime_percentage = 100.0
            self.unreachable_hosts.discard(host_id)
            self.stats_updated.emit(host_id, stats)

    def _start_timer(self, host: Host) -> None:
        self._stop_timer(host.id)
        timer = QTimer(self)
        interval_sec = host.interval if host.interval is not None else self.settings.default_interval
        timer.setInterval(interval_sec * 1000)
        timer.timeout.connect(lambda: self._trigger_ping(host.id))
        self.timers[host.id] = timer
        timer.start()
        self._trigger_ping(host.id)

    def _stop_timer(self, host_id: str) -> None:
        timer = self.timers.pop(host_id, None)
        if timer:
            timer.stop()
            timer.deleteLater()

    def _trigger_ping(self, host_id: str) -> None:
        host = self.hosts.get(host_id)
        if not host or not host.enabled:
            return
        worker = PingWorker(host_id, host.address, self.settings.default_timeout * 1000, self.ping_service)
        worker.signals.completed.connect(self._on_ping_completed)
        self.thread_pool.start(worker)

    def _on_ping_completed(self, host_id: str, result: PingResult) -> None:
        host = self.hosts.get(host_id)
        stats = self.stats.get(host_id)
        if not host or not stats:
            return

        stats.packets_sent += 1
        stats.results_history.append(result)
        if len(stats.results_history) > self.settings.history_retention:
            stats.results_history.pop(0)

        if result.success:
            stats.packets_received += 1
            stats.consecutive_failures = 0
            lat = result.latency
            if lat is not None:
                stats.latency_history.append(lat)
                if len(stats.latency_history) > self.settings.history_retention:
                    stats.latency_history.pop(0)
                
                if stats.min_latency is None or lat < stats.min_latency:
                    stats.min_latency = lat
                if stats.max_latency is None or lat > stats.max_latency:
                    stats.max_latency = lat
                
                if stats.avg_latency is None:
                    stats.avg_latency = lat
                else:
                    stats.avg_latency = ((stats.avg_latency * (stats.packets_received - 1)) + lat) / stats.packets_received

            if host_id in self.unreachable_hosts:
                self.unreachable_hosts.discard(host_id)
                self.alert_triggered.emit(host_id, f"Host {host.name or host.address} is reachable again.", "Info")

            if lat is not None:
                if lat >= self.settings.latency_critical_ms:
                    self.alert_triggered.emit(host_id, f"Host {host.name or host.address} latency critical: {lat:.1f}ms", "Critical")
                elif lat >= self.settings.latency_warning_ms:
                    self.alert_triggered.emit(host_id, f"Host {host.name or host.address} latency warning: {lat:.1f}ms", "Warning")
        else:
            stats.consecutive_failures += 1
            if stats.consecutive_failures >= 3 and host_id not in self.unreachable_hosts:
                self.unreachable_hosts.add(host_id)
                self.alert_triggered.emit(host_id, f"Host {host.name or host.address} became unreachable.", "Critical")

        stats.uptime_percentage = (stats.packets_received / stats.packets_sent) * 100.0
        
        loss_pct = ((stats.packets_sent - stats.packets_received) / stats.packets_sent) * 100.0
        if loss_pct >= self.settings.packet_loss_threshold and stats.packets_sent >= 5:
            self.alert_triggered.emit(host_id, f"Host {host.name or host.address} high packet loss: {loss_pct:.1f}%", "Warning")

        self.ping_completed.emit(host_id, result)
        self.stats_updated.emit(host_id, stats)
