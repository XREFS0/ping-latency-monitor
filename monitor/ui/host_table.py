import time
from typing import List, Dict, Optional, Any
from PySide6.QtCore import Qt, QAbstractTableModel, QModelIndex
from PySide6.QtGui import QColor, QBrush
from monitor.models import Host, HostStats

class HostTableModel(QAbstractTableModel):
    def __init__(self, hosts: List[Host], stats: Dict[str, HostStats]) -> None:
        super().__init__()
        self.hosts = hosts
        self.stats = stats
        self.headers = [
            "Enabled", "Status", "Name", "Address", 
            "Current", "Avg", "Min", "Max", 
            "Loss", "Uptime", "Last Response"
        ]

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.hosts)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return len(self.headers)

    def data(self, index: QModelIndex, role: int = Qt.DisplayRole) -> Any:
        if not index.isValid() or not (0 <= index.row() < len(self.hosts)):
            return None

        host = self.hosts[index.row()]
        stats = self.stats.get(host.id)
        col = index.column()

        if role == Qt.CheckStateRole and col == 0:
            return Qt.Checked if host.enabled else Qt.Unchecked

        if role == Qt.DisplayRole:
            if col == 0:
                return ""
            elif col == 1:
                if not host.enabled:
                    return "Disabled"
                if not stats or stats.packets_sent == 0:
                    return "Pending"
                return "Online" if stats.consecutive_failures == 0 else "Offline"
            elif col == 2:
                return host.name or "-"
            elif col == 3:
                return host.address
            elif col == 4:
                if not stats or not stats.results_history:
                    return "-"
                last_res = stats.results_history[-1]
                return f"{last_res.latency:.1f} ms" if last_res.success and last_res.latency is not None else "Timeout"
            elif col == 5:
                return f"{stats.avg_latency:.1f} ms" if stats and stats.avg_latency is not None else "-"
            elif col == 6:
                return f"{stats.min_latency:.1f} ms" if stats and stats.min_latency is not None else "-"
            elif col == 7:
                return f"{stats.max_latency:.1f} ms" if stats and stats.max_latency is not None else "-"
            elif col == 8:
                if not stats or stats.packets_sent == 0:
                    return "0.0%"
                loss = ((stats.packets_sent - stats.packets_received) / stats.packets_sent) * 100.0
                return f"{loss:.1f}%"
            elif col == 9:
                return f"{stats.uptime_percentage:.1f}%" if stats else "100.0%"
            elif col == 10:
                if not stats or not stats.results_history:
                    return "-"
                for res in reversed(stats.results_history):
                    if res.success:
                        t = time.localtime(res.timestamp)
                        return time.strftime("%H:%M:%S", t)
                return "Never"

        if role == Qt.ForegroundRole:
            if col == 1:
                if not host.enabled:
                    return QBrush(QColor(120, 120, 120))
                if not stats or stats.packets_sent == 0:
                    return QBrush(QColor(255, 167, 38))
                return QBrush(QColor(102, 187, 106)) if stats.consecutive_failures == 0 else QBrush(QColor(239, 83, 80))
            if col == 4 and stats and stats.results_history:
                last_res = stats.results_history[-1]
                if not last_res.success:
                    return QBrush(QColor(239, 83, 80))

        if role == Qt.TextAlignmentRole:
            if col in [0, 1, 4, 5, 6, 7, 8, 9, 10]:
                return Qt.AlignCenter
            return Qt.AlignLeft | Qt.AlignVCenter

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role: int = Qt.DisplayRole) -> Any:
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return self.headers[section]
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlags:
        if not index.isValid():
            return Qt.NoItemFlags
        flags = Qt.ItemIsSelectable | Qt.ItemIsEnabled
        if index.column() == 0:
            flags |= Qt.ItemIsUserCheckable
        return flags

    def setData(self, index: QModelIndex, value: Any, role: int = Qt.EditRole) -> bool:
        if index.isValid() and index.column() == 0 and role == Qt.CheckStateRole:
            host = self.hosts[index.row()]
            host.enabled = (value == Qt.Checked)
            self.dataChanged.emit(index, index, [role])
            return True
        return False

    def update_host_data(self, host_id: str) -> None:
        for row, host in enumerate(self.hosts):
            if host.id == host_id:
                self.dataChanged.emit(self.index(row, 0), self.index(row, len(self.headers) - 1))
                break

    def refresh_all(self) -> None:
        self.layoutChanged.emit()
