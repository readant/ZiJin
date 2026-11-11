"""安全审计日志小部件模块"""
import json
from PyQt6.QtWidgets import QTextEdit, QPushButton, QHBoxLayout
from tools.audit import audit
from ui.components.base_widget import BaseFloatingWidget


class AuditWidget(BaseFloatingWidget):
    """安全审计日志小部件"""

    def __init__(self, parent=None):
        super().__init__("安全审计日志", 400, 350, parent)

        self.log_list = QTextEdit()
        self.log_list.setReadOnly(True)
        self.log_list.setStyleSheet(
            "font-size: 11px; font-family: monospace; background: rgba(255,255,255,0.9); "
            "border-radius: 8px; padding: 4px;"
        )
        self._layout.addWidget(self.log_list)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("background: rgba(186,85,211,0.3); border-radius: 6px; padding: 6px;")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        blocked_btn = QPushButton("仅看拦截")
        blocked_btn.setStyleSheet("background: rgba(255,100,100,0.3); border-radius: 6px; padding: 6px;")
        blocked_btn.clicked.connect(self.show_blocked)
        btn_layout.addWidget(blocked_btn)
        self._layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        self.log_list.setText(audit.format_recent(30))

    def show_blocked(self):
        entries = audit.get_blocked(30)
        if not entries:
            self.log_list.setText("暂无拦截记录")
            return
        lines = []
        for e in reversed(entries):
            ts = e.get("ts", "?")[:19]
            tool = e.get("tool", "?")
            err = e.get("error", "")
            args_str = json.dumps(e.get("args", {}), ensure_ascii=False)
            lines.append(f"{ts} [BLOCKED] {tool}: {err}\n  args: {args_str}")
        self.log_list.setText("\n\n".join(lines))