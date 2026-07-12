from PyQt5.QtWidgets import QDialog
from PyQt5.QtCore import pyqtSlot

from core.theme_manager import theme_manager


class ThemedDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._connect_theme_signal()

    def _connect_theme_signal(self):
        theme_manager.theme_changed.connect(self._on_theme_changed)

    @pyqtSlot(object)
    def _on_theme_changed(self, colors):
        self._apply_theme()

    def _apply_theme(self):
        pass

    def _create_dialog_base_style(self) -> str:
        c = self._get_colors()
        return f"""
            QDialog {{
                background-color: {c.window_bg};
            }}
            QLabel {{
                color: {c.text_primary};
            }}
            QPushButton {{
                background-color: {c.button_bg};
                color: {c.text_primary};
                border: 1px solid {c.button_border};
                border-radius: 3px;
                padding: 6px 16px;
            }}
            QPushButton:hover {{
                background-color: {c.button_hover};
            }}
            QLineEdit {{
                background-color: {c.input_bg};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: 3px;
                padding: 4px 8px;
            }}
            QListWidget {{
                background-color: {c.list_bg};
                color: {c.text_primary};
                border: 1px solid {c.border};
                border-radius: 3px;
            }}
            QListWidget::item:hover {{
                background-color: {c.item_hover};
            }}
            QListWidget::item:selected {{
                background-color: {c.item_selected};
            }}
            QCheckBox {{
                color: {c.text_primary};
            }}
        """

    def _get_colors(self):
        return theme_manager.colors

    def closeEvent(self, event):
        theme_manager.theme_changed.disconnect(self._on_theme_changed)
        super().closeEvent(event)