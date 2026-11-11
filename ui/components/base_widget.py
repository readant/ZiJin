"""浮动窗口基类模块"""
from PyQt6.QtWidgets import QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout
from PyQt6.QtCore import Qt


class BaseFloatingWidget(QWidget):
    """浮动窗口基类 - 提供标题栏、关闭按钮、拖拽功能"""

    def __init__(self, title: str, width: int, height: int, parent=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(width, height)
        self._drag_pos = None

        self._layout = QVBoxLayout(self)
        self._layout.setContentsMargins(8, 8, 8, 8)
        self._layout.setSpacing(6)

        # 标题栏
        title_layout = QHBoxLayout()
        title_label = QLabel(title)
        title_label.setStyleSheet("font-size: 13px; font-weight: bold; color: #333;")
        title_layout.addWidget(title_label)
        title_layout.addStretch()

        close_btn = QPushButton("×")
        close_btn.setFixedSize(24, 24)
        close_btn.setStyleSheet(
            "QPushButton { border: none; font-size: 16px; color: #999; }"
            "QPushButton:hover { color: #333; }"
        )
        close_btn.clicked.connect(self.hide)
        title_layout.addWidget(close_btn)

        self._layout.addLayout(title_layout)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None