from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGroupBox,
    QLabel, QPushButton, QCheckBox, QListWidget,
    QListWidgetItem, QMessageBox
)
from PyQt5.QtGui import QFont
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager


class StorageCleanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("清除存储占用")
        self.setGeometry(200, 200, 500, 450)
        
        self.selected_categories = []
        self.checkboxes = {}
        
        debug_manager.log_info('打开存储清除对话框', 'storage')
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
        
        total_size = self.parent().classifier.get_storage_size()
        total_label = QLabel(f"<b>总存储占用:</b> {self._format_size(total_size)}")
        total_label.setFont(QFont("Arial", 11, QFont.Bold))
        layout.addWidget(total_label)
        
        storage_details = self.parent().classifier.get_storage_details()
        
        for key, info in storage_details.items():
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
        storage_details = self.parent().classifier.get_storage_details()
        total = 0
        for key in self.selected_categories:
            total += storage_details[key]['size']
        self.selected_size_label.setText(f"选中大小: {self._format_size(total)}")
    
    def select_all(self):
        for key in self.checkboxes:
            self.checkboxes[key].setChecked(True)
    
    def deselect_all(self):
        for key in self.checkboxes:
            self.checkboxes[key].setChecked(False)
    
    def clear_selected(self):
        debug_manager.log_info('清除选中的存储类别', 'storage', categories=self.selected_categories)
        if not self.selected_categories:
            debug_manager.log_warning('没有选择任何类别', 'storage')
            QMessageBox.warning(self, "警告", "请选择要清除的类别")
            return
        
        storage_details = self.parent().classifier.get_storage_details()
        
        confirm_text = "将清除以下数据:\n\n"
        for key in self.selected_categories:
            info = storage_details[key]
            confirm_text += f"- {info['name']} ({self._format_size(info['size'])})\n"
        
        confirm_text += f"\n总计: {self.selected_size_label.text().replace('选中大小: ', '')}"
        
        reply = QMessageBox.question(
            self,
            "确认清除",
            confirm_text,
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            debug_manager.log_info('用户确认清除', 'storage', categories=self.selected_categories)
            self.parent().classifier.clear_categories(self.selected_categories)
            debug_manager.log_info('存储清除完成', 'storage', categories=self.selected_categories)
            QMessageBox.information(self, "成功", "存储已清除")
            self.accept()