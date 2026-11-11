"""用户画像模块"""
import json
import os
from datetime import datetime
from config.settings import USER_PROFILE_PATH


class UserProfile:
    """
    用户画像 - JSON 存储用户信息
    
    存储内容：
    - name: 用户名称
    - preferences: 用户偏好 (字典)
    - facts: 关于用户的事实 (列表)
    
    文件位置: data/user_profile.json
    """

    def __init__(self, path: str = USER_PROFILE_PATH):
        self.path = path
        self.profile = self._load()

    def _load(self) -> dict:
        """从文件加载用户画像"""
        if os.path.exists(self.path):
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        # 默认画像
        return {
            "name": "用户",
            "preferences": {},
            "facts": [],
            "created_at": datetime.now().isoformat(),
        }

    def _save(self):
        """保存用户画像到文件"""
        os.makedirs(os.path.dirname(self.path), exist_ok=True)
        with open(self.path, "w", encoding="utf-8") as f:
            json.dump(self.profile, f, ensure_ascii=False, indent=2)

    def get_name(self) -> str:
        """获取用户名称"""
        return self.profile.get("name", "用户")

    def set_name(self, name: str):
        """设置用户名称"""
        self.profile["name"] = name
        self._save()

    def add_fact(self, fact: str):
        """
        添加关于用户的事实
        
        如: "喜欢编程"、"今天要考试"
        """
        if fact not in self.profile["facts"]:
            self.profile["facts"].append(fact)
            self._save()

    def set_preference(self, key: str, value: str):
        """
        设置用户偏好
        
        如: set_preference("语言", "中文")
        """
        self.profile["preferences"][key] = value
        self._save()

    def to_prompt_section(self) -> str:
        """
        生成用于 LLM 提示词的用户信息
        
        示例输出:
            用户名称：L君
            用户偏好：语言=中文
            关于用户：喜欢编程；喜欢Python
        """
        lines = [f"用户名称：{self.get_name()}"]
        if self.profile["preferences"]:
            prefs = "、".join(f"{k}={v}" for k, v in self.profile["preferences"].items())
            lines.append(f"用户偏好：{prefs}")
        if self.profile["facts"]:
            facts = "；".join(self.profile["facts"][:5])  # 最多显示 5 条
            lines.append(f"关于用户：{facts}")
        return "\n".join(lines)