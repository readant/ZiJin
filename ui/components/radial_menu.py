"""圆环扇形菜单组件 - 美化版"""
import math
from PyQt6.QtWidgets import QWidget
from PyQt6.QtCore import Qt, QTimer, QPointF, pyqtSignal, QRectF, QPropertyAnimation, QEasingCurve
from PyQt6.QtGui import (
    QPainter, QColor, QPen, QFont, QBrush, QRadialGradient,
    QPainterPath, QLinearGradient, QFontMetrics, QPixmap, QPainter as QP
)
from core.log import get_logger

log = get_logger("radial_menu")


class RadialMenu(QWidget):
    """圆环扇形菜单 - 毛玻璃+渐变+阴影+动画"""

    item_clicked = pyqtSignal(str)

    # (name, label, icon_char, colors: (center, edge))
    ITEMS = [
        ("chat",     "对话",   "C", (QColor(155, 123, 212), QColor(110, 82, 168))),
        ("memo",     "备忘录", "M", (QColor(123, 167, 217), QColor(78, 127, 181))),
        ("todo",     "待办",   "T", (QColor(217, 184, 123), QColor(176, 143, 85))),
        ("memory",   "记忆",   "R", (QColor(123, 196, 160), QColor(78, 153, 120))),
        ("settings", "设置",   "S", (QColor(160, 160, 176), QColor(117, 117, 133))),
        ("exit",     "退出",   "X", (QColor(201, 130, 140), QColor(160, 92, 104))),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)

        self._visible = False
        self._center = QPointF(0, 0)
        self._inner_radius = 52
        self._outer_radius = 112
        self._hover_index = -1
        self._opacity = 0.0
        self._scale = 0.0
        self._glow_phase = 0.0

        self._anim_timer = QTimer()
        self._anim_timer.timeout.connect(self._animate)
        self._anim_timer.start(16)

        self.hide()

    def show_at(self, global_pos: QPointF):
        if not self.parent():
            return
        parent_pos = self.parent().mapFromGlobal(global_pos.toPoint())
        self._center = QPointF(parent_pos)
        self._visible = True
        self._hover_index = -1
        self._opacity = 0.0
        self._scale = 0.0

        self.setGeometry(0, 0, self.parent().width(), self.parent().height())
        self.show()
        self.raise_()
        self.setFocus()

    def hide_menu(self):
        self._visible = False

    def _animate(self):
        changed = False
        if self._visible:
            if self._opacity < 1.0:
                self._opacity = min(1.0, self._opacity + 0.08)
                changed = True
            if self._scale < 1.0:
                self._scale = min(1.0, self._scale + 0.1)
                changed = True
        else:
            if self._opacity > 0.0:
                self._opacity = max(0.0, self._opacity - 0.12)
                changed = True
            if self._scale > 0.0:
                self._scale = max(0.0, self._scale - 0.1)
                changed = True
            if self._opacity <= 0.0 and self._scale <= 0.0:
                self.hide()
                return

        self._glow_phase += 0.05
        changed = True

        if changed:
            self.update()

    def paintEvent(self, event):
        if self._opacity <= 0.01 or self._scale <= 0.01:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.setOpacity(self._opacity)

        # 毛玻璃背景 - 半透明圆形遮罩
        self._draw_frosted_bg(painter)

        # 绘制扇形
        n = len(self.ITEMS)
        sector_angle = 360.0 / n

        # 缩放动画 - 从中心弹出
        painter.translate(self._center)
        painter.scale(self._scale, self._scale)
        painter.translate(-self._center)

        for i, (name, label, icon, colors) in enumerate(self.ITEMS):
            angle_start = -90 + i * sector_angle
            is_hover = (i == self._hover_index)
            self._draw_sector(painter, angle_start, sector_angle, colors, is_hover)
            self._draw_label(painter, angle_start, sector_angle, label, icon, is_hover)

        # 中心圆
        self._draw_center(painter)

        painter.end()

    def _draw_frosted_bg(self, painter):
        """绘制毛玻璃背景"""
        cx = self._center.x()
        cy = self._center.y()
        r = self._outer_radius + 25

        # 外层光晕
        glow_r = r + 15
        glow = QRadialGradient(cx, cy, glow_r)
        glow.setColorAt(0.0, QColor(186, 85, 211, 0))
        glow.setColorAt(0.7, QColor(186, 85, 211, 10))
        glow.setColorAt(1.0, QColor(186, 85, 211, 0))
        painter.setBrush(QBrush(glow))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(QPointF(cx, cy), glow_r, glow_r)

        # 主体半透明背景
        bg = QRadialGradient(cx, cy, r)
        bg.setColorAt(0.0, QColor(30, 20, 50, 180))
        bg.setColorAt(0.5, QColor(40, 30, 60, 140))
        bg.setColorAt(0.85, QColor(50, 40, 70, 100))
        bg.setColorAt(1.0, QColor(60, 50, 80, 40))
        painter.setBrush(QBrush(bg))
        painter.setPen(QPen(QColor(255, 255, 255, 30), 1))
        painter.drawEllipse(QPointF(cx, cy), r, r)

    def _draw_sector(self, painter, angle_start, angle_span, colors, is_hover):
        cx = self._center.x()
        cy = self._center.y()

        inner = self._inner_radius - 4 if is_hover else self._inner_radius
        outer = self._outer_radius + 6 if is_hover else self._outer_radius

        center_color, edge_color = colors

        # 渐变
        gradient = QRadialGradient(cx, cy, outer)
        if is_hover:
            # 悬停时更亮
            hover_center = QColor(center_color)
            hover_center.setAlpha(240)
            hover_edge = QColor(edge_color)
            hover_edge.setAlpha(255)
            gradient.setColorAt(0.0, QColor(hover_center.red(), hover_center.green(), hover_center.blue(), 50))
            gradient.setColorAt(0.4, hover_center)
            gradient.setColorAt(1.0, hover_edge)
        else:
            normal_center = QColor(center_color)
            normal_center.setAlpha(180)
            normal_edge = QColor(edge_color)
            normal_edge.setAlpha(200)
            gradient.setColorAt(0.0, QColor(normal_center.red(), normal_center.green(), normal_center.blue(), 20))
            gradient.setColorAt(0.4, normal_center)
            gradient.setColorAt(1.0, normal_edge)

        # 构建扇形环路径
        path = QPainterPath()
        steps = 32
        outer_start = math.radians(angle_start)
        outer_end = math.radians(angle_start + angle_span)

        for s in range(steps + 1):
            a = outer_start + (outer_end - outer_start) * s / steps
            pt = QPointF(cx + outer * math.cos(a), cy + outer * math.sin(a))
            if s == 0:
                path.moveTo(pt)
            else:
                path.lineTo(pt)

        inner_end = math.radians(angle_start)
        inner_start = math.radians(angle_start + angle_span)
        for s in range(steps + 1):
            a = inner_start + (inner_end - inner_start) * s / steps
            path.lineTo(QPointF(cx + inner * math.cos(a), cy + inner * math.sin(a)))

        path.closeSubpath()

        # 阴影
        if is_hover:
            shadow_path = QPainterPath()
            shadow_r = outer + 8
            for s in range(steps + 1):
                a = outer_start + (outer_end - outer_start) * s / steps
                pt = QPointF(cx + shadow_r * math.cos(a), cy + shadow_r * math.sin(a))
                if s == 0:
                    shadow_path.moveTo(pt)
                else:
                    shadow_path.lineTo(pt)
            for s in range(steps + 1):
                a = inner_start + (inner_end - inner_start) * s / steps
                shadow_path.lineTo(QPointF(cx + inner * math.cos(a), cy + inner * math.sin(a)))
            shadow_path.closeSubpath()
            painter.setBrush(QBrush(QColor(0, 0, 0, 60)))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(shadow_path)

        # 绘制扇形
        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 80 if is_hover else 40), 1.5))
        painter.drawPath(path)

        # 悬停时的内发光
        if is_hover:
            glow_gradient = QRadialGradient(cx, cy, outer)
            glow_color = QColor(center_color)
            glow_color.setAlpha(60)
            glow_gradient.setColorAt(0.0, QColor(255, 255, 255, 0))
            glow_gradient.setColorAt(0.3, glow_color)
            glow_gradient.setColorAt(1.0, QColor(255, 255, 255, 0))
            painter.setBrush(QBrush(glow_gradient))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawPath(path)

    def _draw_label(self, painter, angle_start, angle_span, label, letter, is_hover):
        cx = self._center.x()
        cy = self._center.y()

        mid_angle = math.radians(angle_start + angle_span / 2)
        mid_radius = (self._inner_radius + self._outer_radius) / 2

        tx = cx + mid_radius * math.cos(mid_angle)
        ty = cy + mid_radius * math.sin(mid_angle)

        # 图标字母
        fsize = 22 if is_hover else 18
        painter.setFont(QFont("Consolas", fsize, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        icon_rect = QRectF(tx - 16, ty - 24, 32, 26)
        painter.drawText(icon_rect, Qt.AlignmentFlag.AlignCenter, letter)

        # 中文标签
        tsize = 11 if is_hover else 9
        painter.setFont(QFont("Microsoft YaHei", tsize, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255, 240 if is_hover else 200))
        text_rect = QRectF(tx - 28, ty + 4, 56, 18)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)

    def _draw_center(self, painter):
        """绘制中心圆"""
        cx = self._center.x()
        cy = self._center.y()
        r = self._inner_radius - 8

        # 中心渐变
        gradient = QRadialGradient(cx, cy, r)
        pulse = (math.sin(self._glow_phase * 2) + 1) / 2
        alpha = int(160 + pulse * 40)
        gradient.setColorAt(0.0, QColor(220, 200, 255, alpha))
        gradient.setColorAt(0.5, QColor(186, 85, 211, alpha))
        gradient.setColorAt(1.0, QColor(140, 50, 180, alpha))

        painter.setBrush(QBrush(gradient))
        painter.setPen(QPen(QColor(255, 255, 255, 100), 2))
        painter.drawEllipse(QPointF(cx, cy), r, r)

        # 中心文字
        painter.setFont(QFont("Microsoft YaHei", 10, QFont.Weight.Bold))
        painter.setPen(QColor(255, 255, 255))
        text_rect = QRectF(cx - 20, cy - 10, 40, 20)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, "子衿")

    def mouseMoveEvent(self, event):
        pos = event.position()
        dx = pos.x() - self._center.x()
        dy = pos.y() - self._center.y()
        dist = math.sqrt(dx * dx + dy * dy)

        if dist < self._inner_radius or dist > self._outer_radius:
            if self._hover_index != -1:
                self._hover_index = -1
                self.setCursor(Qt.CursorShape.ArrowCursor)
                self.update()
            return

        angle = math.degrees(math.atan2(dy, dx))
        if angle < -90:
            angle += 360

        n = len(self.ITEMS)
        sector_angle = 360.0 / n
        index = int((angle + 90) / sector_angle) % n

        if index != self._hover_index:
            self._hover_index = index
            self.setCursor(Qt.CursorShape.PointingHandCursor)
            self.update()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self._hover_index >= 0:
            name = self.ITEMS[self._hover_index][0]
            self.item_clicked.emit(name)
            self.hide_menu()
        elif event.button() == Qt.MouseButton.RightButton:
            self.hide_menu()

    def leaveEvent(self, event):
        if self._hover_index != -1:
            self._hover_index = -1
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.update()
