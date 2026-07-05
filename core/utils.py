from PyQt5.QtCore import Qt


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