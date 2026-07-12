from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton,
    QScrollArea, QWidget, QGroupBox
)
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager
from core.theme_manager import theme_manager
from .themed_dialog import ThemedDialog


class SettingsDialog(ThemedDialog):
    """设置对话框。

    职责：作为应用全局设置的入口，包含主题切换等设置项。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setGeometry(200, 200, 520, 560)
        self.setMinimumSize(420, 420)

        debug_manager.log_info('打开设置对话框', 'settings')
        self._init_ui()
        self._apply_theme()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setAlignment(Qt.AlignTop)
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(10)

        theme_group = QGroupBox("主题设置")
        theme_layout = QVBoxLayout(theme_group)
        theme_layout.setSpacing(8)

        self.theme_btn = QPushButton()
        self._update_theme_button_text()
        self.theme_btn.clicked.connect(self._toggle_theme)
        theme_layout.addWidget(self.theme_btn)

        content_layout.addWidget(theme_group)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        theme_manager.theme_changed.connect(self._on_theme_changed)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(self.ok_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.cancel_btn)

        layout.addLayout(btn_layout)
    
    def _apply_theme(self):
        c = self._get_colors()
        base_style = self._create_dialog_base_style()
        group_box_style = f"""
            QGroupBox {{
                font-weight: bold;
                color: {c.text_primary};
                border: 1px solid {c.group_box_border};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {c.group_box_title};
            }}
        """
        self.setStyleSheet(base_style + group_box_style)
        self.theme_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {c.info};
                border: 1px solid {c.info_pressed};
                border-radius: 5px;
                padding: 6px 12px;
                font-size: 12px;
                color: white;
            }}
            QPushButton:hover {{
                background-color: {c.info_hover};
            }}
            QPushButton:pressed {{
                background-color: {c.info_pressed};
            }}
        """)

    def _update_theme_button_text(self):
        if theme_manager.mode.value == "dark":
            self.theme_btn.setText("切换到浅色主题")
        else:
            self.theme_btn.setText("切换到深色主题")

    def _toggle_theme(self):
        theme_manager.toggle()

    def _on_theme_changed(self, colors):
        self._update_theme_button_text()
        self._apply_theme()
