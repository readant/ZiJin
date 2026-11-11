"""Live2D渲染组件模块

增强交互：
- 鼠标追踪：眼神跟随 + 平滑插值
- 点击互动：触碰身体不同区域触发不同反应
- 动作优先级：情感动作可打断待机
- 随机待机：空闲时自动播放动作
- 鼠标悬停：进入/离开窗口有反应
- 口型同步：外部调用 set_lip_sync 驱动嘴型
"""
import os
import time
import random
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtOpenGLWidgets import QOpenGLWidget
from OpenGL.GL import *
import live2d.v3 as live2d
from config.settings import (
    LIVE2D_EYE_TRACKING, LIVE2D_EYE_LERP_SPEED,
    LIVE2D_CLICK_INTERACTION, LIVE2D_RANDOM_IDLE,
    LIVE2D_IDLE_INTERVAL_MIN, LIVE2D_IDLE_INTERVAL_MAX,
)
from core.log import get_logger

log = get_logger("live2d")


class Live2DWidget(QOpenGLWidget):
    """Live2D OpenGL渲染组件"""

    def __init__(self, model_path: str, parent=None):
        super().__init__(parent)
        self.model_path = model_path
        self.model = None
        self._ok = False
        self._last_time = 0.0

        # 鼠标追踪
        self._mouse_x = 0.0
        self._mouse_y = 0.0
        self._target_x = 0.0
        self._target_y = 0.0
        self._lerp_speed = LIVE2D_EYE_LERP_SPEED  # 平滑插值速度 (0~1)

        # 状态
        self._is_busy = False  # 是否正在播放高优先级动作
        self._busy_timer = QTimer()
        self._busy_timer.setSingleShot(True)
        self._busy_timer.timeout.connect(self._on_busy_done)

        # 随机待机
        self._idle_timer = QTimer()
        self._idle_timer.timeout.connect(self._play_random_idle)

        # 口型同步
        self._lip_sync_value = 0.0
        self._lip_sync_timer = QTimer()
        self._lip_sync_timer.timeout.connect(self._update_lip_sync)
        self._lip_sync_direction = 1  # 1=张嘴, -1=闭嘴

    # === 初始化 ===

    def initializeGL(self):
        if not self.model_path or not os.path.exists(self.model_path):
            log.warning("Live2D 模型路径无效，跳过初始化")
            return

        try:
            self.makeCurrent()
            glClearColor(0.0, 0.0, 0.0, 0.0)
            glEnable(GL_BLEND)
            glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)

            live2d.init()
            live2d.glInit()

            abs_path = os.path.abspath(self.model_path)
            self.model = live2d.Model()
            self.model.LoadModelJson(abs_path)
            self.model.CreateRenderer()
            self.model.Resize(self.width(), self.height())
            self._ok = True
            self._last_time = time.time()
            log.info("Live2D 模型加载成功: %s", abs_path)
            self._start_idle_timer()
            self.update()
        except Exception as e:
            log.error("Live2D 模型加载失败: %s", e)
            self._ok = False

    # === 渲染 ===

    def paintGL(self):
        if not self._ok:
            return
        self.makeCurrent()
        now = time.time()
        dt = now - self._last_time
        self._last_time = now

        # 平滑插值鼠标追踪
        if LIVE2D_EYE_TRACKING:
            self._mouse_x += (self._target_x - self._mouse_x) * self._lerp_speed
            self._mouse_y += (self._target_y - self._mouse_y) * self._lerp_speed
            self.model.Drag(self._mouse_x, self._mouse_y)

        glClearColor(0.0, 0.0, 0.0, 0.0)
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        live2d.clearBuffer()
        self.model.Update(dt)
        self.model.Draw()

    def resizeGL(self, w, h):
        if self._ok:
            self.makeCurrent()
            self.model.Resize(w, h)

    # === 鼠标事件 ===

    def mousePressEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            if self._ok:
                x, y = e.position().x(), e.position().y()
                self._target_x = x
                self._target_y = y
                # 根据点击区域触发不同动作
                if LIVE2D_CLICK_INTERACTION:
                    self._handle_click(x, y)
        elif e.button() == Qt.MouseButton.RightButton:
            e.ignore()

    def mouseMoveEvent(self, e):
        if self._ok:
            self._target_x = e.position().x()
            self._target_y = e.position().y()

    def mouseReleaseEvent(self, e):
        if e.button() == Qt.MouseButton.LeftButton:
            pass  # 保持追踪

    def enterEvent(self, e):
        """鼠标进入窗口"""
        if self._ok:
            log.debug("鼠标进入窗口")

    def leaveEvent(self, e):
        """鼠标离开窗口 - 回到默认朝向"""
        if self._ok:
            self._target_x = self.width() / 2
            self._target_y = self.height() / 2
            log.debug("鼠标离开窗口，回到默认朝向")

    # === 点击互动 ===

    def _handle_click(self, x: float, y: float):
        """根据点击位置触发不同反应"""
        height = self.height()
        if height <= 0:
            return

        # 上半部分 ≈ 头部区域
        if y < height * 0.4:
            log.debug("点击头部区域")
            self.start_motion("Tap", priority=2)
        # 中间部分 ≈ 身体区域
        elif y < height * 0.75:
            log.debug("点击身体区域")
            self.start_motion("Tap@Body", priority=2)
        # 下半部分
        else:
            log.debug("点击下方区域")
            self.start_motion("Flick@Body", priority=2)

    # === 动作系统 ===

    def start_motion(self, group: str, priority: int = 0):
        """播放动作

        Args:
            group: 动作组名 (Idle, Tap, Tap@Body, Flick, FlickDown, Flick@Body)
            priority: 优先级 (0=最低, 1=中, 2=最高)
        """
        if self._ok:
            log.debug("播放动作: %s (priority=%d)", group, priority)
            try:
                self.model.StartMotion(group, 0, priority)
            except Exception as e:
                log.warning("播放动作失败: %s", e)
                try:
                    self.model.StartMotion(group, 0, 0)
                except Exception as e2:
                    log.error("降级播放也失败: %s", e2)

            if priority >= 1:
                self._is_busy = True
                self._busy_timer.start(3000)

    def _on_busy_done(self):
        self._is_busy = False

    # === 参数操控 ===

    def set_parameter(self, param_id: str, value: float, weight: float = 1.0):
        """设置模型参数

        Args:
            param_id: 参数ID (ParamAngleX, ParamAngleZ, ParamEyeLOpen, etc.)
            value: 参数值
            weight: 权重 (0~1)
        """
        if self._ok:
            try:
                self.model.SetParameterValue(param_id, value, weight)
            except Exception as e:
                log.debug("参数设置失败 %s: %s", param_id, e)

    def play_emotion(self, emotion: str):
        """播放带参数操控的情感动画

        在动作基础上叠加参数变化，让情绪更明显。
        """
        if not self._ok:
            return

        log.debug("情感动画: %s", emotion)

        # 情感预设：动作 + 参数组合
        presets = {
            "happy": {
                "motion": "Tap",
                "params": {
                    "ParamAngleZ": 8,      # 头微倾
                    "ParamEyeLOpen": 1.2,  # 眼睛睁大
                    "ParamEyeROpen": 1.2,
                },
                "duration": 1500,
            },
            "sad": {
                "motion": "FlickDown",
                "params": {
                    "ParamAngleX": -5,     # 头低垂
                    "ParamAngleZ": -10,    # 向一侧倾斜
                    "ParamBodyAngleZ": -5, # 身体也倾斜
                },
                "duration": 2000,
            },
            "angry": {
                "motion": "Flick",
                "params": {
                    "ParamAngleX": 8,      # 头前倾
                    "ParamAngleZ": 5,      # 微倾
                },
                "duration": 1500,
            },
            "surprised": {
                "motion": "Flick",
                "params": {
                    "ParamAngleZ": -8,     # 头后仰
                    "ParamEyeLOpen": 1.5,  # 眼睛睁大
                    "ParamEyeROpen": 1.5,
                    "ParamMouthOpenY": 0.8,# 嘴巴张开
                },
                "duration": 1200,
            },
            "shy": {
                "motion": "Tap@Body",
                "params": {
                    "ParamAngleZ": 15,     # 头大幅倾斜
                    "ParamAngleX": -5,     # 低头
                    "ParamBodyAngleZ": 8,  # 身体倾斜
                },
                "duration": 2000,
            },
            "excited": {
                "motion": "Tap",
                "params": {
                    "ParamAngleZ": -5,     # 左右摇摆
                    "ParamBodyAngleX": 5,
                },
                "duration": 1000,
                "shake": True,  # 左右摇摆
            },
            "gentle": {
                "motion": "Idle",
                "params": {
                    "ParamAngleZ": 5,      # 温柔倾斜
                    "ParamAngleX": -3,     # 微微低头
                },
                "duration": 2000,
            },
            "melancholy": {
                "motion": "FlickDown",
                "params": {
                    "ParamAngleX": -8,     # 低头
                    "ParamAngleZ": -12,    # 大幅倾斜
                    "ParamBodyAngleZ": -8, # 身体下垂
                },
                "duration": 2500,
            },
            "thinking": {
                "motion": "Idle",
                "params": {
                    "ParamAngleX": 10,     # 头侧转
                    "ParamAngleZ": 5,      # 微倾
                },
                "duration": 2000,
            },
            "neutral": {
                "motion": "Idle",
                "params": {},
                "duration": 1000,
            },
        }

        preset = presets.get(emotion, presets["neutral"])

        # 播放动作
        self.start_motion(preset["motion"], priority=1)

        # 应用参数
        for param_id, value in preset["params"].items():
            self.set_parameter(param_id, value)

        # 摇摆效果
        if preset.get("shake"):
            self._shake_animation(preset["duration"])
        else:
            # 定时恢复参数
            QTimer.singleShot(preset["duration"], self._reset_params)

    def _reset_params(self):
        """恢复所有参数到默认值"""
        if not self._ok:
            return
        defaults = {
            "ParamAngleX": 0,
            "ParamAngleZ": 0,
            "ParamBodyAngleX": 0,
            "ParamBodyAngleZ": 0,
            "ParamEyeLOpen": 1.0,
            "ParamEyeROpen": 1.0,
            "ParamMouthOpenY": 0,
        }
        for param_id, value in defaults.items():
            self.set_parameter(param_id, value)
        log.debug("参数已重置")

    def _shake_animation(self, duration: int):
        """左右摇摆动画"""
        if not self._ok:
            return
        steps = max(2, duration // 200)  # 每200ms一次
        for i in range(steps):
            value = 8 if i % 2 == 0 else -8
            QTimer.singleShot(i * 200, lambda v=value: self.set_parameter("ParamAngleX", v))
        QTimer.singleShot(duration, self._reset_params)

    # === 随机待机 ===

    def _start_idle_timer(self):
        """启动随机待机定时器"""
        if not LIVE2D_RANDOM_IDLE:
            return
        delay = random.randint(LIVE2D_IDLE_INTERVAL_MIN * 1000, LIVE2D_IDLE_INTERVAL_MAX * 1000)
        self._idle_timer.start(delay)

    def _play_random_idle(self):
        """播放随机待机动作"""
        if self._ok and not self._is_busy:
            log.debug("随机待机动作")
            try:
                # SDK 会从 Idle 组随机选择一个变体
                self.model.StartMotion("Idle", 0, 0)
            except Exception as e:
                log.warning("待机动作失败: %s", e)
        self._start_idle_timer()

    def set_idle_enabled(self, enabled: bool):
        """启用/禁用随机待机"""
        if enabled and self._ok:
            self._start_idle_timer()
        else:
            self._idle_timer.stop()

    # === 口型同步 ===

    def set_lip_sync(self, value: float):
        """设置口型同步参数

        Args:
            value: 0.0 (闭嘴) ~ 1.0 (张嘴)
        """
        if self._ok:
            try:
                self.model.SetParameterValue("ParamMouthOpenY", value)
                self._lip_sync_value = value
            except Exception as e:
                log.debug("口型同步设置失败 (SDK可能不支持): %s", e)

    def start_lip_sync(self):
        """开始口型同步动画（外部调用，如TTS播放时）"""
        self._lip_sync_direction = 1
        self._lip_sync_value = 0.0
        self._lip_sync_timer.start(50)  # 20fps

    def stop_lip_sync(self):
        """停止口型同步动画"""
        self._lip_sync_timer.stop()
        self.set_lip_sync(0.0)

    def _update_lip_sync(self):
        """更新口型同步动画（简单正弦波模拟）"""
        # 简单的开合模拟
        self._lip_sync_value += self._lip_sync_direction * 0.15
        if self._lip_sync_value >= 0.8:
            self._lip_sync_value = 0.8
            self._lip_sync_direction = -1
        elif self._lip_sync_value <= 0.0:
            self._lip_sync_value = 0.0
            self._lip_sync_direction = 1

        self.set_lip_sync(self._lip_sync_value)

    # === 表情 ===

    def set_expression(self, expression: str = ""):
        """设置表情

        Args:
            expression: 表情名，空字符串恢复默认
        """
        if self._ok:
            try:
                if expression:
                    self.model.SetExpression(expression)
                else:
                    self.model.SetRandomExpression()
            except Exception as e:
                log.debug("表情设置失败 (SDK可能不支持): %s", e)
