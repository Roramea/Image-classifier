import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QPushButton, QCheckBox, QWidget, QMessageBox,
    QSizePolicy, QScrollArea
)
from PyQt5.QtGui import QPixmap, QFont
from PyQt5.QtCore import Qt, QSize

from core.debug_manager import debug_manager
from core.utils import format_size, smart_sort_duplicate_paths, get_copy_score
from .themed_dialog import ThemedDialog


class DuplicateDetailDialog(ThemedDialog):
    """重复图片详情对话框。

    职责：展示重复图片组、让用户选择要删除的图片、返回用户的选择。
    不执行实际文件删除（由 Presenter 委托 DuplicateService 处理），
    不访问父组件的核心服务（避免反向耦合）。

    通过 get_deletion_result() 获取用户确认删除的列表。
    """

    def __init__(self, paths_list: list, parent=None, md5_hashes=None):
        super().__init__(parent)
        self.setWindowTitle("重复图片详情")
        # 移除标题栏右侧默认的问号帮助按钮（未填充实际功能）
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowContextHelpButtonHint)
        self.setGeometry(100, 100, 1000, 800)

        self.groups = []
        # 用户确认删除的列表：[(md5_hash, [selected_paths]), ...]
        # 仅在对话框 accept 后填充，由 Presenter 读取并委托 service 执行
        self._pending_deletions: list = []

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
        self._group_frames = []
        self._group_labels = []
        self._img_labels = []
        self._info_texts = []

        self.init_ui()
        self._apply_theme()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        total_images = sum(len(paths) for _, paths in self.groups)
        self.info_label = QLabel(f"共发现 {len(self.groups)} 组重复图片，总计 {total_images} 张")
        self.info_label.setFont(QFont("Arial", 12, QFont.Bold))
        layout.addWidget(self.info_label)
        
        scroll_area = QWidget()
        scroll_layout = QVBoxLayout(scroll_area)
        
        for group_idx, (md5_hash, paths) in enumerate(self.groups):
            sorted_paths = smart_sort_duplicate_paths(paths)
            group_frame = QWidget()
            self._group_frames.append(group_frame)
            group_layout = QVBoxLayout(group_frame)
            group_layout.setContentsMargins(10, 10, 10, 10)
            
            group_label = QLabel(f"重复组 {group_idx + 1}（{len(sorted_paths)}张图片）")
            group_label.setFont(QFont("Arial", 10, QFont.Bold))
            self._group_labels.append(group_label)
            group_layout.addWidget(group_label)
            
            grid_layout = QGridLayout()
            
            for i, path in enumerate(sorted_paths):
                row = i // 2
                col = i % 2
                
                img_widget = QWidget()
                img_layout = QVBoxLayout(img_widget)
                
                copy_score = get_copy_score(path)
                is_copy = copy_score > 0
                if i == 0:
                    checkbox = QCheckBox(f"图片 {i + 1}（推荐保留）")
                elif is_copy:
                    checkbox = QCheckBox(f"图片 {i + 1}（疑似副本）")
                else:
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
                        self._img_labels.append(img_label)
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
                    self._info_texts.append(info_text)
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
        
        self.select_all_btn = QPushButton("全选")
        self.select_all_btn.clicked.connect(self.select_all)
        button_layout.addWidget(self.select_all_btn)
        
        self.deselect_all_btn = QPushButton("取消全选")
        self.deselect_all_btn.clicked.connect(self.deselect_all)
        button_layout.addWidget(self.deselect_all_btn)
        
        self.keep_first_btn = QPushButton("只保留第一张")
        self.keep_first_btn.clicked.connect(self.keep_first_only)
        button_layout.addWidget(self.keep_first_btn)
        
        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        button_layout.addWidget(spacer)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        self.delete_btn = QPushButton("删除选中")
        self.delete_btn.clicked.connect(self.delete_selected)
        button_layout.addWidget(self.delete_btn)
        
        layout.addLayout(button_layout)
    
    def _apply_theme(self):
        c = self._get_colors()
        self.setStyleSheet(self._create_dialog_base_style())
        self.info_label.setStyleSheet(f"color: {c.danger};")
        for frame in self._group_frames:
            frame.setStyleSheet(f"border: 1px solid {c.border}; border-radius: 5px; margin-bottom: 10px;")
        for label in self._group_labels:
            label.setStyleSheet(f"color: {c.accent};")
        for img_label in self._img_labels:
            img_label.setStyleSheet(f"background-color: {c.image_bg};")
        for info_text in self._info_texts:
            info_text.setStyleSheet(f"color: {c.text_hint};")
        self.delete_btn.setStyleSheet(f"background-color: {c.danger}; color: white; border: none;")

    def get_file_info(self, path: str) -> str:
        try:
            size = os.path.getsize(path)
            size_str = format_size(size)
            
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

    def toggle_path(self, path: str, state: int):
        if state == Qt.Checked:
            self.selected_paths.add(path)
        else:
            self.selected_paths.discard(path)

    def select_all(self):
        for md5_hash, paths in self.groups:
            sorted_paths = smart_sort_duplicate_paths(paths)
            for i, path in enumerate(sorted_paths):
                if i > 0:
                    self.selected_paths.add(path)
        self.update_checkboxes()

    def deselect_all(self):
        self.selected_paths.clear()
        self.update_checkboxes()

    def keep_first_only(self):
        self.selected_paths.clear()
        for md5_hash, paths in self.groups:
            sorted_paths = smart_sort_duplicate_paths(paths)
            for i, path in enumerate(sorted_paths):
                if i > 0:
                    self.selected_paths.add(path)
        self.update_checkboxes()

    def update_checkboxes(self):
        for path, checkbox in self.checkbox_map.items():
            checkbox.setChecked(path in self.selected_paths)

    def delete_selected(self):
        """收集用户选中的删除项，确认后关闭对话框。

        仅整理选中路径到 _pending_deletions，不执行实际文件删除。
        实际删除由 Presenter 通过 DuplicateService.delete_selected_duplicates 执行，
        以保证文件删除、记忆保存、状态更新的一致性。
        """
        debug_manager.log_info('收集选中的重复图片', 'duplicate', selected_count=len(self.selected_paths))
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
            # 按 md5 分组整理选中路径，供 Presenter 调用 service 使用
            for md5_hash, paths in self.groups:
                group_selected = [p for p in paths if p in self.selected_paths]
                if group_selected:
                    self._pending_deletions.append((md5_hash, group_selected))
            debug_manager.log_info('用户确认删除，关闭对话框', 'duplicate', group_count=len(self._pending_deletions))
            self.accept()

    def get_deletion_result(self) -> list:
        """返回用户确认删除的列表。

        Returns:
            [(md5_hash, [selected_paths]), ...]，仅在对框 accept 后有值；
            未确认或取消时返回空列表。
        """
        return self._pending_deletions