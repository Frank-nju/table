"""
通用辅助函数模块

提供跨模块共享的基础工具函数
"""


def safe_text(value):
    """安全获取文本，None 返回空字符串"""
    if value is None:
        return ""
    text = str(value).strip()
    return "" if text.lower() == "none" else text


def safe_bool(value):
    """安全获取布尔值"""
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).lower() in {'true', '1', 'yes', 'y', '是'}
