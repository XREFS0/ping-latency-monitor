from typing import List, Optional
from PySide6.QtCore import Qt, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QBrush, QFont, QPaintEvent
from PySide6.QtWidgets import QWidget
from monitor.models import PingResult

class LatencyGraphWidget(QWidget):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.results: List[PingResult] = []
        self.max_history = 100
        self.warning_threshold = 100.0
        self.critical_threshold = 250.0
        self.setMinimumHeight(180)

    def set_results(self, results: List[PingResult], max_history: int) -> None:
        self.results = results
        self.max_history = max_history
        self.update()

    def set_thresholds(self, warning: float, critical: float) -> None:
        self.warning_threshold = warning
        self.critical_threshold = critical
        self.update()

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)

        width = self.width()
        height = self.height()
        margin_left = 50
        margin_right = 15
        margin_top = 20
        margin_bottom = 30

        plot_width = width - margin_left - margin_right
        plot_height = height - margin_top - margin_bottom

        is_dark = self.palette().window().color().lightness() < 128
        bg_color = QColor(30, 30, 30) if is_dark else QColor(245, 245, 245)
        grid_color = QColor(50, 50, 50) if is_dark else QColor(220, 220, 220)
        text_color = QColor(200, 200, 200) if is_dark else QColor(50, 50, 50)

        painter.fillRect(self.rect(), bg_color)

        painter.setPen(QPen(grid_color, 1, Qt.SolidLine))
        painter.drawRect(margin_left, margin_top, plot_width, plot_height)

        max_val = 50.0
        for res in self.results:
            if res.success and res.latency is not None:
                if res.latency > max_val:
                    max_val = res.latency
        max_y = max_val * 1.15

        painter.setPen(QPen(grid_color, 1, Qt.DashLine))
        font = QFont("Segoe UI", 8)
        painter.setFont(font)
        painter.setPen(text_color)

        for i in range(4):
            val = (max_y / 3) * i
            y = int(height - margin_bottom - (val / max_y) * plot_height)
            painter.setPen(QPen(grid_color, 1, Qt.DashLine))
            painter.drawLine(margin_left, y, width - margin_right, y)
            painter.setPen(text_color)
            painter.drawText(5, y + 4, f"{int(val)} ms")

        if not self.results:
            painter.drawText(margin_left + int(plot_width / 2) - 40, margin_top + int(plot_height / 2), "No Data")
            return

        points: List[QPointF] = []
        seg_width = plot_width / max(1, self.max_history - 1)
        start_idx = max(0, len(self.results) - self.max_history)
        visible_results = self.results[start_idx:]

        for i, res in enumerate(visible_results):
            x = margin_left + i * seg_width
            if res.success and res.latency is not None:
                y = height - margin_bottom - (res.latency / max_y) * plot_height
                points.append(QPointF(x, y))
            else:
                y_fail = height - margin_bottom
                painter.setPen(Qt.NoPen)
                painter.setBrush(QBrush(QColor(239, 83, 80, 80)))
                painter.drawRect(int(x - seg_width/2), margin_top, max(2, int(seg_width)), plot_height)

        if len(points) > 1:
            line_pen = QPen(QColor(66, 165, 245), 2, Qt.SolidLine)
            painter.setPen(line_pen)
            for i in range(len(points) - 1):
                painter.drawLine(points[i], points[i+1])

        painter.setPen(Qt.NoPen)
        for pt in points:
            y_val = height - margin_bottom - pt.y()
            latency_ms = (y_val / plot_height) * max_y
            
            if latency_ms >= self.critical_threshold:
                color = QColor(239, 83, 80)
            elif latency_ms >= self.warning_threshold:
                color = QColor(255, 167, 38)
            else:
                color = QColor(102, 187, 106)
                
            painter.setBrush(QBrush(color))
            painter.drawEllipse(pt, 3.5, 3.5)
            
        painter.setPen(text_color)
        painter.drawText(margin_left, height - 10, "Oldest")
        painter.drawText(width - margin_right - 35, height - 10, "Recent")
