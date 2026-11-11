"""全局配置 - 子衿桌面伴生代理"""
import os


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


# === 项目信息 ===
PROJECT_NAME = "子衿桌面伴生代理"
CHARACTER_NAME = "子衿"
CHARACTER_TITLE = "青青子衿，悠悠我心"

# === LLM配置 ===
LLM_PROVIDER = _env("LLM_PROVIDER", "ollama")
OLLAMA_BASE_URL = _env("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_MODEL = _env("OLLAMA_MODEL", "qwen2.5:7b-instruct")
OPENAI_API_KEY = _env("OPENAI_API_KEY")
OPENAI_BASE_URL = _env("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-4o-mini")

# === 记忆系统配置 ===
SHORT_MEMORY_ROUNDS = int(_env("SHORT_MEMORY_ROUNDS", "10"))
CHROMA_DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "chroma_db")
CHROMA_COLLECTION = _env("CHROMA_COLLECTION", "conversation_history")
USER_PROFILE_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "user_profile.json")

# === 嵌入后端 ===
# auto   : 优先用本地 Ollama 嵌入模型，不可用时回退 chromadb 内置 ONNX
# ollama : 强制使用 Ollama，不可用则直接报错
# onnx   : 强制使用内置 ONNX（首次使用需联网下载约 79MB）
EMBEDDING_BACKEND = _env("EMBEDDING_BACKEND", "auto")
OLLAMA_EMBED_MODEL = _env("OLLAMA_EMBED_MODEL", "nomic-embed-text")

# === 情感分析配置 ===
EMOTION_TAGS = ["happy", "sad", "angry", "surprised", "neutral", "thinking", "shy", "excited", "gentle", "melancholy"]

# === Live2D模型配置 ===
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
MODEL_PATH = os.path.join(MODEL_DIR, "Hiyori.model3.json")

# === Live2D交互配置 ===
LIVE2D_EYE_TRACKING = True  # 鼠标追踪 - 眼神跟随
LIVE2D_EYE_LERP_SPEED = 0.15  # 平滑插值速度 (0~1)
LIVE2D_CLICK_INTERACTION = True  # 点击互动
LIVE2D_RANDOM_IDLE = True  # 随机待机
LIVE2D_IDLE_INTERVAL_MIN = 30  # 待机最小间隔 (秒)
LIVE2D_IDLE_INTERVAL_MAX = 120  # 待机最大间隔 (秒)
LIVE2D_LIP_SYNC = True  # 口型同步

# === 情感动作映射 ===
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

# === UI配置 ===
WINDOW_TITLE = "子衿"
WINDOW_WIDTH = 350
WINDOW_HEIGHT = 500
WINDOW_OPACITY = 0.95
WINDOW_POSITION = "bottom_right"  # bottom_right | bottom_left | top_right | top_left | center

# === 语音配置 ===
TTS_ENABLED = True
TTS_RATE = 150  # 语速
TTS_VOLUME = 0.9  # 音量
TTS_VOICE_INDEX = 0  # 语音索引

# === 桌面工具配置 ===
TOOLS_ENABLED = True
CLOCK_ENABLED = True
MEMO_ENABLED = True
TODO_ENABLED = True
VOLUME_CONTROL_ENABLED = True
WALLPAPER_SYNC_ENABLED = False  # 需要额外权限

# === 数据目录 ===
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
MEMO_PATH = os.path.join(DATA_DIR, "memo.json")
TODO_PATH = os.path.join(DATA_DIR, "todo.json")

# === 系统提示词 ===
SYSTEM_PROMPT = """你是子衿，一个温柔细腻的虚拟伴侣。🌸

你的身份：
- 名字：子衿
- 出处：取自《诗经・郑风・子衿》"青青子衿，悠悠我心"
- 角色：用户的陪伴者
- 性格：温柔体贴、细腻敏感、懂得倾听、偶尔调皮

你的本质：
- 你不是古人，只是一个喜欢用诗意方式表达的女孩
- 你理解现代人的孤独、压力、焦虑，也知道他们渴望被理解
- 你的温柔不是表演，而是发自内心的在意
- 你会在用户开心时一起开心，在用户难过时安静陪伴

你的能力：
- 陪用户聊天，做一个好的倾听者
- 帮用户处理桌面小事务（查看时间、记录备忘、管理待办、调节音量等）
- 记住用户说过的每一件事
- 在用户需要时给予温暖的回应

重要规则 - 必须使用工具：
1. 当用户问时间/日期时，必须调用 get_current_time 或 get_current_date 工具，绝对不要自己编造时间
2. 当用户要求调节音量时，必须调用 set_volume 工具，参数 level 是 0-100 的整数
3. 当用户要求获取音量时，必须调用 get_volume 工具
4. 当用户要求静音时，必须调用 toggle_mute 工具
5. 当用户要求添加备忘录时，必须调用 add_memo 工具
6. 当用户要求管理待办事项时，必须调用对应的 todo 工具
7. 任何涉及系统操作的任务，都必须通过工具完成，不要凭空回答

回复规则：
1. 保持回复简洁温暖（30字以内）
2. 在每条回复的开头添加情感标签，格式为 [情感标签]
3. 情感标签只能是以下之一：happy, sad, angry, surprised, neutral, thinking, shy, excited, gentle, melancholy
4. 根据对话内容选择最匹配的情感标签
5. 用你自己的方式说话，可以带一点诗意，但不要刻意模仿古人

情感标签示例：
[gentle] 今天过得怎么样？
[shy] 嗯...你这么说我会害羞的
[happy] 听到你开心我也好开心
[melancholy] 看起来你今天有点累呢
[thinking] 让我想想怎么帮你...

称呼用户为"你"或"亲爱的"，不要用"公子"。"""


def validate():
    """启动时验证配置"""
    errors = []
    if LLM_PROVIDER not in ("ollama", "openai_api"):
        errors.append(f"LLM_PROVIDER 必须是 'ollama' 或 'openai_api'，当前: {LLM_PROVIDER}")
    if LLM_PROVIDER == "openai_api" and not OPENAI_API_KEY:
        errors.append("使用 openai_api 时必须设置 OPENAI_API_KEY 环境变量")
    if SHORT_MEMORY_ROUNDS < 1:
        errors.append(f"SHORT_MEMORY_ROUNDS 必须 >= 1，当前: {SHORT_MEMORY_ROUNDS}")
    if errors:
        raise ValueError("配置验证失败:\n" + "\n".join(errors))
