from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QPushButton,
    QLabel, QScrollArea, QWidget
)
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager


class SettingsDialog(QDialog):
    """设置对话框。

    职责：作为应用全局设置的入口，具体的设置项后续填充。
    当前为空框架，仅包含占位提示与确定/取消按钮。
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("设置")
        # 移除标题栏右侧默认的问号帮助按钮（未填充实际功能）
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setGeometry(200, 200, 520, 560)
        self.setMinimumSize(420, 420)

        debug_manager.log_info('打开设置对话框', 'settings')
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        # 占位提示：具体设置项后续填充
        placeholder = QLabel("设置项稍后填充")
        placeholder.setAlignment(Qt.AlignCenter)
        placeholder.setStyleSheet("color: #7f8c8d; font-size: 13px;")
        layout.addWidget(placeholder)

        # 预留滚动区域，便于后续添加多个设置项
        scroll_area = QScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setStyleSheet("QScrollArea { border: none; }")
        scroll_content = QWidget()
        content_layout = QVBoxLayout(scroll_content)
        content_layout.setAlignment(Qt.AlignTop)
        scroll_area.setWidget(scroll_content)
        layout.addWidget(scroll_area, 1)

        # 底部按钮区
        btn_layout = QHBoxLayout()
        btn_layout.addStretch(1)

        ok_btn = QPushButton("确定")
        ok_btn.clicked.connect(self.accept)
        btn_layout.addWidget(ok_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        layout.addLayout(btn_layout)
