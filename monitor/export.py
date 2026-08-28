import csv
from typing import List, Dict
from monitor.models import Host, HostStats

class ExportService:
    @staticmethod
    def export_stats_to_csv(filepath: str, hosts: List[Host], stats_map: Dict[str, HostStats]) -> None:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Host ID", 
                "Display Name", 
                "Address", 
                "Status", 
                "Packets Sent", 
                "Packets Received", 
                "Packet Loss (%)", 
                "Uptime (%)", 
                "Min Latency (ms)", 
                "Max Latency (ms)", 
                "Avg Latency (ms)"
            ])
            for host in hosts:
                stats = stats_map.get(host.id)
                if not stats:
                    continue
                loss = ((stats.packets_sent - stats.packets_received) / stats.packets_sent * 100.0) if stats.packets_sent > 0 else 0.0
                status = "Online" if stats.consecutive_failures == 0 and stats.packets_sent > 0 else "Offline" if stats.consecutive_failures > 0 else "Pending"
                writer.writerow([
                    host.id,
                    host.name,
                    host.address,
                    status,
                    stats.packets_sent,
                    stats.packets_received,
                    f"{loss:.2f}",
                    f"{stats.uptime_percentage:.2f}",
                    f"{stats.min_latency:.2f}" if stats.min_latency is not None else "N/A",
                    f"{stats.max_latency:.2f}" if stats.max_latency is not None else "N/A",
                    f"{stats.avg_latency:.2f}" if stats.avg_latency is not None else "N/A"
                ])
                
    @staticmethod
    def export_history_to_csv(filepath: str, host: Host, stats: HostStats) -> None:
        with open(filepath, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.writer(f)
            writer.writerow([
                "Timestamp",
                "Success",
                "Latency (ms)",
                "Error Message"
            ])
            for res in stats.results_history:
                writer.writerow([
                    res.timestamp,
                    "Yes" if res.success else "No",
                    f"{res.latency:.2f}" if res.latency is not None else "N/A",
                    res.error_message or ""
                ])
