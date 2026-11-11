"""UI模块 - 子衿桌面伴生代理"""
import sys
import os
import time
import json
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QMenu, QSystemTrayIcon,
    QMessageBox, QVBoxLayout, QHBoxLayout, QWidget, QTextEdit, QLineEdit, QPushButton
)
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from PyQt6.QtCore import Qt, QTimer, QPoint, QPointF, pyqtSignal
from PyQt6.QtGui import QIcon, QAction, QPixmap, QPainter, QColor, QPen, QFont
from OpenGL.GL import *
import live2d.v3 as live2d
from config.settings import DATA_DIR, EMOTION_MOTIONS
from core.bus import bus
from tools.audit import audit
from core.log import get_logger
from ui.components.live2d_widget import Live2DWidget
from ui.components.chat_bubble import ChatBubble
from ui.components.status_bar import StatusBar
from ui.components.radial_menu import RadialMenu
from ui.widgets.memo_widget import MemoWidget
from ui.widgets.todo_widget import TodoWidget
from ui.widgets.memory_widget import MemoryWidget
from ui.widgets.audit_widget import AuditWidget
from ui.widgets.settings_widget import SettingsWidget
from ui.workers.llm_worker import LLMWorker

log = get_logger("ui")


class MainWindow(QMainWindow):
    """主窗口 - 子衿桌面伴生代理"""

    # 工具确认请求：工作线程 emit，主线程弹框（Qt 信号天然跨线程排队）
    _confirm_requested = pyqtSignal(str, dict)

    def __init__(self, agent, model_path: str):
        super().__init__()
        self.agent = agent
        self._workers = []
        self._memo_widget = None
        self._todo_widget = None
        self._memory_widget = None
        self._audit_widget = None
        self._settings_widget = None
        self._chat_visible = False
        self._typing_started = False
        self._accumulated_text = ""
        self._poll_timer = None

        self.setWindowTitle("子衿")
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setFixedSize(350, 500)
        self.setAttribute(Qt.WidgetAttribute.WA_QuitOnClose, False)

        # Live2D 模型
        self.live2d = Live2DWidget(model_path, self)
        self.setCentralWidget(self.live2d)

        # 聊天气泡 (初始隐藏)
        self.bubble = ChatBubble(self)
        self.bubble.setGeometry(8, 8, 334, 90)
        self.bubble.hide()

        # 输入框 (初始隐藏)
        self.input_box = QLineEdit(self)
        self.input_box.setPlaceholderText("输入消息...")
        self.input_box.setGeometry(8, 440, 334, 32)
        self.input_box.setStyleSheet("""
            QLineEdit {
                background: rgba(255,255,255,0.72);
                border: 1px solid rgba(186,85,211,0.35);
                border-radius: 8px;
                padding: 4px 8px;
                font-size: 13px;
                color: #333;
            }
            QLineEdit:focus {
                background: rgba(255,255,255,0.9);
                border: 1px solid rgba(186,85,211,0.6);
            }
        """)
        self.input_box.returnPressed.connect(self._on_send)
        self.input_box.hide()

        self._drag_pos = None

        # 状态栏 (初始隐藏)
        self.status_bar = StatusBar(self)
        self.status_bar.setGeometry(8, 470, 334, 28)
        self.status_bar.hide()

        # 圆环菜单
        self.radial_menu = RadialMenu(self)
        self.radial_menu.item_clicked.connect(self._on_menu_item)

        self._render_timer = QTimer()
        self._render_timer.timeout.connect(self._on_render)
        self._render_timer.start(16)

        # TTS 口型同步事件
        bus.on("tts_start", self._on_tts_start)
        bus.on("tts_end", self._on_tts_end)

        # 危险工具确认：工具在后台线程触发，必须投递回主线程弹框
        self._confirm_requested.connect(self._on_tool_confirm_requested)
        bus.on("tool_confirm_required", self._relay_confirm_request)

        self._setup_tray()

    def _setup_tray(self):
        self.tray = QSystemTrayIcon(self)

        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setBrush(QColor(186, 85, 211))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(4, 4, 56, 56)
        painter.setPen(QPen(QColor(255, 255, 255), 2))
        font = QFont("楷体", 24, QFont.Weight.Bold)
        painter.setFont(font)
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "衿")
        painter.end()

        self.tray.setIcon(QIcon(pixmap))
        self.tray.setToolTip("子衿 - 桌面伴生代理")

        tray_menu = QMenu()
        tray_menu.addAction("显示窗口", self.show)
        tray_menu.addSeparator()
        tray_menu.addAction("退出", self._quit)

        self.tray.setContextMenu(tray_menu)
        self.tray.activated.connect(self._on_tray_activated)
        self.tray.show()

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show()
            self.raise_()
            self.activateWindow()

    def _on_menu_item(self, name: str):
        """处理圆环菜单点击"""
        log.debug("菜单点击: %s", name)
        if name == "chat":
            self._toggle_chat()
        elif name == "memo":
            self._toggle_memo()
        elif name == "todo":
            self._toggle_todo()
        elif name == "memory":
            self._toggle_memory()
        elif name == "settings":
            self._toggle_settings()
        elif name == "exit":
            self._quit()

    def _toggle_chat(self):
        """切换对话模式"""
        self._chat_visible = not self._chat_visible
        if self._chat_visible:
            self.input_box.show()
            self.input_box.setFocus()
            self.status_bar.show()
            self.status_bar.show_connected()
            # 显示欢迎气泡
            self.bubble.show_text("你好呀~ 右键我可以选择其他功能哦", duration_ms=4000)
        else:
            self.input_box.hide()
            self.status_bar.hide()
            self.bubble.hide()

    def _toggle_memo(self):
        if self._memo_widget and self._memo_widget.isVisible():
            self._memo_widget.hide()
        else:
            if not self._memo_widget:
                self._memo_widget = MemoWidget()
            self._memo_widget.show()

    def _toggle_todo(self):
        if self._todo_widget and self._todo_widget.isVisible():
            self._todo_widget.hide()
        else:
            if not self._todo_widget:
                self._todo_widget = TodoWidget()
            self._todo_widget.show()

    def _toggle_memory(self):
        if self._memory_widget and self._memory_widget.isVisible():
            self._memory_widget.hide()
        else:
            if not self._memory_widget:
                self._memory_widget = MemoryWidget(self.agent)
            self._memory_widget.refresh()
            self._memory_widget.show()

    def _toggle_settings(self):
        if self._settings_widget and self._settings_widget.isVisible():
            self._settings_widget.hide()
        else:
            if not self._settings_widget:
                self._settings_widget = SettingsWidget()
            self._settings_widget.show()

    def _quit(self):
        log.info("用户请求退出")
        self.tray.hide()
        QApplication.instance().quit()

    def closeEvent(self, event):
        log.info("窗口关闭事件触发")
        event.ignore()
        self.hide()

    def _on_tts_start(self):
        """TTS 开始播放 - 启动口型同步"""
        self.live2d.start_lip_sync()

    # === 危险工具确认 ===

    def _relay_confirm_request(self, name: str, args: dict):
        """在工作线程被调用：只做跨线程投递，不直接碰界面"""
        self._confirm_requested.emit(name, args)

    def _on_tool_confirm_requested(self, name: str, args: dict):
        """在主线程弹出确认框，并把结果回投给工具执行器"""
        detail = "、".join(f"{k}={v}" for k, v in args.items()) if args else "无参数"

        if not self.isVisible():
            self.show()
            self.raise_()

        answer = QMessageBox.question(
            self,
            "需要确认",
            f"子衿请求执行工具「{name}」\n\n参数：{detail}\n\n是否允许？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        allowed = answer == QMessageBox.StandardButton.Yes
        log.info("用户确认工具 %s: %s", name, allowed)
        self.agent.tool_executor.resolve_confirmation(allowed)

    def _on_tts_end(self):
        """TTS 播放结束 - 停止口型同步"""
        self.live2d.stop_lip_sync()

    def _on_render(self):
        if self.live2d._ok:
            self.live2d.update()

    def show_reply(self, emotion: str, text: str, body_params: dict = None):
        """显示回复"""
        self.bubble.set_emotion_style(emotion)
        self.bubble.show_text(text, duration_ms=6000)
        self.live2d.play_emotion(emotion)
        if body_params:
            from core.emotion import BODY_PARAM_MAP
            for param_key, value in body_params.items():
                param_id = BODY_PARAM_MAP.get(param_key)
                if param_id:
                    self.live2d.set_parameter(param_id, value)

    def on_user_input(self, text: str):
        """处理用户输入"""
        log.debug("用户输入: %s", text[:50])
        self.bubble.show_typing()
        self.status_bar.show_thinking()
        self._typing_started = False
        self._accumulated_text = ""

        worker = LLMWorker(self.agent, text, use_stream=True)
        worker.start()
        self._workers.append(worker)

        self._poll_timer = QTimer()
        self._poll_timer.timeout.connect(self._poll_worker)
        self._poll_timer.start(50)

    def _poll_worker(self):
        """轮询工作线程获取数据"""
        if not self._workers:
            self._poll_timer.stop()
            return

        worker = self._workers[-1] if self._workers else None
        if not worker:
            self._poll_timer.stop()
            return

        while True:
            msg = worker.get_chunk()
            if msg is None:
                break
            msg_type, chunk = msg
            self._handle_chunk(chunk)

        if not worker.is_running():
            msg = worker.get_result()
            if msg:
                msg_type, result = msg
                self._handle_result(result)
            self._cleanup_worker(worker)
            self._poll_timer.stop()

    def _handle_chunk(self, chunk: dict):
        """处理流式输出块"""
        chunk_type = chunk.get("type")

        if chunk_type == "text":
            content = chunk.get("content", "")
            if content:
                if not self._typing_started:
                    self._typing_started = True
                    self._accumulated_text = content
                else:
                    self._accumulated_text += content
                # 移除情感标签后显示
                clean = self._accumulated_text
                if clean.startswith("["):
                    bracket_end = clean.find("]")
                    if bracket_end > 0:
                        clean = clean[bracket_end + 1:].strip()
                self.bubble.update_text(clean)

        elif chunk_type == "emotion":
            emotion = chunk.get("emotion", "neutral")
            body_params = chunk.get("body_params", {})
            self.bubble.set_emotion_style(emotion)
            # 应用情感动画 + 肢体语言参数
            self.live2d.play_emotion(emotion)
            for param_key, value in body_params.items():
                from core.emotion import BODY_PARAM_MAP
                param_id = BODY_PARAM_MAP.get(param_key)
                if param_id:
                    self.live2d.set_parameter(param_id, value)

        elif chunk_type == "done":
            self._typing_started = False
            # 使用累积文本的干净版本
            clean = self._accumulated_text
            if clean.startswith("["):
                bracket_end = clean.find("]")
                if bracket_end > 0:
                    clean = clean[bracket_end + 1:].strip()
            display = clean[:200] + "..." if len(clean) > 200 else clean
            self.bubble.setText(display)
            self.bubble.adjustSize()

    def _handle_result(self, result: dict):
        """处理最终结果"""
        if result.get("text"):
            self.show_reply(
                result.get("emotion", "neutral"),
                result.get("text", ""),
                result.get("body_params", {}),
            )
        self.input_box.setEnabled(True)
        self.input_box.setFocus()
        self.status_bar.show_connected()

    def _cleanup_worker(self, worker):
        if worker in self._workers:
            self._workers.remove(worker)

    def _on_send(self):
        text = self.input_box.text().strip()
        if not text:
            return
        self.input_box.clear()
        self.input_box.setEnabled(False)
        self.on_user_input(text)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
        elif event.button() == Qt.MouseButton.RightButton:
            global_pos = event.globalPosition()
            self.radial_menu.show_at(global_pos)
            # 不消费事件，让圆环菜单接收后续鼠标事件
            event.ignore()

    def mouseDoubleClickEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self._toggle_chat()

    def mouseMoveEvent(self, event):
        if self._drag_pos:
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event):
        self._drag_pos = None

    # === 调试快捷键 ===

    def keyPressEvent(self, event):
        """调试用键盘快捷键"""
        key = event.key()

        # 情感动画测试 (Q~P键)
        emotion_map = {
            Qt.Key.Key_Q: "happy",
            Qt.Key.Key_W: "sad",
            Qt.Key.Key_E: "angry",
            Qt.Key.Key_R: "surprised",
            Qt.Key.Key_T: "shy",
            Qt.Key.Key_Y: "excited",
            Qt.Key.Key_U: "gentle",
            Qt.Key.Key_I: "melancholy",
            Qt.Key.Key_O: "thinking",
            Qt.Key.Key_P: "neutral",
        }

        # 基础动作测试 (1-6键)
        motion_map = {
            Qt.Key.Key_1: ("Idle", "待机"),
            Qt.Key.Key_2: ("Tap", "点击头部"),
            Qt.Key.Key_3: ("Tap@Body", "点击身体"),
            Qt.Key.Key_4: ("Flick", "轻拂"),
            Qt.Key.Key_5: ("FlickDown", "向下轻拂"),
            Qt.Key.Key_6: ("Flick@Body", "身体轻拂"),
        }

        if key in emotion_map:
            emotion = emotion_map[key]
            log.debug("调试: 情感动画 %s", emotion)
            self.live2d.play_emotion(emotion)
            self.bubble.show_text(f"[调试] {emotion}", duration_ms=2000)

        elif key in motion_map:
            group, label = motion_map[key]
            log.debug("调试: 播放 %s (%s)", group, label)
            self.live2d.start_motion(group, priority=2)
            self.bubble.show_text(f"[调试] {label}", duration_ms=2000)

        elif key == Qt.Key.Key_L:
            log.debug("调试: 口型同步")
            self.live2d.start_lip_sync()
            self.bubble.show_text("[调试] 口型同步中...", duration_ms=3000)
            QTimer.singleShot(3000, self.live2d.stop_lip_sync)

        elif key == Qt.Key.Key_H:
            self.bubble.show_text(
                "调试快捷键:\n1-6: 动作\nQ-P: 情感\nL: 口型\nH: 帮助",
                duration_ms=5000,
            )

        elif key == Qt.Key.Key_0:
            log.debug("调试: 重置参数")
            self.live2d._reset_params()
            self.bubble.show_text("[调试] 参数重置", duration_ms=1000)

        else:
            super().keyPressEvent(event)
