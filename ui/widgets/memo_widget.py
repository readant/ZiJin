"""备忘录小部件模块"""
import os
import json
from PyQt6.QtWidgets import QTextEdit
from config.settings import DATA_DIR
from ui.components.base_widget import BaseFloatingWidget


class MemoWidget(BaseFloatingWidget):
    """备忘录小部件"""

    def __init__(self, parent=None):
        super().__init__("备忘录", 250, 200, parent)
        self._save_path = os.path.join(DATA_DIR, "memo.json")

        self.text_edit = QTextEdit()
        self.text_edit.setPlaceholderText("在此记录备忘...")
        self._layout.addWidget(self.text_edit)

        self._load_content()

    def _load_content(self):
        if os.path.exists(self._save_path):
            try:
                with open(self._save_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.text_edit.setText(data.get("content", ""))
            except Exception:
                pass

    def _save_content(self):
        os.makedirs(os.path.dirname(self._save_path), exist_ok=True)
        with open(self._save_path, "w", encoding="utf-8") as f:
            json.dump({"content": self.text_edit.toPlainText()}, f, ensure_ascii=False)

    def hideEvent(self, event):
        self._save_content()
        super().hideEvent(event)