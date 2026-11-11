"""记忆查看小部件模块"""
from PyQt6.QtWidgets import QLabel, QTextEdit, QPushButton, QHBoxLayout, QMessageBox
from ui.components.base_widget import BaseFloatingWidget


class MemoryWidget(BaseFloatingWidget):
    """记忆查看小部件"""

    def __init__(self, agent, parent=None):
        super().__init__("记忆系统", 350, 400, parent)
        self.agent = agent

        self.stats_label = QLabel()
        self.stats_label.setStyleSheet(
            "font-size: 11px; color: #666; background: rgba(240,240,240,0.8); "
            "border-radius: 6px; padding: 6px;"
        )
        self.stats_label.setWordWrap(True)
        self._layout.addWidget(self.stats_label)

        self.memory_list = QTextEdit()
        self.memory_list.setReadOnly(True)
        self.memory_list.setStyleSheet(
            "font-size: 12px; background: rgba(255,255,255,0.9); "
            "border-radius: 8px; padding: 4px;"
        )
        self._layout.addWidget(self.memory_list)

        btn_layout = QHBoxLayout()
        refresh_btn = QPushButton("刷新")
        refresh_btn.setStyleSheet("background: rgba(186,85,211,0.3); border-radius: 6px; padding: 6px;")
        refresh_btn.clicked.connect(self.refresh)
        btn_layout.addWidget(refresh_btn)

        clear_btn = QPushButton("清空长期记忆")
        clear_btn.setStyleSheet("background: rgba(255,100,100,0.3); border-radius: 6px; padding: 6px;")
        clear_btn.clicked.connect(self.clear_long_memory)
        btn_layout.addWidget(clear_btn)
        self._layout.addLayout(btn_layout)

        self.refresh()

    def refresh(self):
        viewer = self.agent.memory.get_viewer()
        self.stats_label.setText(viewer.format_stats())
        self.memory_list.setText(viewer.format_memory_list(viewer.get_recent(20)))

    def clear_long_memory(self):
        reply = QMessageBox.question(
            self, "确认", "确定要清空所有长期记忆吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self.agent.memory.clear_long()
            self.refresh()