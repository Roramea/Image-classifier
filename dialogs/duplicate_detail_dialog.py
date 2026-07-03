import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QWidget, QMessageBox,
    QSizePolicy, QScrollArea
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QSize

from core.debug_manager import debug_manager


class DuplicateDetailDialog(QDialog):
    def __init__(self, paths_list: list, parent=None, md5_hashes=None):
        super().__init__(parent)
        self.setWindowTitle("重复图片详情")
        self.setGeometry(100, 100, 1000, 800)
        
        self.groups = []
        
        if not paths_list:
            debug_manager.log_warning('路径列表为空', 'duplicate')
            QMessageBox.warning(self, "警告", "没有足够的重复图片")
            self.reject()
            return
        
        if isinstance(paths_list[0], list):
            for i, paths in enumerate(paths_list):
                valid_paths = [p for p in paths if p and os.path.exists(p)]
                if len(valid_paths) > 1:
                    md5_hash = md5_hashes[i] if md5_hashes and i < len(md5_hashes) else None
                    self.groups.append((md5_hash, valid_paths))
        else:
            valid_paths = [p for p in paths_list if p and os.path.exists(p)]
            if len(valid_paths) > 1:
                self.groups = [(md5_hashes, valid_paths)]
        
        debug_manager.log_info('打开重复图片详情对话框', 'duplicate', group_count=len(self.groups))
        
        if not self.groups:
            debug_manager.log_warning('没有有效重复图片组', 'duplicate')
            QMessageBox.warning(self, "警告", "没有足够的重复图片")
            self.reject()
            return
        
        self.selected_paths = set()
        self.checkbox_map = {}
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        total_images = sum(len(paths) for _, paths in self.groups)
        info_label = QLabel(f"共发现 {len(self.groups)} 组重复图片，总计 {total_images} 张")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_label.setStyleSheet("color: #c0392b;")
        layout.addWidget(info_label)
        
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        
        for group_idx, (md5_hash, paths) in enumerate(self.groups):
            group_frame = QWidget()
            group_layout = QVBoxLayout(group_frame)
            group_layout.setContentsMargins(10, 10, 10, 10)
            group_frame.setStyleSheet("border: 1px solid #34495e; border-radius: 5px; margin-bottom: 10px;")
            
            group_label = QLabel(f"重复组 {group_idx + 1}（{len(paths)}张图片）")
            group_label.setFont(QFont("Arial", 10, QFont.Bold))
            group_label.setStyleSheet("color: #3498db;")
            group_layout.addWidget(group_label)
            
            grid_layout = QGridLayout()
            
            for i, path in enumerate(paths):
                row = i // 2
                col = i % 2
                
                img_widget = QWidget()
                img_layout = QVBoxLayout(img_widget)
                
                checkbox = QCheckBox(f"图片 {i + 1}")
                if i > 0:
                    checkbox.setChecked(True)
                    self.selected_paths.add(path)
                self.checkbox_map[path] = checkbox
                checkbox.stateChanged.connect(lambda state, p=path: self.toggle_path(p, state))
                img_layout.addWidget(checkbox)
                
                try:
                    pixmap = QPixmap(path)
                    if not pixmap.isNull():
                        scaled_pixmap = pixmap.scaled(QSize(300, 200), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        img_label = QLabel()
                        img_label.setPixmap(scaled_pixmap)
                        img_label.setAlignment(Qt.AlignCenter)
                        img_label.setStyleSheet("background-color: #2a2a2a;")
                        img_layout.addWidget(img_label)
                    else:
                        img_layout.addWidget(QLabel("无法加载图片"))
                except Exception as e:
                    img_layout.addWidget(QLabel(f"加载失败: {str(e)[:20]}"))
                
                try:
                    file_info = self.get_file_info(path)
                    info_text = QLabel(file_info)
                    info_text.setWordWrap(True)
                    info_text.setFont(QFont("Arial", 8))
                    info_text.setStyleSheet("color: #7f8c8d;")
                    img_layout.addWidget(info_text)
                except Exception:
                    img_layout.addWidget(QLabel(f"文件名: {os.path.basename(path)}"))
                
                grid_layout.addWidget(img_widget, row, col)
            
            group_layout.addLayout(grid_layout)
            scroll_layout.addWidget(group_frame)
        
        scroll = QScrollArea()
        scroll.setWidget(scroll_area)
        scroll.setWidgetResizable(True)
        scroll.setFixedHeight(600)
        layout.addWidget(scroll)
        
        button_layout = QHBoxLayout()
        
        select_all_btn = QPushButton("全选")
        select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(select_all_btn)
        
        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(deselect_all_btn)
        
        keep_first_btn = QPushButton("只保留第一张")
        keep_first_btn.clicked.connect(self.keep_first_only)
        button_layout.addWidget(keep_first_btn)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_layout.addWidget(spacer)
        
        cancel_btn = QPushButton("取消")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)
        
        delete_btn = QPushButton("删除选中")
        delete_btn.setStyleSheet("background-color: #e74c3c; color: white;")
        delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(delete_btn)
        
        layout.addLayout(button_layout)

    def get_file_info(self, path: str) -> str:
        try:
            size = os.path.getsize(path)
            size_str = self.format_size(size)
            
            mtime = os.path.getmtime(path)
            mtime_str = datetime.fromtimestamp(mtime).strftime("%Y-%m-%d %H:%M:%S")
            
            ext = os.path.splitext(path)[1].upper()
            filename = os.path.basename(path)
            
            return f"<b>文件名:</b> {filename}<br>" \
                   f"<b>大小:</b> {size_str}<br>" \
                   f"<b>格式:</b> {ext}<br>" \
                   f"<b>修改时间:</b> {mtime_str}<br>" \
                   f"<b>路径:</b> {path}"
        except Exception:
            return f"<b>文件名:</b> {os.path.basename(path)}<br><b>路径:</b> {path}"

    def format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"

    def toggle_path(self, path: str, state: int):
        if state == Qt.Checked:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)

    def select_all(self):
        for md5_hash, paths in self.groups:
            for i, path in enumerate(paths):
                if i > 0:
                    self.selected_paths.add(path)
        self.update_checkboxes()

    def deselect_all(self):
        self.selected_paths.clear()
        self.update_checkboxes()

    def keep_first_only(self):
        self.selected_paths.clear()
        for md5_hash, paths in self.groups:
            for i, path in enumerate(paths):
                if i > 0:
                    self.selected_paths.add(path)
        self.update_checkboxes()

    def update_checkboxes(self):
        for path, checkbox in self.checkbox_map.items():
            checkbox.setChecked(path in self.selected_paths)

    def delete_selected(self):
        debug_manager.log_info('删除选中的重复图片', 'duplicate', selected_count=len(self.selected_paths))
        if not self.selected_paths:
            debug_manager.log_warning('没有选中任何图片', 'duplicate')
            QMessageBox.warning(self, "警告", "请选择要删除的图片")
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"将删除 {len(self.selected_paths)} 张图片，是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            success_count = 0
            failed_paths = []
            deleted_paths = []
            debug_manager.log_info('用户确认删除', 'duplicate', count=len(self.selected_paths))
            
            for path in list(self.selected_paths):
                try:
                    os.remove(path)
                    success_count += 1
                    deleted_paths.append(path)
                    debug_manager.log_info('图片删除成功', 'duplicate', path=path)
                except Exception as e:
                    failed_paths.append(f"{path}: {e}")
                    debug_manager.log_exception(e, 'duplicate', path=path)
            
            if self.parent() and hasattr(self.parent(), 'classifier'):
                for md5_hash, paths in self.groups:
                    group_deleted = [p for p in paths if p in deleted_paths]
                    if group_deleted:
                        self.parent().classifier.add_processed_duplicate(md5_hash, group_deleted)
            
            if success_count > 0:
                debug_manager.log_info('重复图片删除完成', 'duplicate', success_count=success_count)
                QMessageBox.information(self, "成功", f"已删除 {success_count} 张图片")
            
            if failed_paths:
                debug_manager.log_warning('部分图片删除失败', 'duplicate', failed_count=len(failed_paths))
                QMessageBox.warning(self, "警告", f"以下图片删除失败:\n{chr(10).join(failed_paths)}")
            
            self.accept()