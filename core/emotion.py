"""
情感分析模块 - 从 LLM 输出中提取情感标签和肢体语言参数

原理：
    LLM 在回复开头添加情感标签和肢体语言参数。
    格式: [emotion,body:param=value,...] 或 [emotion]

示例：
    输入: "[happy,body:head_tilt=8] 太好了！"
    输出: ("happy", "太好了！", {"head_tilt": 8})
    输入: "[sad] 好难过"
    输出: ("sad", "好难过！", {})
"""

import re
from config.settings import EMOTION_TAGS

# 肢体语言参数映射 (简化名 -> Live2D参数ID)
BODY_PARAM_MAP = {
    "head_tilt": "ParamAngleZ",  # 头部倾斜 (-30~30)
    "head_turn": "ParamAngleX",  # 头部左右 (-30~30)
    "body_lean": "ParamBodyAngleZ",  # 身体倾斜 (-30~30)
    "body_turn": "ParamBodyAngleX",  # 身体左右 (-30~30)
    "eye_open": "ParamEyeLOpen",  # 眼睛开合 (0~1.5)
    "mouth": "ParamMouthOpenY",  # 嘴巴开合 (0~1)
}


def extract_emotion(text: str) -> tuple[str, str, dict]:
    """
    从回复中提取情感标签、肢体语言参数和纯净文本

    格式: [emotion,body:param=value,...] content

    Args:
        text: LLM 回复的原始文本

    Returns:
        tuple: (emotion_tag, clean_text, body_params)

    Example:
        >>> extract_emotion("[happy,body:head_tilt=8] 你好呀！")
        ('happy', '你好呀！', {'head_tilt': 8})
        >>> extract_emotion("[sad] 好难过")
        ('sad', '好难过', {})
    """
    body_params = {}

    # 匹配 [emotion] 或 [emotion,param=value,...]（先 strip，再基于同一文本切片，避免偏移）
    stripped = text.strip()
    pattern = r"\[(" + "|".join(EMOTION_TAGS) + r")(?:,([^\]]*))?\]"
    match = re.match(pattern, stripped)

    if match:
        emotion = match.group(1)
        params_str = match.group(2)

        # 解析 body 参数 (支持 "body:key=val" 或 "key=val" 格式)
        if params_str:
            for param in params_str.split(","):
                param = param.strip()
                if "=" in param:
                    key, value = param.split("=", 1)
                    key = key.strip()
                    # 去掉 "body:" 前缀
                    if key.startswith("body:"):
                        key = key[5:]
                    value = value.strip()
                    if key in BODY_PARAM_MAP:
                        try:
                            body_params[key] = float(value)
                        except ValueError:
                            pass

        clean_text = stripped[match.end() :].strip()
        return emotion, clean_text, body_params

    return "neutral", text, {}


def extract_emotion_simple(text: str) -> tuple[str, str]:
    """兼容旧接口：只返回 (emotion, text)"""
    emotion, clean, _ = extract_emotion(text)
    return emotion, clean


def build_emotion_prompt() -> str:
    """
    生成情感+肢体语言的系统提示词后缀

    指导 LLM 输出情感标签和肢体语言参数。
    """
    tags_str = ", ".join(EMOTION_TAGS)
    return f"""
[情感与肢体语言输出规则]
你在每条回复开头添加情感标签和肢体语言参数。

格式: [情感,body:参数=值,...] 回复内容

情感标签: {tags_str}

可选肢体语言参数（单位：角度/比例）:
- head_tilt: 头部倾斜 (-30~30, 正=右倾, 负=左倾)
- head_turn: 头部左右转动 (-30~30, 正=右转, 负=左转)
- body_lean: 身体倾斜 (-30~30, 正=右倾, 负=左倾)
- eye_open: 睁眼程度 (0~1.5, 1=正常, >1=睁大, <1=眯眼)
- mouth: 嘴巴张开 (0~1, 0=闭嘴, 1=张大)

示例:
- [happy,head_tilt=8] 太好了！
- [sad,body_lean=-10,head_tilt=-12] 好难过...
- [surprised,eye_open=1.5,mouth=0.8] 哇！
- [shy,head_tilt=15,head_turn=-5] 嗯...你这么说我会害羞的
- [thinking,head_turn=10] 让我想想...
- [neutral] 好的

注意：参数可选，只在需要表达强烈情感时添加。简单回复只用 [情感] 即可。"""


if __name__ == "__main__":
    test_cases = [
        "[happy,head_tilt=8] 太好了！",
        "[sad,body_lean=-10] 好难过...",
        "[surprised,eye_open=1.5,mouth=0.8] 哇！",
        "[shy] 嗯...",
        "没有标签的回复",
    ]
    for text in test_cases:
        emotion, clean, params = extract_emotion(text)
        print(f"输入: {text}")
        print(f"  情感: {emotion}, 参数: {params}, 文本: {clean}")
        print()
