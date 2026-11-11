"""设置界面小部件模块"""
import os
import json
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QComboBox, QSpinBox, QCheckBox, QPushButton, QTabWidget,
    QGroupBox, QFormLayout, QMessageBox, QSlider
)
from PyQt6.QtCore import Qt
from config.settings import (
    LLM_PROVIDER, OLLAMA_BASE_URL, OLLAMA_MODEL,
    OPENAI_API_KEY, OPENAI_BASE_URL, OPENAI_MODEL,
    SHORT_MEMORY_ROUNDS, TTS_ENABLED, TTS_RATE, TTS_VOLUME,
    WINDOW_OPACITY, TOOLS_ENABLED, DATA_DIR
)
from ui.components.base_widget import BaseFloatingWidget
from core.log import get_logger

log = get_logger("settings")


class SettingsWidget(BaseFloatingWidget):
    """设置界面小部件"""

    def __init__(self, parent=None):
        super().__init__("设置", 450, 500, parent)
        self._settings_path = os.path.join(DATA_DIR, "settings.json")
        self._settings = self._load_settings()

        self._setup_ui()
        self._load_current_settings()

    def _setup_ui(self):
        """设置UI界面"""
        self.tabs = QTabWidget()
        self._layout.addWidget(self.tabs)

        # LLM设置标签页
        self._setup_llm_tab()

        # 记忆设置标签页
        self._setup_memory_tab()

        # TTS设置标签页
        self._setup_tts_tab()

        # UI设置标签页
        self._setup_ui_tab()

        # 保存按钮
        btn_layout = QHBoxLayout()
        btn_layout.addStretch()

        reset_btn = QPushButton("恢复默认")
        reset_btn.setStyleSheet(
            "QPushButton { background: rgba(200,200,200,0.5); border-radius: 6px; padding: 8px 16px; }"
            "QPushButton:hover { background: rgba(180,180,180,0.7); }"
        )
        reset_btn.clicked.connect(self._reset_settings)
        btn_layout.addWidget(reset_btn)

        save_btn = QPushButton("保存设置")
        save_btn.setStyleSheet(
            "QPushButton { background: rgba(186,85,211,0.6); color: white; border-radius: 6px; padding: 8px 16px; }"
            "QPushButton:hover { background: rgba(186,85,211,0.8); }"
        )
        save_btn.clicked.connect(self._save_settings)
        btn_layout.addWidget(save_btn)

        self._layout.addLayout(btn_layout)

    def _setup_llm_tab(self):
        """设置LLM标签页"""
        llm_widget = QWidget()
        layout = QFormLayout(llm_widget)
        layout.setSpacing(12)

        # LLM提供商
        self.llm_provider_combo = QComboBox()
        self.llm_provider_combo.addItems(["ollama", "openai_api"])
        layout.addRow("LLM提供商:", self.llm_provider_combo)

        # Ollama设置组
        self.ollama_group = QGroupBox("Ollama设置")
        ollama_layout = QFormLayout(self.ollama_group)

        self.ollama_url_edit = QLineEdit()
        self.ollama_url_edit.setPlaceholderText("http://localhost:11434")
        ollama_layout.addRow("服务地址:", self.ollama_url_edit)

        self.ollama_model_edit = QLineEdit()
        self.ollama_model_edit.setPlaceholderText("qwen2.5:7b-instruct")
        ollama_layout.addRow("模型名称:", self.ollama_model_edit)

        layout.addRow(self.ollama_group)

        # OpenAI设置组
        self.openai_group = QGroupBox("OpenAI API设置")
        openai_layout = QFormLayout(self.openai_group)

        self.openai_key_edit = QLineEdit()
        self.openai_key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.openai_key_edit.setPlaceholderText("sk-...")
        openai_layout.addRow("API Key:", self.openai_key_edit)

        self.openai_url_edit = QLineEdit()
        self.openai_url_edit.setPlaceholderText("https://api.openai.com/v1")
        openai_layout.addRow("API地址:", self.openai_url_edit)

        self.openai_model_edit = QLineEdit()
        self.openai_model_edit.setPlaceholderText("gpt-4o-mini")
        openai_layout.addRow("模型名称:", self.openai_model_edit)

        layout.addRow(self.openai_group)

        # 连接提供商切换事件
        self.llm_provider_combo.currentTextChanged.connect(self._on_provider_changed)

        self.tabs.addTab(llm_widget, "LLM")

    def _setup_memory_tab(self):
        """设置记忆标签页"""
        memory_widget = QWidget()
        layout = QFormLayout(memory_widget)
        layout.setSpacing(12)

        # 短期记忆轮数
        self.memory_rounds_spin = QSpinBox()
        self.memory_rounds_spin.setRange(1, 50)
        self.memory_rounds_spin.setValue(SHORT_MEMORY_ROUNDS)
        layout.addRow("短期记忆轮数:", self.memory_rounds_spin)

        # 启用长期记忆
        self.long_memory_check = QCheckBox("启用长期记忆 (ChromaDB)")
        self.long_memory_check.setChecked(True)
        layout.addRow(self.long_memory_check)

        info_label = QLabel("长期记忆使用向量数据库存储历史对话，\n支持语义搜索相关记忆。")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow(info_label)

        self.tabs.addTab(memory_widget, "记忆")

    def _setup_tts_tab(self):
        """设置TTS标签页"""
        tts_widget = QWidget()
        layout = QFormLayout(tts_widget)
        layout.setSpacing(12)

        # 启用TTS
        self.tts_enabled_check = QCheckBox("启用语音合成")
        self.tts_enabled_check.setChecked(TTS_ENABLED)
        layout.addRow(self.tts_enabled_check)

        # 语速
        self.tts_rate_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_rate_slider.setRange(50, 300)
        self.tts_rate_slider.setValue(TTS_RATE)
        self.tts_rate_label = QLabel(f"{TTS_RATE}")
        self.tts_rate_slider.valueChanged.connect(
            lambda v: self.tts_rate_label.setText(str(v))
        )
        rate_layout = QHBoxLayout()
        rate_layout.addWidget(self.tts_rate_slider)
        rate_layout.addWidget(self.tts_rate_label)
        layout.addRow("语速:", rate_layout)

        # 音量
        self.tts_volume_slider = QSlider(Qt.Orientation.Horizontal)
        self.tts_volume_slider.setRange(0, 100)
        self.tts_volume_slider.setValue(int(TTS_VOLUME * 100))
        self.tts_volume_label = QLabel(f"{int(TTS_VOLUME * 100)}%")
        self.tts_volume_slider.valueChanged.connect(
            lambda v: self.tts_volume_label.setText(f"{v}%")
        )
        volume_layout = QHBoxLayout()
        volume_layout.addWidget(self.tts_volume_slider)
        volume_layout.addWidget(self.tts_volume_label)
        layout.addRow("音量:", volume_layout)

        self.tabs.addTab(tts_widget, "语音")

    def _setup_ui_tab(self):
        """设置UI标签页"""
        ui_widget = QWidget()
        layout = QFormLayout(ui_widget)
        layout.setSpacing(12)

        # 窗口透明度
        self.opacity_slider = QSlider(Qt.Orientation.Horizontal)
        self.opacity_slider.setRange(30, 100)
        self.opacity_slider.setValue(int(WINDOW_OPACITY * 100))
        self.opacity_label = QLabel(f"{int(WINDOW_OPACITY * 100)}%")
        self.opacity_slider.valueChanged.connect(
            lambda v: self.opacity_label.setText(f"{v}%")
        )
        opacity_layout = QHBoxLayout()
        opacity_layout.addWidget(self.opacity_slider)
        opacity_layout.addWidget(self.opacity_label)
        layout.addRow("窗口透明度:", opacity_layout)

        # 启用工具
        self.tools_enabled_check = QCheckBox("启用桌面工具")
        self.tools_enabled_check.setChecked(TOOLS_ENABLED)
        layout.addRow(self.tools_enabled_check)

        info_label = QLabel("关闭后LLM将不会调用任何工具，\n仅进行纯对话。")
        info_label.setStyleSheet("color: #666; font-size: 11px;")
        layout.addRow(info_label)

        self.tabs.addTab(ui_widget, "界面")

    def _on_provider_changed(self, provider: str):
        """LLM提供商切换"""
        self.ollama_group.setVisible(provider == "ollama")
        self.openai_group.setVisible(provider == "openai_api")

    def _load_settings(self) -> dict:
        """加载自定义设置"""
        if os.path.exists(self._settings_path):
            try:
                with open(self._settings_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def _load_current_settings(self):
        """加载当前设置到界面"""
        settings = self._settings

        # LLM设置
        provider = settings.get("LLM_PROVIDER", LLM_PROVIDER)
        self.llm_provider_combo.setCurrentText(provider)

        self.ollama_url_edit.setText(settings.get("OLLAMA_BASE_URL", OLLAMA_BASE_URL))
        self.ollama_model_edit.setText(settings.get("OLLAMA_MODEL", OLLAMA_MODEL))
        self.openai_key_edit.setText(settings.get("OPENAI_API_KEY", OPENAI_API_KEY or ""))
        self.openai_url_edit.setText(settings.get("OPENAI_BASE_URL", OPENAI_BASE_URL))
        self.openai_model_edit.setText(settings.get("OPENAI_MODEL", OPENAI_MODEL))

        # 记忆设置
        self.memory_rounds_spin.setValue(settings.get("SHORT_MEMORY_ROUNDS", SHORT_MEMORY_ROUNDS))

        # TTS设置
        self.tts_enabled_check.setChecked(settings.get("TTS_ENABLED", TTS_ENABLED))
        self.tts_rate_slider.setValue(settings.get("TTS_RATE", TTS_RATE))
        self.tts_volume_slider.setValue(int(settings.get("TTS_VOLUME", TTS_VOLUME) * 100))

        # UI设置
        self.opacity_slider.setValue(int(settings.get("WINDOW_OPACITY", WINDOW_OPACITY) * 100))
        self.tools_enabled_check.setChecked(settings.get("TOOLS_ENABLED", TOOLS_ENABLED))

        # 触发提供商切换
        self._on_provider_changed(provider)

    def _save_settings(self):
        """保存设置"""
        settings = {
            # LLM
            "LLM_PROVIDER": self.llm_provider_combo.currentText(),
            "OLLAMA_BASE_URL": self.ollama_url_edit.text().strip(),
            "OLLAMA_MODEL": self.ollama_model_edit.text().strip(),
            "OPENAI_API_KEY": self.openai_key_edit.text().strip(),
            "OPENAI_BASE_URL": self.openai_url_edit.text().strip(),
            "OPENAI_MODEL": self.openai_model_edit.text().strip(),
            # 记忆
            "SHORT_MEMORY_ROUNDS": self.memory_rounds_spin.value(),
            # TTS
            "TTS_ENABLED": self.tts_enabled_check.isChecked(),
            "TTS_RATE": self.tts_rate_slider.value(),
            "TTS_VOLUME": self.tts_volume_slider.value() / 100.0,
            # UI
            "WINDOW_OPACITY": self.opacity_slider.value() / 100.0,
            "TOOLS_ENABLED": self.tools_enabled_check.isChecked(),
        }

        try:
            os.makedirs(os.path.dirname(self._settings_path), exist_ok=True)
            with open(self._settings_path, "w", encoding="utf-8") as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            self._settings = settings
            QMessageBox.information(self, "成功", "设置已保存！\n部分设置需要重启应用才能生效。")
            log.info("设置已保存")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存设置失败: {e}")
            log.error("保存设置失败: %s", e)

    def _reset_settings(self):
        """恢复默认设置"""
        reply = QMessageBox.question(
            self, "确认", "确定要恢复默认设置吗？",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            self._settings = {}
            self._load_current_settings()
            QMessageBox.information(self, "成功", "已恢复默认设置，点击保存以应用。")