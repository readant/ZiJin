# Live2D交互

## 原理

通过Live2D Cubism SDK渲染2D角色，支持动画、表情、物理效果。

```
┌─────────────────────────────────────┐
│          OpenGL渲染                  │
│  ┌─────────────────────────────┐   │
│  │      Live2D Model           │   │
│  │  • 动画 (Motions)           │   │
│  │  • 表情 (Expressions)       │   │
│  │  • 物理 (Physics)           │   │
│  │  • 拖拽 (Drag)              │   │
│  │  • 口型同步 (LipSync)       │   │
│  └─────────────────────────────┘   │
└─────────────────────────────────────┘
```

## 实现

### 模型加载

```python
class Live2DWidget(QOpenGLWidget):
    def initializeGL(self):
        live2d.init()
        live2d.glInit()
        
        self.model = live2d.Model()
        self.model.LoadModelJson(model_path)
        self.model.CreateRenderer()
        self.model.Resize(width, height)
```

### 渲染循环

```python
def paintGL(self):
    # 平滑插值鼠标追踪
    self._mouse_x += (self._target_x - self._mouse_x) * self._lerp_speed
    self._mouse_y += (self._target_y - self._mouse_y) * self._lerp_speed
    self.model.Drag(self._mouse_x, self._mouse_y)
    
    # 清除缓冲
    glClearColor(0.0, 0.0, 0.0, 0.0)
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    
    # 更新和绘制
    live2d.clearBuffer()
    self.model.Update(dt)
    self.model.Draw()
```

### 交互

```python
def mousePressEvent(self, e):
    if e.button() == Qt.MouseButton.LeftButton:
        x, y = e.position().x(), e.position().y()
        self._target_x = x
        self._target_y = y
        # 根据点击区域触发不同反应
        if y < self.height() * 0.4:
            self.start_motion("Tap", priority=2)  # 头部
        elif y < self.height() * 0.75:
            self.start_motion("Tap@Body", priority=2)  # 身体
        else:
            self.start_motion("Flick@Body", priority=2)  # 下方

def start_motion(self, group, priority=0):
    self.model.StartMotion(group, 0, priority)
```

## 增强交互功能

### 1. 鼠标追踪 (眼神跟随)

鼠标移动时，模型眼睛和头部平滑跟随。

```python
# 配置项
LIVE2D_EYE_TRACKING = True  # 启用追踪
LIVE2D_EYE_LERP_SPEED = 0.15  # 平滑速度 (0~1)
```

实现原理：
- `mouseMoveEvent` 更新目标坐标 `_target_x/y`
- `paintGL` 中用 Lerp 插值平滑过渡
- 避免模型头部抖动

### 2. 点击互动

点击模型不同区域触发不同动画：

| 区域 | 位置 | 动作 | 优先级 |
|------|------|------|--------|
| 头部 | 上方 40% | Tap | 2 (最高) |
| 身体 | 中间 35% | Tap@Body | 2 |
| 下方 | 下方 25% | Flick@Body | 2 |

```python
# 配置项
LIVE2D_CLICK_INTERACTION = True
```

### 3. 动作优先级

情感动作可以打断待机动画：

| 优先级 | 用途 | 示例 |
|--------|------|------|
| 0 | 待机动画 | Idle |
| 1 | 情感动作 | 情感回复时的 Tap/Flick |
| 2 | 用户交互 | 点击触发的动作 |

```python
# 情感动作使用优先级1
self.live2d.start_motion(motion, priority=1)

# 点击交互使用优先级2
self.live2d.start_motion("Tap", priority=2)
```

### 4. 随机待机

空闲时自动播放待机动作，让角色更生动：

```python
# 配置项
LIVE2D_RANDOM_IDLE = True
LIVE2D_IDLE_INTERVAL_MIN = 30  # 最小间隔 (秒)
LIVE2D_IDLE_INTERVAL_MAX = 120  # 最大间隔 (秒)
```

实现：
- 使用 `QTimer` 随机延迟
- SDK 从 Idle 组随机选择变体 (m01/m02/m05)
- 高优先级动作时暂停待机

### 5. 鼠标悬停反应

鼠标进入/离开窗口时有反应：
- 进入：模型开始追踪鼠标
- 离开：模型回到默认朝向 (中心)

```python
def leaveEvent(self, e):
    self._target_x = self.width() / 2
    self._target_y = self.height() / 2
```

### 6. 口型同步

TTS 播放时驱动嘴型动画：

```python
# 配置项
LIVE2D_LIP_SYNC = True
```

实现：
- TTS 工具通过事件总线发射 `tts_start` / `tts_end` 事件
- MainWindow 订阅事件，调用 `live2d.start_lip_sync()` / `stop_lip_sync()`
- 口型同步用简单正弦波模拟开合

## 动画系统

### 可用动画

| 动画组 | 文件 | 说明 |
|--------|------|------|
| `Idle` | m01, m02, m05 | 空闲状态 (3变体) |
| `Tap` | m06 | 点击头部 |
| `Tap@Body` | m07 | 点击身体 |
| `Flick` | m03 | 轻拂 |
| `FlickDown` | m04 | 向下轻拂 |
| `Flick@Body` | m08 | 身体轻拂 |

### 情感映射

```python
EMOTION_MOTIONS = {
    "happy": "Tap",
    "sad": "FlickDown",
    "angry": "Flick",
    "surprised": "Flick",
    "neutral": "Idle",
    "thinking": "Idle",
    "shy": "Tap@Body",
    "excited": "Tap",
    "gentle": "Idle",
    "melancholy": "FlickDown",
}
```

## 配置项

| 配置 | 默认值 | 说明 |
|------|--------|------|
| `LIVE2D_EYE_TRACKING` | True | 启用鼠标追踪 |
| `LIVE2D_EYE_LERP_SPEED` | 0.15 | 平滑插值速度 |
| `LIVE2D_CLICK_INTERACTION` | True | 启用点击互动 |
| `LIVE2D_RANDOM_IDLE` | True | 启用随机待机 |
| `LIVE2D_IDLE_INTERVAL_MIN` | 30 | 待机最小间隔 (秒) |
| `LIVE2D_IDLE_INTERVAL_MAX` | 120 | 待机最大间隔 (秒) |
| `LIVE2D_LIP_SYNC` | True | 启用口型同步 |

## 事件总线

TTS 通过事件总线通知 Live2D 组件：

```python
# TTS 播放时
bus.emit("tts_start")  # 开始口型同步
bus.emit("tts_end")    # 停止口型同步

# MainWindow 订阅
bus.on("tts_start", self._on_tts_start)
bus.on("tts_end", self._on_tts_end)
```

## 后续升级

| 方向 | 描述 |
|------|------|
| 表情系统 | 支持表情文件切换 (.exp3.json) |
| 物理效果 | 头发、衣服物理模拟 |
| 视线追踪 | 使用 LAppModel 的 SetParameterValue |
| 更多动画 | 添加新的动画组 |
| 天气联动 | 根据天气改变角色状态 |
