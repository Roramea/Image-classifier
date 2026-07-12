from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager
from core.utils import format_size
from .themed_dialog import ThemedDialog


class StorageCleanDialog(ThemedDialog):
    """存储清理对话框。

    职责：展示各类存储占用情况、让用户选择要清理的类别、返回用户的选择。
    不直接访问 ClassificationManager（核心服务），仅通过构造函数接收展示数据，
    通过 get_selected_categories() 返回选中类别，由 Presenter 执行实际清理。
    """

    def __init__(self, storage_size: int, storage_details: dict, parent=None):
        """初始化对话框。

        Args:
            storage_size: 总存储占用字节数
            storage_details: 各类别详情，结构为
                {category_key: {'name': str, 'description': str, 'files': [...], 'size': int}}
            parent: 父组件
        """
        super().__init__(parent)
        self.setWindowTitle("清除存储占用")
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setGeometry(200, 200, 500, 450)

        self._storage_size = storage_size
        self._storage_details = storage_details
        self.selected_categories = []
        self.checkboxes = {}
        self._group_boxes = []
        self._desc_labels = []
        self._file_lists = []

        debug_manager.log_info('打开存储清除对话框', 'storage', total_size=storage_size)
        self.init_ui()
        self._apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)

        self.total_label = QLabel(f"<b>总存储占用:</b> {format_size(self._storage_size)}")
        self.total_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(self.total_label)

        for key, info in self._storage_details.items():
            group = QGroupBox(f"{info['name']}")
            self._group_boxes.append(group)
            group_layout = QVBoxLayout(group)

            desc_label = QLabel(f"<small>{info['description']}</small>")
            self._desc_labels.append(desc_label)
            group_layout.addWidget(desc_label)

            size_label = QLabel(f"文件数量: {len(info['files'])} | 占用大小: {format_size(info['size'])}")
            group_layout.addWidget(size_label)

            checkbox = QCheckBox("选中清除")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda state, k=key: self.toggle_category(k, state))
            self.checkboxes[key] = checkbox
            group_layout.addWidget(checkbox)

            if info['files']:
                file_list = QListWidget()
                file_list.setMaximumHeight(80)
                self._file_lists.append(file_list)
                for f in info['files']:
                    item = QListWidgetItem(f"{f['name']} ({format_size(f['size'])})")
                    file_list.addItem(item)
                group_layout.addWidget(file_list)

            layout.addWidget(group)

        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(self.select_all_btn)
        btn_layout.addWidget(self.deselect_all_btn)
        layout.addLayout(btn_layout)

        self.selected_size_label = QLabel("选中大小: 0 B")
        self.selected_size_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selected_size_label)

        self.clear_btn = QPushButton("清除选中")
        self.clear_btn.clicked.connect(self.clear_selected)
        layout.addWidget(self.clear_btn)

        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        layout.addWidget(self.cancel_btn)
    
    def _apply_theme(self):
        c = self._get_colors()
        group_box_style = f"""
            QGroupBox {{
                border: 1px solid {c.group_box_border};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
                color: {c.group_box_title};
                font-weight: bold;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
            }}
        """
        self.setStyleSheet(self._create_dialog_base_style() + group_box_style)
        for desc_label in self._desc_labels:
            desc_label.setStyleSheet(f"color: {c.text_hint};")
        self.clear_btn.setStyleSheet(f"background-color: {c.danger_pressed}; color: white; border: none;")

    def toggle_category(self, key: str, state: int):
        if state == Qt.Checked:
            if key not in self.selected_categories:
                self.selected_categories.append(key)
        else:
            if key in self.selected_categories:
                self.selected_categories.remove(key)
        self.update_selected_size()

    def update_selected_size(self):
        total = 0
        for key in self.selected_categories:
            total += self._storage_details[key]['size']
        self.selected_size_label.setText(f"选中大小: {format_size(total)}")

    def select_all(self):
        for key in self.checkboxes:
            self.checkboxes[key].setChecked(True)

    def deselect_all(self):
        for key in self.checkboxes:
            self.checkboxes[key].setChecked(False)

    def clear_selected(self):
        """确认后关闭对话框，不执行实际清理。

        实际清理由 Presenter 调用 ClassificationManager.clear_categories 执行。
        """
        debug_manager.log_info('用户确认清除选中类别', 'storage', categories=self.selected_categories)
        if not self.selected_categories:
            debug_manager.log_warning('没有选择任何类别', 'storage')
            QMessageBox.warning(self, "警告", "请选择要清除的类别")
            return

        confirm_text = "将清除以下数据:\n\n"
        for key in self.selected_categories:
            info = self._storage_details[key]
            confirm_text += f"- {info['name']} ({format_size(info['size'])})\n"

        confirm_text += f"\n总计: {self.selected_size_label.text().replace('选中大小: ', '')}"

        reply = QMessageBox.question(
            self,
            "确认清除",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            debug_manager.log_info('用户确认清除，关闭对话框', 'storage', categories=self.selected_categories)
            self.accept()

    def get_selected_categories(self) -> list:
        """返回用户选中的类别键列表，如 ['shortcuts', 'duplicates']。仅在 accept 后有意义。"""
        return self.selected_categories
