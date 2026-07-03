import os

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QListWidget,
    QListWidgetItem, QPushButton, QLineEdit, QMessageBox,
    QLabel, QToolButton, QInputDialog
)
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt

from core.debug_manager import debug_manager


class FolderSelectDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("选择或新建文件夹")
        self.setGeometry(200, 200, 600, 450)
        
        self.current_path = os.path.expanduser("~")
        self.selected_path = ""
        
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        path_layout = QHBoxLayout()
        
        self.path_edit = QLineEdit(self.current_path)
        self.path_edit.setReadOnly(True)
        path_layout.addWidget(self.path_edit)
        
        refresh_btn = QToolButton()
        refresh_btn.setText("↻")
        refresh_btn.clicked.connect(self.refresh_list)
        path_layout.addWidget(refresh_btn)
        
        layout.addLayout(path_layout)
        
        self.folder_list = QListWidget()
        self.folder_list.itemDoubleClicked.connect(self.on_folder_double_clicked)
        self.folder_list.itemClicked.connect(self.on_folder_clicked)
        layout.addWidget(self.folder_list)
        
        btn_layout = QHBoxLayout()
        
        up_btn = QPushButton("上一级")
        up_btn.clicked.connect(self.go_up)
        btn_layout.addWidget(up_btn)
        
        new_folder_btn = QPushButton("新建文件夹")
        new_folder_btn.clicked.connect(self.create_new_folder)
        btn_layout.addWidget(new_folder_btn)
        
        btn_layout.addStretch()
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)
        
        select_btn = QPushButton("选择")
        select_btn.clicked.connect(self.accept)
        select_btn.setStyleSheet("background-color: #3498db; color: white;")
        btn_layout.addWidget(select_btn)
        
        layout.addLayout(btn_layout)
        
        self.refresh_list()
    
    def refresh_list(self):
        self.folder_list.clear()
        
        try:
            entries = os.listdir(self.current_path)
            entries.sort(key=lambda x: (not os.path.isdir(os.path.join(self.current_path, x)), x.lower()))
            
            if self.current_path != os.path.dirname(self.current_path):
                parent_item = QListWidgetItem("..")
                parent_item.setData(Qt.UserRole, os.path.dirname(self.current_path))
                self.folder_list.addItem(parent_item)
            
            for entry in entries:
                full_path = os.path.join(self.current_path, entry)
                if os.path.isdir(full_path):
                    item = QListWidgetItem(f"📁 {entry}")
                    item.setData(Qt.UserRole, full_path)
                    self.folder_list.addItem(item)
        except Exception as e:
            debug_manager.log_exception(e, 'folder_select', current_path=self.current_path)
            QMessageBox.warning(self, "错误", f"无法读取目录: {str(e)}")
    
    def go_up(self):
        parent_path = os.path.dirname(self.current_path)
        if parent_path and parent_path != self.current_path:
            self.current_path = parent_path
            self.path_edit.setText(self.current_path)
            self.refresh_list()
    
    def on_folder_double_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path:
            self.current_path = path
            self.path_edit.setText(self.current_path)
            self.refresh_list()
    
    def on_folder_clicked(self, item):
        path = item.data(Qt.UserRole)
        if path and os.path.isdir(path):
            self.selected_path = path
    
    def create_new_folder(self):
        folder_name, ok = QInputDialog.getText(self, "新建文件夹", "请输入文件夹名称:")
        if not ok or not folder_name.strip():
            return
        
        folder_name = folder_name.strip()
        original_name = folder_name
        
        invalid_chars = '<>:\"/\\|?*'
        for char in invalid_chars:
            folder_name = folder_name.replace(char, '')
        
        folder_name = folder_name.strip()
        if not folder_name:
            debug_manager.log_warning('文件夹名称包含无效字符', 'folder_select', original_name=original_name, invalid_chars=invalid_chars)
            QMessageBox.warning(self, "警告", "文件夹名称不能包含特殊字符")
            return
        
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL', 'COM1', 'COM2', 'COM3', 'COM4', 'COM5', 'COM6', 'COM7', 'COM8', 'COM9', 'LPT1', 'LPT2', 'LPT3', 'LPT4', 'LPT5', 'LPT6', 'LPT7', 'LPT8', 'LPT9']
        if folder_name.upper() in reserved_names or folder_name.startswith('.'):
            debug_manager.log_warning('无效的文件夹名称', 'folder_select', folder_name=folder_name, is_reserved=folder_name.upper() in reserved_names)
            QMessageBox.warning(self, "警告", "无效的文件夹名称")
            return
        
        new_path = os.path.join(self.current_path, folder_name)
        
        try:
            if os.path.exists(new_path):
                debug_manager.log_warning('文件夹已存在', 'folder_select', path=new_path)
                QMessageBox.warning(self, "警告", "文件夹已存在")
                return
            
            os.makedirs(new_path)
            debug_manager.log_info('文件夹创建成功', 'folder_select', path=new_path)
            self.refresh_list()
            
            for i in range(self.folder_list.count()):
                item = self.folder_list.item(i)
                if item.data(Qt.UserRole) == new_path:
                    self.folder_list.setCurrentItem(item)
                    self.selected_path = new_path
                    break
        except PermissionError:
            debug_manager.log_error('没有权限创建文件夹', 'folder_select', path=new_path)
            QMessageBox.warning(self, "错误", "没有权限创建文件夹，请检查路径权限")
        except Exception as e:
            debug_manager.log_exception(e, 'folder_select', path=new_path, folder_name=folder_name)
            QMessageBox.warning(self, "错误", f"创建文件夹失败: {str(e)}")
    
    def get_selected_path(self):
        if self.selected_path:
            return self.selected_path
        return self.current_path
    
    def accept(self):
        self.selected_path = self.get_selected_path()
        super().accept()


