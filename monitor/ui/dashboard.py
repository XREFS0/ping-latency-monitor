from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QLabel, QFrame
from PySide6.QtGui import QFont, QColor

class MetricCard(QFrame):
    def __init__(self, title: str, val: str, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Plain)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(4)
        
        self.title_label = QLabel(title)
        self.title_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        title_font = QFont("Segoe UI", 9)
        self.title_label.setFont(title_font)
        self.title_label.setStyleSheet("color: #888888;")
        
        self.val_label = QLabel(val)
        self.val_label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
        val_font = QFont("Segoe UI", 16, QFont.Bold)
        self.val_label.setFont(val_font)
        
        layout.addWidget(self.title_label)
        layout.addWidget(self.val_label)
        

    def update_value(self, val: str, color_stylesheet: Optional[str] = None) -> None:
        self.val_label.setText(val)
        if color_stylesheet:
            self.val_label.setStyleSheet(color_stylesheet)
        else:
            self.val_label.setStyleSheet("")

class DashboardWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 10)
        layout.setSpacing(10)
        
        self.card_total = MetricCard("Total Hosts", "0")
        self.card_online = MetricCard("Online", "0")
        self.card_offline = MetricCard("Offline", "0")
        self.card_avg_lat = MetricCard("Avg Latency", "N/A")
        self.card_max_lat = MetricCard("Max Latency", "N/A")
        self.card_loss = MetricCard("Avg Packet Loss", "0.0%")
        
        layout.addWidget(self.card_total)
        layout.addWidget(self.card_online)
        layout.addWidget(self.card_offline)
        layout.addWidget(self.card_avg_lat)
        layout.addWidget(self.card_max_lat)
        layout.addWidget(self.card_loss)

    def update_metrics(self, total: int, online: int, offline: int, avg_lat: Optional[float], max_lat: Optional[float], avg_loss: float) -> None:
        self.card_total.update_value(str(total))
        self.card_online.update_value(str(online), "color: #66BB6A;" if online > 0 else None)
        self.card_offline.update_value(str(offline), "color: #EF5350;" if offline > 0 else None)
        
        avg_str = f"{avg_lat:.1f} ms" if avg_lat is not None else "N/A"
        self.card_avg_lat.update_value(avg_str)
        
        max_str = f"{max_lat:.1f} ms" if max_lat is not None else "N/A"
        self.card_max_lat.update_value(max_str)
        
        loss_color = "color: #EF5350;" if avg_loss > 5.0 else "color: #FFA726;" if avg_loss > 1.0 else None
        self.card_loss.update_value(f"{avg_loss:.1f}%", loss_color)
