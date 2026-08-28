import re
from typing import Optional
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, 
    QCheckBox, QSpinBox, QDoubleSpinBox, QComboBox, QPushButton, 
    QMessageBox, QFormLayout
)
from monitor.models import Host, AppSettings

class HostDialog(QDialog):
    def __init__(self, host: Optional[Host] = None, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.host = host
        self.setWindowTitle("Edit Host" if host else "Add Host")
        self.resize(350, 200)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.address_input = QLineEdit()
        self.address_input.setPlaceholderText("e.g. 8.8.8.8 or google.com")
        if host:
            self.address_input.setText(host.address)
        form_layout.addRow("Host / IP Address:", self.address_input)

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Optional Display Name")
        if host:
            self.name_input.setText(host.name)
        form_layout.addRow("Display Name:", self.name_input)

        self.interval_input = QSpinBox()
        self.interval_input.setRange(0, 86400)
        self.interval_input.setSpecialValueText("Use Default")
        self.interval_input.setValue(host.interval if host and host.interval is not None else 0)
        form_layout.addRow("Custom Interval (s):", self.interval_input)

        self.enabled_checkbox = QCheckBox()
        self.enabled_checkbox.setChecked(host.enabled if host else True)
        form_layout.addRow("Enabled:", self.enabled_checkbox)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_host_data(self) -> Host:
        addr = self.address_input.text().strip()
        name = self.name_input.text().strip()
        interval = self.interval_input.value()
        enabled = self.enabled_checkbox.isChecked()
        
        host_id = self.host.id if self.host else None
        
        return Host(
            address=addr,
            name=name,
            interval=interval if interval > 0 else None,
            enabled=enabled,
            id=host_id if host_id else None
        ) if host_id else Host(
            address=addr,
            name=name,
            interval=interval if interval > 0 else None,
            enabled=enabled
        )

    def accept(self) -> None:
        addr = self.address_input.text().strip()
        if not addr:
            QMessageBox.warning(self, "Validation Error", "Host/IP Address cannot be empty.")
            return
            
        pattern = re.compile(r"^[a-zA-Z0-9.\-_:]+$")
        if not pattern.match(addr):
            QMessageBox.warning(self, "Validation Error", "Invalid characters in Host/IP Address.")
            return

        super().accept()

class SettingsDialog(QDialog):
    def __init__(self, settings: AppSettings, parent: Optional[QDialog] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Settings")
        self.resize(400, 320)

        layout = QVBoxLayout(self)
        form_layout = QFormLayout()

        self.interval_spin = QSpinBox()
        self.interval_spin.setRange(1, 3600)
        self.interval_spin.setValue(settings.default_interval)
        form_layout.addRow("Default Ping Interval (s):", self.interval_spin)

        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(1, 30)
        self.timeout_spin.setValue(settings.default_timeout)
        form_layout.addRow("Default Timeout (s):", self.timeout_spin)

        self.warn_spin = QDoubleSpinBox()
        self.warn_spin.setRange(1.0, 10000.0)
        self.warn_spin.setValue(settings.latency_warning_ms)
        form_layout.addRow("Latency Warning (ms):", self.warn_spin)

        self.crit_spin = QDoubleSpinBox()
        self.crit_spin.setRange(1.0, 10000.0)
        self.crit_spin.setValue(settings.latency_critical_ms)
        form_layout.addRow("Latency Critical (ms):", self.crit_spin)

        self.loss_spin = QDoubleSpinBox()
        self.loss_spin.setRange(0.0, 100.0)
        self.loss_spin.setValue(settings.packet_loss_threshold)
        form_layout.addRow("Packet Loss Threshold (%):", self.loss_spin)

        self.history_spin = QSpinBox()
        self.history_spin.setRange(10, 10000)
        self.history_spin.setValue(settings.history_retention)
        form_layout.addRow("History Retention (pings):", self.history_spin)

        self.auto_start_check = QCheckBox()
        self.auto_start_check.setChecked(settings.auto_start)
        form_layout.addRow("Start Monitoring Automatically:", self.auto_start_check)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light"])
        self.theme_combo.setCurrentText(settings.theme)
        form_layout.addRow("Application Theme:", self.theme_combo)

        layout.addLayout(form_layout)

        btn_layout = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.clicked.connect(self.accept)
        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.clicked.connect(self.reject)

        btn_layout.addStretch()
        btn_layout.addWidget(self.save_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def get_settings(self) -> AppSettings:
        return AppSettings(
            default_interval=self.interval_spin.value(),
            default_timeout=self.timeout_spin.value(),
            latency_warning_ms=self.warn_spin.value(),
            latency_critical_ms=self.crit_spin.value(),
            packet_loss_threshold=self.loss_spin.value(),
            history_retention=self.history_spin.value(),
            auto_start=self.auto_start_check.isChecked(),
            theme=self.theme_combo.currentText()
        )
