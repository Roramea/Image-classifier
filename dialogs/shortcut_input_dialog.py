from PyQt5.QtWidgets import QLabel, QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QKeyEvent

from core.utils import key_to_string, is_conflicting_key
from core.debug_manager import debug_manager
from .themed_dialog import ThemedDialog


class ShortcutInputDialog(ThemedDialog):
    key_selected = pyqtSignal(str)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置快捷键")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setFixedSize(320, 190)
        self.setModal(True)
        self.setFocusPolicy(Qt.StrongFocus)
        
        self.selected_key = None
        self.confirm_mode = False
        
        self.init_ui()
        self._apply_theme()
    
    def showEvent(self, event):
        super().showEvent(event)
        self.setFocus()
        self.grabKeyboard()
    
    def init_ui(self):
        main_layout = QVBoxLayout()
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        self.title_label = QLabel("请按下要绑定的按键")
        self.title_label.setAlignment(Qt.AlignCenter)
        
        self.key_display = QLabel("")
        self.key_display.setAlignment(Qt.AlignCenter)
        
        self.hint_label = QLabel("按 ESC 取消 | 按 Enter 确认")
        self.hint_label.setAlignment(Qt.AlignCenter)
        
        button_layout = QHBoxLayout()
        
        self.confirm_button = QPushButton("确认")
        self.confirm_button.setEnabled(False)
        self.confirm_button.clicked.connect(self.accept)
        
        self.cancel_button = QPushButton("取消")
        self.cancel_button.clicked.connect(self.reject)
        
        button_layout.addWidget(self.confirm_button)
        button_layout.addWidget(self.cancel_button)
        
        main_layout.addWidget(self.title_label)
        main_layout.addWidget(self.key_display)
        main_layout.addWidget(self.hint_label)
        main_layout.addLayout(button_layout)
        
        self.setLayout(main_layout)
    
    def keyPressEvent(self, event: QKeyEvent):
        key = event.key()
        debug_manager.log_info('快捷键对话框按键事件', 'shortcut', key=key, key_name=event.text())
        
        if key == Qt.Key_Escape:
            debug_manager.log_info('按下 ESC，关闭对话框', 'shortcut')
            self.reject()
            event.accept()
            return
        
        if key == Qt.Key_Enter or key == Qt.Key_Return:
            debug_manager.log_info('按下 Enter，selected_key:', 'shortcut', selected_key=self.selected_key)
            if self.selected_key:
                debug_manager.log_info('确认快捷键', 'shortcut', key=self.selected_key)
                self.accept()
                event.accept()
                return
            else:
                debug_manager.log_info('未选择按键，忽略 Enter', 'shortcut')
                event.accept()
                return
        
        if is_conflicting_key(key):
            debug_manager.log_info('冲突按键', 'shortcut', key=key)
            QMessageBox.warning(self, "警告", "该按键与导航功能冲突，请选择其他按键")
            event.accept()
            return
        
        key_str = key_to_string(key)
        debug_manager.log_info('转换按键', 'shortcut', key=key, key_str=key_str)
        if key_str:
            self.selected_key = key_str.lower()
            self.key_display.setText(key_str.upper())
            self.confirm_button.setEnabled(True)
            self.title_label.setText("按键已选择")
            self.confirm_mode = True
            debug_manager.log_info('按键已选择', 'shortcut', selected_key=self.selected_key)
            event.accept()
        else:
            debug_manager.log_info('无效按键', 'shortcut', key=key)
            event.ignore()
    
    def get_key(self) -> str:
        return self.selected_key
    
    def _apply_theme(self):
        c = self._get_colors()
        disabled_style = f"""
            QPushButton:disabled {{
                background-color: {c.button_pressed};
                color: {c.text_disabled};
            }}
        """
        self.setStyleSheet(self._create_dialog_base_style() + disabled_style)
        self.title_label.setStyleSheet(f"font-size: 16px; color: {c.text_primary}; font-weight: bold;")
        self.key_display.setStyleSheet(f"""
            font-size: 48px; 
            font-weight: bold; 
            color: {c.accent}; 
            border: 2px dashed {c.border}; 
            border-radius: 10px; 
            padding: 20px;
            background-color: {c.list_bg};
        """)
        self.hint_label.setStyleSheet(f"font-size: 12px; color: {c.text_hint};")
    
    def closeEvent(self, event):
        self.releaseKeyboard()
        super().closeEvent(event)
    
    def done(self, result):
        self.releaseKeyboard()
        super().done(result)