from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager


class StorageCleanDialog(QDialog):
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
        self.setGeometry(200, 200, 500, 450)

        self._storage_size = storage_size
        self._storage_details = storage_details
        self.selected_categories = []
        self.checkboxes = {}

        debug_manager.log_info('打开存储清除对话框', 'storage', total_size=storage_size)
        self.init_ui()

    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

    def init_ui(self):
        layout = QVBoxLayout(self)

        total_label = QLabel(f"<b>总存储占用:</b> {self._format_size(self._storage_size)}")
        total_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(total_label)

        for key, info in self._storage_details.items():
            group = QGroupBox(f"{info['name']}")
            group_layout = QVBoxLayout(group)

            desc_label = QLabel(f"<small>{info['description']}</small>")
            desc_label.setStyleSheet("color: #7f8c8d;")
            group_layout.addWidget(desc_label)

            size_label = QLabel(f"文件数量: {len(info['files'])} | 占用大小: {self._format_size(info['size'])}")
            group_layout.addWidget(size_label)

            checkbox = QCheckBox("选中清除")
            checkbox.setChecked(False)
            checkbox.stateChanged.connect(lambda state, k=key: self.toggle_category(k, state))
            self.checkboxes[key] = checkbox
            group_layout.addWidget(checkbox)

            if info['files']:
                file_list = QListWidget()
                file_list.setMaximumHeight(80)
                for f in info['files']:
                    item = QListWidgetItem(f"{f['name']} ({self._format_size(f['size'])})")
                    file_list.addItem(item)
                group_layout.addWidget(file_list)

            layout.addWidget(group)

        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all)

        btn_layout = QHBoxLayout()
        btn_layout.addWidget(select_all_btn)
        btn_layout.addWidget(deselect_all_btn)
        layout.addLayout(btn_layout)

        self.selected_size_label = QLabel("选中大小: 0 B")
        self.selected_size_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.selected_size_label)

        clear_btn = QPushButton("清除选中")
        clear_btn.clicked.connect(self.clear_selected)
        clear_btn.setStyleSheet("background-color: #c0392b; color: white;")
        layout.addWidget(clear_btn)

        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        layout.addWidget(cancel_btn)

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
        self.selected_size_label.setText(f"选中大小: {self._format_size(total)}")

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
            confirm_text += f"- {info['name']} ({self._format_size(info['size'])})\n"

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
