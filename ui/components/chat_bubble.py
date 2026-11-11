"""聊天气泡组件模块 - 增强版"""
from PyQt6.QtWidgets import QLabel, QGraphicsOpacityEffect
from PyQt6.QtCore import Qt, QTimer, QPropertyAnimation, QEasingCurve
from core.log import get_logger

log = get_logger("chat_bubble")


class ChatBubble(QLabel):
    """聊天气泡组件 - 支持动画和视觉效果"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        # 样式设置
        self._base_style = """
            QLabel {
                background: rgba(255, 255, 255, 0.92);
                border: 1px solid rgba(186, 85, 211, 0.2);
                border-radius: 12px;
                padding: 10px 14px;
                font-size: 13px;
                color: #333;
                line-height: 1.4;
            }
        """
        self.setStyleSheet(self._base_style)

        # 透明度效果
        self._opacity_effect = QGraphicsOpacityEffect(self)
        self._opacity_effect.setOpacity(1.0)
        self.setGraphicsEffect(self._opacity_effect)

        # 动画
        self._fade_animation = QPropertyAnimation(self._opacity_effect, b"opacity")
        self._fade_animation.setDuration(300)
        self._fade_animation.setEasingCurve(QEasingCurve.Type.InOutQuad)

        # 隐藏
        self.hide()
        self._current_text = ""

    def show_text(self, text: str, duration_ms: int = 4000, animate: bool = True):
        """
        显示文本
        
        Args:
            text: 要显示的文本
            duration_ms: 显示持续时间（毫秒），0表示不自动隐藏
            animate: 是否启用淡入动画
        """
        self._current_text = text
        display = text[:200] + "..." if len(text) > 200 else text
        self.setText(display)
        self.adjustSize()

        # 淡入动画
        if animate:
            self._fade_animation.stop()
            self._opacity_effect.setOpacity(1.0)
            self._fade_animation.setStartValue(0.0)
            self._fade_animation.setEndValue(1.0)
            self._fade_animation.start()

        self.show()

        # 自动隐藏
        if duration_ms > 0:
            QTimer.singleShot(duration_ms, self._fade_out)

    def show_typing(self):
        """显示思考中状态"""
        self._current_text = ""
        self.setText("思考中...")
        self.adjustSize()
        self._opacity_effect.setOpacity(1.0)
        self.show()

    def update_text(self, text: str):
        """
        直接更新文本（用于流式输出）
        
        Args:
            text: 要显示的文本
        """
        self._current_text = text
        display = text[:200] + "..." if len(text) > 200 else text
        self.setText(display)
        self.adjustSize()
        self.show()

    def _fade_out(self):
        """淡出动画"""
        if self._fade_animation.state() == QPropertyAnimation.State.Running:
            return
        self._fade_animation.stop()
        self._fade_animation.setStartValue(1.0)
        self._fade_animation.setEndValue(0.0)
        self._fade_animation.finished.connect(self._on_fade_out_done)
        self._fade_animation.start()

    def _on_fade_out_done(self):
        """淡出完成后隐藏"""
        try:
            self._fade_animation.finished.disconnect(self._on_fade_out_done)
        except:
            pass
        self.hide()

    def set_emotion_style(self, emotion: str):
        """
        根据情感设置样式
        
        Args:
            emotion: 情感标签
        """
        emotion_styles = {
            "happy": "border-color: rgba(255, 200, 50, 0.4);",
            "sad": "border-color: rgba(100, 150, 255, 0.4);",
            "angry": "border-color: rgba(255, 100, 100, 0.4);",
            "surprised": "border-color: rgba(255, 150, 50, 0.4);",
            "shy": "border-color: rgba(255, 180, 200, 0.4);",
            "excited": "border-color: rgba(255, 220, 50, 0.4);",
            "gentle": "border-color: rgba(180, 220, 255, 0.4);",
            "melancholy": "border-color: rgba(150, 150, 200, 0.4);",
        }

        if emotion in emotion_styles:
            extra = emotion_styles[emotion]
            self.setStyleSheet(self._base_style.replace(
                "border: 1px solid rgba(186, 85, 211, 0.2);",
                f"border: 1px solid rgba(186, 85, 211, 0.2); {extra}"
            ))
        else:
            self.setStyleSheet(self._base_style)

    def clear(self):
        """清空气泡内容"""
        self.setText("")
        self._current_text = ""
        self.hide()