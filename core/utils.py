from PyQt5.QtCore import Qt


def key_to_string(key: int) -> str:
    if key >= Qt.Key_A and key <= Qt.Key_Z:
        return chr(key).lower()
    if key >= Qt.Key_0 and key <= Qt.Key_9:
        return str(key - Qt.Key_0)
    
    if key >= Qt.Key_NumPad0 and key <= Qt.Key_NumPad9:
        return str(key - Qt.Key_NumPad0)
    
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
        Qt.Key_NumPad0: '0',
        Qt.Key_NumPad1: '1',
        Qt.Key_NumPad2: '2',
        Qt.Key_NumPad3: '3',
        Qt.Key_NumPad4: '4',
        Qt.Key_NumPad5: '5',
        Qt.Key_NumPad6: '6',
        Qt.Key_NumPad7: '7',
        Qt.Key_NumPad8: '8',
        Qt.Key_NumPad9: '9',
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