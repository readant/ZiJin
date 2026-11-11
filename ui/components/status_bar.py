"""状态指示器组件模块"""
from PyQt6.QtWidgets import QWidget, QHBoxLayout, QLabel, QPushButton
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont, QColor, QPainter
from core.log import get_logger

log = get_logger("status_bar")


class StatusIndicator(QLabel):
    """状态指示点"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(12, 12)
        self._status = "disconnected"
        self._update_style()

    def set_status(self, status: str):
        """
        设置状态
        
        Args:
            status: connected, disconnected, loading, error
        """
        self._status = status
        self._update_style()

    def _update_style(self):
        """更新样式"""
        colors = {
            "connected": "#4CAF50",      # 绿色
            "disconnected": "#9E9E9E",   # 灰色
            "loading": "#FFC107",        # 黄色
            "error": "#F44336",          # 红色
            "thinking": "#2196F3",       # 蓝色
        }
        color = colors.get(self._status, "#9E9E9E")
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: 6px;
                border: 1px solid rgba(0,0,0,0.1);
            }}
        """)


class StatusBar(QWidget):
    """状态栏组件"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("statusBar")
        self.setFixedHeight(28)
        # 用 id 选择器限定背景，避免 QWidget 选择器级联到所有子标签
        # （否则每个 QLabel 都会被套上一层灰白底，在深色背景下格外突兀）
        self.setStyleSheet("""
            #statusBar {
                background: rgba(240, 240, 240, 0.62);
                border-top: 1px solid rgba(200, 200, 200, 0.35);
            }
        """)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 2, 8, 2)
        layout.setSpacing(8)

        # LLM连接状态
        self.llm_indicator = StatusIndicator()
        layout.addWidget(self.llm_indicator)

        self.llm_label = QLabel("LLM")
        self.llm_label.setStyleSheet(
            "background: transparent; font-size: 10px; color: #666;")
        layout.addWidget(self.llm_label)

        # 记忆状态
        self.memory_indicator = StatusIndicator()
        layout.addWidget(self.memory_indicator)

        self.memory_label = QLabel("记忆")
        self.memory_label.setStyleSheet(
            "background: transparent; font-size: 10px; color: #666;")
        layout.addWidget(self.memory_label)

        # 工具状态
        self.tool_indicator = StatusIndicator()
        layout.addWidget(self.tool_indicator)

        self.tool_label = QLabel("工具")
        self.tool_label.setStyleSheet(
            "background: transparent; font-size: 10px; color: #666;")
        layout.addWidget(self.tool_label)

        layout.addStretch()

        # 状态文本
        self.status_text = QLabel("就绪")
        self.status_text.setStyleSheet(
            "background: transparent; font-size: 10px; color: #888;")
        layout.addWidget(self.status_text)

    def set_llm_status(self, status: str, text: str = ""):
        """设置LLM状态"""
        self.llm_indicator.set_status(status)
        if text:
            self.llm_label.setText(text)

    def set_memory_status(self, status: str, text: str = ""):
        """设置记忆状态"""
        self.memory_indicator.set_status(status)
        if text:
            self.memory_label.setText(text)

    def set_tool_status(self, status: str, text: str = ""):
        """设置工具状态"""
        self.tool_indicator.set_status(status)
        if text:
            self.tool_label.setText(text)

    def set_status_text(self, text: str):
        """设置状态文本"""
        self.status_text.setText(text)

    def show_thinking(self):
        """显示思考状态"""
        self.llm_indicator.set_status("thinking")
        self.set_status_text("思考中...")

    def show_connected(self):
        """显示已连接状态"""
        self.llm_indicator.set_status("connected")
        self.set_status_text("就绪")

    def show_error(self, error: str = ""):
        """显示错误状态"""
        self.llm_indicator.set_status("error")
        self.set_status_text(error or "连接错误")