import uuid
from dataclasses import dataclass, field
from typing import List, Optional

@dataclass
class Host:
    address: str
    name: str = ""
    interval: Optional[int] = None
    enabled: bool = True
    id: str = field(default_factory=lambda: str(uuid.uuid4()))

@dataclass
class PingResult:
    timestamp: float
    latency: Optional[float]
    success: bool
    error_message: Optional[str] = None

@dataclass
class HostStats:
    host_id: str
    packets_sent: int = 0
    packets_received: int = 0
    consecutive_failures: int = 0
    min_latency: Optional[float] = None
    max_latency: Optional[float] = None
    avg_latency: Optional[float] = None
    latency_history: List[float] = field(default_factory=list)
    results_history: List[PingResult] = field(default_factory=list)
    uptime_percentage: float = 100.0

@dataclass
class AlertConfig:
    latency_threshold_ms: float = 200.0
    packet_loss_threshold_pct: float = 10.0
    unreachable_alert: bool = True
    recovery_alert: bool = True

@dataclass
class AppSettings:
    default_interval: int = 5
    default_timeout: int = 2
    latency_warning_ms: float = 100.0
    latency_critical_ms: float = 250.0
    packet_loss_threshold: float = 5.0
    history_retention: int = 100
    auto_start: bool = True
    theme: str = "Dark"
