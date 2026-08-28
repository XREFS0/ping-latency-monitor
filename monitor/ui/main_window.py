import os
import time
from typing import Optional, List
from PySide6.QtCore import Qt, QModelIndex
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, 
    QTableView, QSplitter, QTextEdit, QFileDialog, QMessageBox,
    QAbstractItemView, QLabel, QHeaderView
)
from PySide6.QtGui import QAction, QIcon
from monitor.models import Host, AppSettings, HostStats, PingResult
from monitor.config import ConfigManager
from monitor.engine import MonitorEngine
from monitor.export import ExportService
from monitor.ui.dashboard import DashboardWidget
from monitor.ui.host_table import HostTableModel
from monitor.ui.graph import LatencyGraphWidget
from monitor.ui.dialogs import HostDialog, SettingsDialog

class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("Ping & Latency Monitor")
        self.resize(1000, 700)

        self.config_manager = ConfigManager()
        self.settings = self.config_manager.load_settings()
        self.hosts = self.config_manager.load_hosts()

        self.engine = MonitorEngine(self.settings)
        for host in self.hosts:
            self.engine.add_host(host)

        self.selected_host_id: Optional[str] = None
        self.setup_ui()
        self.apply_theme(self.settings.theme)

        self.engine.ping_completed.connect(self._on_ping_completed)
        self.engine.stats_updated.connect(self._on_stats_updated)
        self.engine.alert_triggered.connect(self._on_alert_triggered)

        if self.settings.auto_start:
            self.toggle_monitoring()

    def setup_ui(self) -> None:
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(10)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.setSpacing(6)

        self.btn_toggle = QPushButton("Start Monitoring")
        self.btn_toggle.clicked.connect(self.toggle_monitoring)
        toolbar_layout.addWidget(self.btn_toggle)

        self.btn_add = QPushButton("Add Host")
        self.btn_add.clicked.connect(self.add_host)
        toolbar_layout.addWidget(self.btn_add)

        self.btn_edit = QPushButton("Edit Host")
        self.btn_edit.clicked.connect(self.edit_host)
        self.btn_edit.setEnabled(False)
        toolbar_layout.addWidget(self.btn_edit)

        self.btn_remove = QPushButton("Remove Host")
        self.btn_remove.clicked.connect(self.remove_host)
        self.btn_remove.setEnabled(False)
        toolbar_layout.addWidget(self.btn_remove)

        self.btn_clear_history = QPushButton("Clear History")
        self.btn_clear_history.clicked.connect(self.clear_history)
        self.btn_clear_history.setEnabled(False)
        toolbar_layout.addWidget(self.btn_clear_history)

        self.btn_export = QPushButton("Export CSV")
        self.btn_export.clicked.connect(self.export_csv)
        toolbar_layout.addWidget(self.btn_export)

        self.btn_settings = QPushButton("Settings")
        self.btn_settings.clicked.connect(self.open_settings)
        toolbar_layout.addWidget(self.btn_settings)

        toolbar_layout.addStretch()
        main_layout.addLayout(toolbar_layout)

        self.dashboard = DashboardWidget()
        main_layout.addWidget(self.dashboard)

        splitter = QSplitter(Qt.Vertical)

        mid_splitter = QSplitter(Qt.Horizontal)
        
        self.table_model = HostTableModel(self.hosts, self.engine.stats)
        self.table_view = QTableView()
        self.table_view.setModel(self.table_model)
        self.table_view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table_view.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table_view.doubleClicked.connect(self.edit_host)
        
        header = self.table_view.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(True)
        
        self.table_view.selectionModel().selectionChanged.connect(self._on_table_selection_changed)
        self.table_model.dataChanged.connect(self._on_table_data_changed)
        mid_splitter.addWidget(self.table_view)

        self.graph_widget = LatencyGraphWidget()
        self.graph_widget.set_thresholds(self.settings.latency_warning_ms, self.settings.latency_critical_ms)
        mid_splitter.addWidget(self.graph_widget)

        mid_splitter.setSizes([600, 400])
        splitter.addWidget(mid_splitter)

        bottom_widget = QWidget()
        bottom_layout = QVBoxLayout(bottom_widget)
        bottom_layout.setContentsMargins(0, 0, 0, 0)
        
        alerts_header = QHBoxLayout()
        alerts_header.addWidget(QLabel("Alerts & Activity Log"))
        alerts_header.addStretch()
        btn_clear_logs = QPushButton("Clear Logs")
        btn_clear_logs.clicked.connect(self.clear_logs)
        alerts_header.addWidget(btn_clear_logs)
        bottom_layout.addLayout(alerts_header)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        bottom_layout.addWidget(self.log_area)
        
        bottom_widget.setMinimumHeight(120)
        splitter.addWidget(bottom_widget)

        splitter.setSizes([450, 150])
        main_layout.addWidget(splitter)

        self.update_dashboard()

    def toggle_monitoring(self) -> None:
        if self.engine.is_monitoring:
            self.engine.stop()
            self.btn_toggle.setText("Start Monitoring")
            self.btn_toggle.setStyleSheet("")
        else:
            self.engine.start()
            self.btn_toggle.setText("Stop Monitoring")
            self.btn_toggle.setStyleSheet("background-color: #C62828; color: white;")
        self.update_dashboard()

    def add_host(self) -> None:
        dialog = HostDialog(parent=self)
        if dialog.exec() == HostDialog.Accepted:
            new_host = dialog.get_host_data()
            self.hosts.append(new_host)
            self.engine.add_host(new_host)
            self.config_manager.save_hosts(self.hosts)
            self.table_model.refresh_all()
            self.update_dashboard()

    def edit_host(self) -> None:
        selected_index = self.table_view.currentIndex()
        if not selected_index.isValid():
            return
        row = selected_index.row()
        host = self.hosts[row]
        
        dialog = HostDialog(host=host, parent=self)
        if dialog.exec() == HostDialog.Accepted:
            updated_host = dialog.get_host_data()
            self.hosts[row] = updated_host
            self.engine.update_host(updated_host)
            self.config_manager.save_hosts(self.hosts)
            self.table_model.refresh_all()
            self.update_dashboard()

    def remove_host(self) -> None:
        selected_index = self.table_view.currentIndex()
        if not selected_index.isValid():
            return
        row = selected_index.row()
        host = self.hosts[row]

        reply = QMessageBox.question(
            self, "Confirm Delete", 
            f"Are you sure you want to remove {host.name or host.address}?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.engine.remove_host(host.id)
            self.hosts.pop(row)
            self.config_manager.save_hosts(self.hosts)
            self.table_model.refresh_all()
            self.selected_host_id = None
            self.graph_widget.set_results([], self.settings.history_retention)
            self.update_dashboard()

    def clear_history(self) -> None:
        if not self.selected_host_id:
            return
        self.engine.clear_history(self.selected_host_id)
        self.graph_widget.set_results([], self.settings.history_retention)
        self.update_dashboard()

    def clear_logs(self) -> None:
        self.log_area.clear()

    def export_csv(self) -> None:
        if not self.hosts:
            QMessageBox.warning(self, "Export Warning", "No host data available to export.")
            return

        filepath, _ = QFileDialog.getSaveFileName(self, "Export CSV", "", "CSV Files (*.csv)")
        if not filepath:
            return

        try:
            ExportService.export_stats_to_csv(filepath, self.hosts, self.engine.stats)
            QMessageBox.information(self, "Success", "Export completed successfully.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to export CSV: {str(e)}")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec() == SettingsDialog.Accepted:
            new_settings = dialog.get_settings()
            
            theme_changed = new_settings.theme != self.settings.theme
            history_changed = new_settings.history_retention != self.settings.history_retention
            
            self.settings = new_settings
            self.config_manager.save_settings(self.settings)
            
            self.engine.set_settings(self.settings)
            self.graph_widget.set_thresholds(self.settings.latency_warning_ms, self.settings.latency_critical_ms)
            
            if theme_changed:
                self.apply_theme(self.settings.theme)
            if history_changed and self.selected_host_id:
                stats = self.engine.stats.get(self.selected_host_id)
                if stats:
                    self.graph_widget.set_results(stats.results_history, self.settings.history_retention)
                    
            self.table_model.refresh_all()
            self.update_dashboard()

    def update_dashboard(self) -> None:
        total = len(self.hosts)
        online = 0
        offline = 0
        sum_lat = 0.0
        cnt_lat = 0
        max_lat: Optional[float] = None
        sum_loss = 0.0
        cnt_loss = 0

        for host in self.hosts:
            stats = self.engine.stats.get(host.id)
            if not stats:
                continue
            if host.enabled:
                if stats.packets_sent > 0:
                    if stats.consecutive_failures == 0:
                        online += 1
                    else:
                        offline += 1
                    
                    if stats.avg_latency is not None:
                        sum_lat += stats.avg_latency
                        cnt_lat += 1
                        if max_lat is None or stats.avg_latency > max_lat:
                            max_lat = stats.avg_latency
                    
                    loss = ((stats.packets_sent - stats.packets_received) / stats.packets_sent) * 100.0
                    sum_loss += loss
                    cnt_loss += 1
                else:
                    pass

        avg_lat = (sum_lat / cnt_lat) if cnt_lat > 0 else None
        avg_loss = (sum_loss / cnt_loss) if cnt_loss > 0 else 0.0

        self.dashboard.update_metrics(total, online, offline, avg_lat, max_lat, avg_loss)

    def apply_theme(self, theme_name: str) -> None:
        if theme_name == "Dark":
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #121212;
                }
                QWidget {
                    background-color: #121212;
                    color: #E0E0E0;
                    font-family: "Segoe UI", "Segoe UI Semibold", sans-serif;
                }
                QTableView {
                    background-color: #1E1E1E;
                    gridline-color: #2D2D2D;
                    border: 1px solid #2D2D2D;
                    selection-background-color: #333333;
                    selection-color: #FFFFFF;
                }
                QHeaderView::section {
                    background-color: #252526;
                    color: #A0A0A0;
                    border: 1px solid #2D2D2D;
                    padding: 4px;
                }
                QPushButton {
                    background-color: #252526;
                    border: 1px solid #333333;
                    border-radius: 3px;
                    padding: 5px 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #2D2D2D;
                    border-color: #444444;
                }
                QPushButton:pressed {
                    background-color: #1E1E1E;
                }
                QPushButton:disabled {
                    background-color: #151515;
                    color: #555555;
                    border-color: #202020;
                }
                QTextEdit {
                    background-color: #1E1E1E;
                    border: 1px solid #2D2D2D;
                    font-family: Consolas, monospace;
                    font-size: 9pt;
                }
                QSplitter::handle {
                    background-color: #2D2D2D;
                }
                MetricCard {
                    background-color: #1E1E1E;
                    border: 1px solid #2D2D2D;
                    border-radius: 4px;
                }
                MetricCard QLabel {
                    background-color: transparent;
                }
            """)
        else:
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #F3F3F3;
                }
                QWidget {
                    background-color: #F3F3F3;
                    color: #2C2C2C;
                    font-family: "Segoe UI", sans-serif;
                }
                QTableView {
                    background-color: #FFFFFF;
                    gridline-color: #E0E0E0;
                    border: 1px solid #CCCCCC;
                    selection-background-color: #E5E5E5;
                    selection-color: #000000;
                }
                QHeaderView::section {
                    background-color: #EAEAEA;
                    color: #404040;
                    border: 1px solid #CCCCCC;
                    padding: 4px;
                }
                QPushButton {
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    border-radius: 3px;
                    padding: 5px 12px;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #F7F7F7;
                    border-color: #BBBBBB;
                }
                QPushButton:pressed {
                    background-color: #EAEAEA;
                }
                QPushButton:disabled {
                    background-color: #F3F3F3;
                    color: #AAAAAA;
                    border-color: #E0E0E0;
                }
                QTextEdit {
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    font-family: Consolas, monospace;
                    font-size: 9pt;
                }
                QSplitter::handle {
                    background-color: #CCCCCC;
                }
                MetricCard {
                    background-color: #FFFFFF;
                    border: 1px solid #CCCCCC;
                    border-radius: 4px;
                }
                MetricCard QLabel {
                    background-color: transparent;
                }
            """)

    def _on_table_selection_changed(self) -> None:
        selected_index = self.table_view.currentIndex()
        if selected_index.isValid():
            row = selected_index.row()
            host = self.hosts[row]
            self.selected_host_id = host.id
            self.btn_edit.setEnabled(True)
            self.btn_remove.setEnabled(True)
            self.btn_clear_history.setEnabled(True)
            
            stats = self.engine.stats.get(host.id)
            if stats:
                self.graph_widget.set_results(stats.results_history, self.settings.history_retention)
            else:
                self.graph_widget.set_results([], self.settings.history_retention)
        else:
            self.selected_host_id = None
            self.btn_edit.setEnabled(False)
            self.btn_remove.setEnabled(False)
            self.btn_clear_history.setEnabled(False)
            self.graph_widget.set_results([], self.settings.history_retention)

    def _on_table_data_changed(self, top_left: QModelIndex, bottom_right: QModelIndex, roles: List[int]) -> None:
        if Qt.CheckStateRole in roles:
            for row in range(top_left.row(), bottom_right.row() + 1):
                host = self.hosts[row]
                if host.enabled:
                    self.engine.update_host(host)
                else:
                    self.engine.remove_host(host.id)
                    self.engine.add_host(host)
            self.config_manager.save_hosts(self.hosts)
            self.update_dashboard()

    def _on_ping_completed(self, host_id: str, result: PingResult) -> None:
        if host_id == self.selected_host_id:
            stats = self.engine.stats.get(host_id)
            if stats:
                self.graph_widget.set_results(stats.results_history, self.settings.history_retention)

    def _on_stats_updated(self, host_id: str, stats: HostStats) -> None:
        self.table_model.update_host_data(host_id)
        self.update_dashboard()

    def _on_alert_triggered(self, host_id: str, message: str, severity: str) -> None:
        timestamp = time.strftime("%H:%M:%S")
        log_msg = f"[{timestamp}] [{severity.upper()}] {message}"
        self.log_area.append(log_msg)

    def closeEvent(self, event) -> None:
        self.engine.stop()
        super().closeEvent(event)
