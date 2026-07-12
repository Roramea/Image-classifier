from PyQt5.QtCore import pyqtSignal, QObject
from enum import Enum


class ThemeMode(Enum):
    DARK = "dark"
    LIGHT = "light"


class ThemeColors:
    def __init__(self, mode: ThemeMode):
        self.mode = mode
        self._init_colors()

    def _init_colors(self):
        if self.mode == ThemeMode.DARK:
            self.window_bg = "#2d2d2d"
            self.widget_bg = "#2d2d2d"
            self.list_bg = "#1e1e1e"
            self.input_bg = "#1e1e1e"
            
            self.text_primary = "#ecf0f1"
            self.text_secondary = "#95a5a6"
            self.text_disabled = "#7f8c8d"
            self.text_hint = "#7f8c8d"
            self.text_on_accent = "#ffffff"
            
            self.accent = "#3498db"
            self.accent_hover = "#2980b9"
            self.accent_dark = "#1a5276"
            
            self.button_bg = "#34495e"
            self.button_border = "#2c3e50"
            self.button_hover = "#3d566e"
            self.button_pressed = "#2c3e50"
            
            self.success = "#27ae60"
            self.success_hover = "#2ecc71"
            self.success_pressed = "#1e8449"
            
            self.warning = "#e67e22"
            self.warning_hover = "#f39c12"
            self.warning_pressed = "#d35400"
            
            self.danger = "#e74c3c"
            self.danger_hover = "#ff6b6b"
            self.danger_pressed = "#c0392b"
            
            self.info = "#9b59b6"
            self.info_hover = "#8e44ad"
            self.info_pressed = "#6c3483"
            
            self.neutral = "#7f8c8d"
            self.neutral_hover = "#95a5a6"
            self.neutral_pressed = "#566573"
            
            self.border = "#34495e"
            self.border_light = "#2c3e50"
            self.scrollbar = "#34495e"
            
            self.slider_groove = "#2c3e50"
            self.slider_handle = "#3498db"
            self.slider_tick = "#7f8c8d"
            
            self.progress_bg = "#1e1e1e"
            self.progress_bar = "#3498db"
            
            self.group_box_border = "#34495e"
            self.group_box_title = "#3498db"
            
            self.item_hover = "#34495e"
            self.item_selected = "#34495e"
            self.item_alternate = "#252525"
            
            self.image_bg = "#1a1a1a"
        else:
            self.window_bg = "#f5f5f5"
            self.widget_bg = "#fafafa"
            self.list_bg = "#ffffff"
            self.input_bg = "#ffffff"
            
            self.text_primary = "#2c3e50"
            self.text_secondary = "#7f8c8d"
            self.text_disabled = "#bdc3c7"
            self.text_hint = "#95a5a6"
            self.text_on_accent = "#ffffff"
            
            self.accent = "#3498db"
            self.accent_hover = "#2980b9"
            self.accent_dark = "#1a5276"
            
            self.button_bg = "#ecf0f1"
            self.button_border = "#bdc3c7"
            self.button_hover = "#dfe6e9"
            self.button_pressed = "#bdc3c7"
            
            self.success = "#27ae60"
            self.success_hover = "#2ecc71"
            self.success_pressed = "#1e8449"
            
            self.warning = "#e67e22"
            self.warning_hover = "#f39c12"
            self.warning_pressed = "#d35400"
            
            self.danger = "#e74c3c"
            self.danger_hover = "#ff6b6b"
            self.danger_pressed = "#c0392b"
            
            self.info = "#9b59b6"
            self.info_hover = "#8e44ad"
            self.info_pressed = "#6c3483"
            
            self.neutral = "#95a5a6"
            self.neutral_hover = "#aab7b8"
            self.neutral_pressed = "#7f8c8d"
            
            self.border = "#bdc3c7"
            self.border_light = "#dfe6e9"
            self.scrollbar = "#bdc3c7"
            
            self.slider_groove = "#dfe6e9"
            self.slider_handle = "#3498db"
            self.slider_tick = "#95a5a6"
            
            self.progress_bg = "#ecf0f1"
            self.progress_bar = "#3498db"
            
            self.group_box_border = "#bdc3c7"
            self.group_box_title = "#3498db"
            
            self.item_hover = "#dfe6e9"
            self.item_selected = "#3498db"
            self.item_alternate = "#f8f9fa"
            
            self.image_bg = "#e8e8e8"


class ThemeManager(QObject):
    theme_changed = pyqtSignal(ThemeColors)

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        super().__init__()
        self._initialized = True
        self._current_mode = ThemeMode.DARK
        self._colors = ThemeColors(self._current_mode)

    @property
    def colors(self) -> ThemeColors:
        return self._colors

    @property
    def mode(self) -> ThemeMode:
        return self._current_mode

    def set_mode(self, mode: ThemeMode):
        if self._current_mode != mode:
            self._current_mode = mode
            self._colors = ThemeColors(self._current_mode)
            self.theme_changed.emit(self._colors)

    def toggle(self):
        new_mode = ThemeMode.LIGHT if self._current_mode == ThemeMode.DARK else ThemeMode.DARK
        self.set_mode(new_mode)

    def get_stylesheet(self, template: str) -> str:
        return template.format(**vars(self._colors))


theme_manager = ThemeManager()