import os
import re
from typing import List

from PyQt5.QtCore import Qt


def format_size(size: int) -> str:
    if size < 1024:
        return f"{size} B"
    elif size < 1024 * 1024:
        return f"{size / 1024:.2f} KB"
    else:
        return f"{size / (1024 * 1024):.2f} MB"


def key_to_string(key: int) -> str:
    """将 Qt 键码转换为字符串表示。

    小键盘数字键在 Qt 中会映射到 Qt.Key_0 ~ Qt.Key_9（带 KeypadModifier），
    因此无需单独处理 NumPad 枚举（PyQt5 中不存在 Qt.Key_NumPad0 等枚举）。
    """
    if key >= Qt.Key_A and key <= Qt.Key_Z:
        return chr(key).lower()
    if key >= Qt.Key_0 and key <= Qt.Key_9:
        return str(key - Qt.Key_0)

    special_keys = {
        Qt.Key_F1: 'f1',
        Qt.Key_F2: 'f2',
        Qt.Key_F3: 'f3',
        Qt.Key_F4: 'f4',
        Qt.Key_F5: 'f5',
        Qt.Key_F6: 'f6',
        Qt.Key_F7: 'f7',
        Qt.Key_F8: 'f8',
        Qt.Key_F9: 'f9',
        Qt.Key_F10: 'f10',
        Qt.Key_F11: 'f11',
        Qt.Key_F12: 'f12',
        Qt.Key_Space: 'space',
        Qt.Key_Backspace: 'backspace',
        Qt.Key_Delete: 'delete',
        Qt.Key_Home: 'home',
        Qt.Key_End: 'end',
    }

    return special_keys.get(key, "")


def is_conflicting_key(key: int) -> bool:
    conflict_keys = [
        Qt.Key_Left,
        Qt.Key_Right,
        Qt.Key_Up,
        Qt.Key_Down,
        Qt.Key_Tab,
        Qt.Key_Enter,
        Qt.Key_Return,
        Qt.Key_Escape,
        Qt.Key_Control,
        Qt.Key_Shift,
        Qt.Key_Alt,
        Qt.Key_Meta,
        Qt.Key_Insert,
        Qt.Key_PageUp,
        Qt.Key_PageDown,
    ]
    return key in conflict_keys


COPY_NAME_PATTERNS = [
    r'[（(]\d+[）)]$',
    r'[-_\s]*副本\d*$',
    r'[-_\s]*copy\d*$',
    r'[-_\s]*Copy\d*$',
    r'[-_\s]*COPY\d*$',
    r'[-_]\d+$',
    r' \d+$',
]


def get_copy_score(filepath: str) -> int:
    """计算文件名的"副本程度"分数。

    分数越高，越可能是副本文件，越应该被优先删除。
    返回 0 表示未检测到副本特征。
    """
    filename = os.path.splitext(os.path.basename(filepath))[0]
    score = 0

    for pattern in COPY_NAME_PATTERNS:
        if re.search(pattern, filename, re.IGNORECASE):
            score += 10
            match = re.search(r'(\d+)', filename[::-1])
            if match:
                num = int(match.group(1)[::-1])
                score += min(num, 50)
            break

    if re.search(r'[（(]\d+[）)]', filename):
        score += 5

    return score


def smart_sort_duplicate_paths(paths: List[str]) -> List[str]:
    """对重复图片路径进行智能排序。

    排序规则（按优先级）：
    1. 副本命名特征最少的排在最前面（优先保留）
    2. 文件名较短的排在前面
    3. 修改时间较早的排在前面

    Returns:
        排序后的路径列表，首张为最应保留的图片
    """
    if len(paths) <= 1:
        return paths

    def sort_key(path: str):
        copy_score = get_copy_score(path)
        filename = os.path.basename(path)
        name_len = len(filename)
        try:
            mtime = os.path.getmtime(path)
        except OSError:
            mtime = 0
        return (copy_score, name_len, -mtime)

    return sorted(paths, key=sort_key)