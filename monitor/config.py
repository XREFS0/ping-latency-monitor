import json
import os
from typing import List, Dict, Any
from monitor.models import AppSettings, Host

class ConfigManager:
    def __init__(self) -> None:
        self.config_dir = os.path.join(os.path.expanduser("~"), ".ping_latency_monitor")
        os.makedirs(self.config_dir, exist_ok=True)
        self.settings_path = os.path.join(self.config_dir, "settings.json")
        self.hosts_path = os.path.join(self.config_dir, "hosts.json")

    def load_settings(self) -> AppSettings:
        if not os.path.exists(self.settings_path):
            return AppSettings()
        try:
            with open(self.settings_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return AppSettings(**data)
        except Exception:
            return AppSettings()

    def save_settings(self, settings: AppSettings) -> None:
        try:
            with open(self.settings_path, "w", encoding="utf-8") as f:
                json.dump(settings.__dict__, f, indent=4)
        except Exception:
            pass

    def load_hosts(self) -> List[Host]:
        if not os.path.exists(self.hosts_path):
            return []
        try:
            with open(self.hosts_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                hosts = []
                for item in data:
                    hosts.append(Host(
                        address=item["address"],
                        name=item.get("name", ""),
                        interval=item.get("interval"),
                        enabled=item.get("enabled", True),
                        id=item.get("id")
                    ))
                return hosts
        except Exception:
            return []

    def save_hosts(self, hosts: List[Host]) -> None:
        try:
            with open(self.hosts_path, "w", encoding="utf-8") as f:
                data = []
                for host in hosts:
                    data.append({
                        "address": host.address,
                        "name": host.name,
                        "interval": host.interval,
                        "enabled": host.enabled,
                        "id": host.id
                    })
                json.dump(data, f, indent=4)
        except Exception:
            pass
