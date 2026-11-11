"""
子衿 - 桌面伴生代理 (主入口)

功能：
- 初始化 PyQt6 应用
- 加载 Live2D 模型
- 创建 Agent 协调器
- 启动主窗口

使用方法：
    python main.py

环境要求：
    - Python 3.11+
    - PyQt6
    - live2d (Cubism SDK)
    - OpenGL 3.3+
"""
import sys
import os

# 将项目根目录添加到 Python 路径，确保模块导入正常
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 导入配置并验证
from config.settings import validate, PROJECT_NAME, CHARACTER_NAME, MODEL_PATH
validate()  # 启动前验证配置合法性

# Windows DPI 感知设置 - 确保在高分屏上正确显示
import ctypes
try:
    # Windows 10+ 的 DPI 感知 API
    ctypes.windll.shcore.SetProcessDpiAwarenessContext(True)
except Exception:
    # 非 Windows 系统或旧版本会失败，忽略即可
    pass

from core.log import setup_logging, get_logger
setup_logging()
log = get_logger("main")

# 全局异常捕获
def excepthook(exc_type, exc_value, exc_traceback):
    log.error("未捕获异常: %s", exc_value)
    import traceback
    log.error(traceback.format_exception(exc_type, exc_value, exc_traceback))

sys.excepthook = excepthook

# PyQt6 基础组件
from PyQt6.QtWidgets import QApplication
from PyQt6.QtGui import QSurfaceFormat, QPixmap, QPainter, QColor, QPen, QFont
from PyQt6.QtCore import QTimer, Qt

# 核心模块
from core.agent import Agent          # Agent 协调器
from core.bus import bus              # 事件总线
from tools import registry            # 工具注册表
from ui.main_window import MainWindow # 主窗口


def get_model_path() -> str:
    log.debug("MODEL_PATH config: %s", MODEL_PATH)
    log.debug("File exists: %s", os.path.exists(MODEL_PATH))
    if os.path.exists(MODEL_PATH):
        return MODEL_PATH
    return ""


def create_default_icon() -> QPixmap:
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
    return pixmap


def main():
    log.info("=== %s 启动中 ===", PROJECT_NAME)

    agent = Agent()
    log.info("Agent就绪: %s", agent.llm.model)
    log.info("已注册工具: %s", registry.list_tools())

    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    fmt = QSurfaceFormat()
    fmt.setVersion(3, 3)
    fmt.setProfile(QSurfaceFormat.OpenGLContextProfile.CompatibilityProfile)
    fmt.setAlphaBufferSize(8)
    QSurfaceFormat.setDefaultFormat(fmt)

    model_path = get_model_path()
    if not model_path:
        log.warning("未找到Live2D模型文件，Live2D功能将不可用")
        log.warning("请将模型放入 models/ 目录")

    window = MainWindow(agent, model_path)

    window.show()
    screen = app.primaryScreen().geometry()
    window.move((screen.width() - 350) // 2, (screen.height() - 500) // 2)
    window.raise_()
    window.activateWindow()

    log.info("%s已上线", CHARACTER_NAME)

    # 追踪退出原因
    app.aboutToQuit.connect(lambda: log.info("QApplication 即将退出"))

    try:
        sys.exit(app.exec())
    except Exception as e:
        log.error("应用异常退出: %s", e)
        import traceback
        log.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
