import os
import sys
from datetime import datetime
from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QProgressBar,
    QMessageBox, QInputDialog, QListWidget, QListWidgetItem,
    QScrollArea, QSplitter, QGroupBox, QDialog, QCheckBox,
    QGridLayout, QComboBox, QSizePolicy
)
from PyQt5.QtGui import QPixmap, QKeySequence, QFont
from PyQt5.QtCore import Qt, QThread, pyqtSignal, QSize

from image_scanner import ImageScanner
from classification_manager import ClassificationManager


class ScanThread(QThread):
    progress_updated = pyqtSignal(int, int)
    scanning_finished = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        self.scanner = ImageScanner()

    def run(self):
        try:
            count = self.scanner.scan_folder(self.folder_path)
            self.progress_updated.emit(count, count)
            self.scanning_finished.emit(self.scanner.image_paths)
        except Exception as e:
            self.error_occurred.emit(str(e))


class HashThread(QThread):
    progress_updated = pyqtSignal(int, int)
    hash_finished = pyqtSignal(list, dict)
    error_occurred = pyqtSignal(str)

    def __init__(self, image_paths: list):
        super().__init__()
        self.image_paths = image_paths
        self.scanner = ImageScanner()
        self.scanner.image_paths = image_paths

    def run(self):
        try:
            total = len(self.image_paths)
            self.progress_updated.emit(0, total)
            
            duplicates = self.scanner.find_duplicates()
            self.progress_updated.emit(total // 2, total)
            
            groups = self.scanner.group_similar_images(threshold=10)
            self.progress_updated.emit(total, total)
            
            self.hash_finished.emit(groups, duplicates)
        except Exception as e:
            self.error_occurred.emit(str(e))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分类器")
        self.setGeometry(100, 100, 1200, 800)

        self.scanner = ImageScanner()
        self.classifier = ClassificationManager()
        
        self.current_group_index = 0
        self.current_image_index = 0
        self.groups = []
        self.duplicates = {}
        self.processed_images = set()
        
        self.hash_scanning = False
        self.hash_completed = False
        
        self.init_ui()
        self.classifier.load_config()
        self.load_shortcuts()
        
        self.check_unfinished_session()
        
        if self.classifier.last_folder:
            self.status_label.setText(f"上次分类: {os.path.basename(self.classifier.last_folder)}")
        else:
            self.status_label.setText("请选择图片文件夹开始分类")

    def init_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        
        select_btn = QPushButton("选择图片文件夹")
        select_btn.clicked.connect(self.select_folder)
        left_layout.addWidget(select_btn)

        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("最近分类的文件夹")
        self.recent_combo.setMaximumWidth(280)
        self.recent_combo.currentIndexChanged.connect(self.on_recent_folder_selected)
        left_layout.addWidget(self.recent_combo)
        self.update_recent_folders()

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        left_layout.addWidget(self.progress_bar)

        self.status_label = QLabel("请选择图片文件夹开始分类")
        left_layout.addWidget(self.status_label)

        self.shortcut_group = QGroupBox("分类快捷键")
        shortcut_layout = QVBoxLayout(self.shortcut_group)
        
        self.shortcut_list = QListWidget()
        shortcut_layout.addWidget(self.shortcut_list)

        add_shortcut_btn = QPushButton("添加快捷键")
        add_shortcut_btn.clicked.connect(self.add_shortcut)
        shortcut_layout.addWidget(add_shortcut_btn)

        remove_shortcut_btn = QPushButton("删除快捷键")
        remove_shortcut_btn.clicked.connect(self.remove_shortcut)
        shortcut_layout.addWidget(remove_shortcut_btn)

        left_layout.addWidget(self.shortcut_group)

        self.duplicate_group = QGroupBox("重复图片")
        duplicate_layout = QVBoxLayout(self.duplicate_group)
        self.duplicate_group.setVisible(False)
        
        self.duplicate_list = QListWidget()
        duplicate_layout.addWidget(self.duplicate_list)
        
        duplicate_btn_layout = QHBoxLayout()
        
        view_detail_btn = QPushButton("查看详情")
        view_detail_btn.clicked.connect(self.show_duplicate_detail)
        duplicate_btn_layout.addWidget(view_detail_btn)
        
        delete_duplicate_btn = QPushButton("删除选中重复图片")
        delete_duplicate_btn.clicked.connect(self.delete_selected_duplicates)
        duplicate_btn_layout.addWidget(delete_duplicate_btn)
        
        duplicate_layout.addLayout(duplicate_btn_layout)

        left_layout.addWidget(self.duplicate_group)
        
        clear_storage_btn = QPushButton("清除存储占用")
        clear_storage_btn.clicked.connect(self.clear_storage)
        clear_storage_btn.setStyleSheet("color: #c0392b;")
        left_layout.addWidget(clear_storage_btn)
        
        left_layout.addStretch()

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)

        image_container = QWidget()
        image_layout = QHBoxLayout(image_container)
        
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignCenter)
        
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("background-color: #2a2a2a;")
        self.scroll_area.setWidget(self.image_label)
        
        image_layout.addWidget(self.scroll_area)
        right_layout.addWidget(image_container)

        info_layout = QHBoxLayout()
        
        self.group_info = QLabel("组: 0/0")
        info_layout.addWidget(self.group_info)
        
        self.image_info = QLabel("图片: 0/0")
        info_layout.addWidget(self.image_info)
        
        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        info_layout.addWidget(self.path_label)
        
        right_layout.addLayout(info_layout)

        nav_layout = QHBoxLayout()
        
        prev_group_btn = QPushButton("上一组")
        prev_group_btn.clicked.connect(self.prev_group)
        nav_layout.addWidget(prev_group_btn)
        
        prev_img_btn = QPushButton("上一张")
        prev_img_btn.clicked.connect(self.prev_image)
        nav_layout.addWidget(prev_img_btn)
        
        next_img_btn = QPushButton("下一张")
        next_img_btn.clicked.connect(self.next_image)
        nav_layout.addWidget(next_img_btn)
        
        next_group_btn = QPushButton("下一组")
        next_group_btn.clicked.connect(self.next_group)
        nav_layout.addWidget(next_group_btn)
        
        right_layout.addLayout(nav_layout)

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])
        
        main_layout.addWidget(splitter)

    def load_shortcuts(self):
        self.shortcut_list.clear()
        shortcuts = self.classifier.get_all_shortcuts()
        for key, path in shortcuts.items():
            item = QListWidgetItem(f"{key} -> {os.path.basename(path)}")
            item.setData(Qt.UserRole, key)
            self.shortcut_list.addItem(item)

    def update_recent_folders(self):
        self.recent_combo.clear()
        self.recent_combo.addItem("选择最近的文件夹", "")
        
        recent_folders = self.classifier.get_recent_folders()
        for folder in recent_folders:
            folder_name = os.path.basename(folder)
            if not folder_name:
                folder_name = folder
            self.recent_combo.addItem(folder_name, folder)
    
    def on_recent_folder_selected(self, index: int):
        if index == 0:
            return
        
        folder_path = self.recent_combo.itemData(index)
        if folder_path and os.path.exists(folder_path):
            self.status_label.setText("正在扫描图片...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            self.scan_thread = ScanThread(folder_path)
            self.scan_thread.progress_updated.connect(self.update_scan_progress)
            self.scan_thread.scanning_finished.connect(self.on_scan_finished)
            self.scan_thread.error_occurred.connect(self.on_scan_error)
            self.scan_thread.start()
        elif folder_path:
            QMessageBox.warning(self, "警告", f"文件夹不存在: {folder_path}")
            self.update_recent_folders()

    def check_unfinished_session(self):
        session = self.classifier.get_unfinished_session()
        if not session:
            return
        
        folder_path = session.get('folder_path', "")
        total_count = session.get('total_count', 0)
        processed_count = session.get('processed_count', 0)
        
        if total_count == 0:
            return
        
        remaining = total_count - processed_count
        
        reply = QMessageBox.question(
            self,
            "未完成的分类",
            f"检测到上次分类未完成！\n\n"
            f"文件夹: {os.path.basename(folder_path)}\n"
            f"已完成: {processed_count}/{total_count} ({processed_count/total_count*100:.0f}%)\n"
            f"剩余: {remaining} 张图片\n\n"
            f"是否继续上次的分类？",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.Yes
        )
        
        if reply == QMessageBox.Yes:
            self.status_label.setText("正在扫描图片...")
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            self.scan_thread = ScanThread(folder_path)
            self.scan_thread.progress_updated.connect(self.update_scan_progress)
            self.scan_thread.scanning_finished.connect(self.on_scan_finished)
            self.scan_thread.error_occurred.connect(self.on_scan_error)
            self.scan_thread.start()
        else:
            self.classifier.clear_unfinished_session()

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder_path:
            return

        self.status_label.setText("正在扫描图片...")
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)

        self.scan_thread = ScanThread(folder_path)
        self.scan_thread.progress_updated.connect(self.update_scan_progress)
        self.scan_thread.scanning_finished.connect(self.on_scan_finished)
        self.scan_thread.error_occurred.connect(self.on_scan_error)
        self.scan_thread.start()

    def update_scan_progress(self, current: int, total: int):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)
        self.status_label.setText(f"正在扫描: {current}/{total}")

    def on_scan_finished(self, image_paths: list):
        self.groups = [[path] for path in image_paths]
        self.current_group_index = 0
        self.current_image_index = 0
        self.processed_images = set()
        self.duplicates = {}
        
        self.progress_bar.setVisible(False)
        
        folder_path = self.scan_thread.folder_path
        self.classifier.load_config(folder_path)
        self.classifier.load_duplicate_memory()
        self.load_shortcuts()
        self.update_recent_folders()
        
        if not image_paths:
            self.status_label.setText("未找到图片")
            return

        self.status_label.setText(f"扫描完成，共 {len(image_paths)} 张图片")
        self.show_current_image()
        
        self.hash_scanning = True
        self.hash_completed = False
        
        self.hash_thread = HashThread(image_paths)
        self.hash_thread.progress_updated.connect(self.update_hash_progress)
        self.hash_thread.hash_finished.connect(self.on_hash_finished)
        self.hash_thread.error_occurred.connect(self.on_hash_error)
        self.hash_thread.start()

    def update_hash_progress(self, current: int, total: int):
        self.status_label.setText(f"后台分析相似度: {current}/{total}")

    def on_hash_finished(self, groups: list, duplicates: dict):
        self.hash_scanning = False
        self.hash_completed = True
        self.groups = groups
        
        remaining_duplicates = {}
        for md5_hash, paths in duplicates.items():
            if not self.classifier.is_duplicate_processed(md5_hash):
                remaining_duplicates[md5_hash] = paths
        
        self.duplicates = remaining_duplicates
        
        self.show_current_image()
        self.update_duplicate_list()
        
        if remaining_duplicates:
            total_duplicates = sum(len(p) - 1 for p in remaining_duplicates.values())
            processed_count = len(duplicates) - len(remaining_duplicates)
            if processed_count > 0:
                self.status_label.setText(f"分析完成: {len(groups)}组, {len(remaining_duplicates)}组重复({total_duplicates}张), {processed_count}组已处理")
            else:
                self.status_label.setText(f"分析完成: {len(groups)}组, {len(remaining_duplicates)}组重复({total_duplicates}张)")
        else:
            self.status_label.setText(f"分析完成，共 {len(groups)} 组")

    def on_hash_error(self, error: str):
        self.hash_scanning = False
        self.status_label.setText("相似度分析出错")
        QMessageBox.warning(self, "警告", f"后台分析时出错: {error}")

    def on_scan_error(self, error: str):
        self.progress_bar.setVisible(False)
        self.status_label.setText("扫描出错")
        QMessageBox.critical(self, "错误", f"扫描图片时出错: {error}")

    def show_current_image(self):
        if not self.groups or self.current_group_index >= len(self.groups):
            self.image_label.clear()
            self.group_info.setText("组: 0/0")
            self.image_info.setText("图片: 0/0")
            self.path_label.setText("")
            return

        current_group = self.groups[self.current_group_index]
        if self.current_image_index >= len(current_group):
            self.current_image_index = 0

        image_path = current_group[self.current_image_index]
        
        try:
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                max_size = QSize(800, 600)
                scaled_pixmap = pixmap.scaled(max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
            else:
                self.image_label.setText("无法加载图片")
        except Exception:
            self.image_label.setText("无法加载图片")

        self.group_info.setText(f"组: {self.current_group_index + 1}/{len(self.groups)}")
        self.image_info.setText(f"图片: {self.current_image_index + 1}/{len(current_group)}")
        self.path_label.setText(image_path)

    def update_duplicate_list(self):
        self.duplicate_list.clear()
        if self.duplicates:
            self.duplicate_group.setVisible(True)
            for md5, paths in self.duplicates.items():
                item = QListWidgetItem(f"重复 ({len(paths)}张): {os.path.basename(paths[0])}")
                item.setData(Qt.UserRole, (md5, paths))
                self.duplicate_list.addItem(item)
        else:
            self.duplicate_group.setVisible(False)

    def add_shortcut(self):
        key, ok = QInputDialog.getText(self, "添加快捷键", "请输入快捷键（单个字母或数字）:")
        if not ok or not key:
            return

        key = key.strip().lower()
        if len(key) != 1 or not key.isalnum():
            QMessageBox.warning(self, "警告", "快捷键只能是单个字母或数字")
            return

        if key in self.classifier.get_all_shortcuts():
            QMessageBox.warning(self, "警告", "该快捷键已被使用")
            return

        folder_path = QFileDialog.getExistingDirectory(self, "选择目标文件夹")
        if not folder_path:
            return

        if not self.classifier.add_shortcut(key, folder_path):
            QMessageBox.warning(self, "警告", "添加快捷键失败")
            return

        self.load_shortcuts()
        QMessageBox.information(self, "成功", f"已将快捷键 '{key}' 绑定到文件夹")

    def remove_shortcut(self):
        selected_items = self.shortcut_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要删除的快捷键")
            return

        key = selected_items[0].data(Qt.UserRole)
        if self.classifier.remove_shortcut(key):
            self.load_shortcuts()
            QMessageBox.information(self, "成功", "快捷键已删除")
        else:
            QMessageBox.warning(self, "警告", "删除快捷键失败")

    def delete_selected_duplicates(self):
        selected_items = self.duplicate_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "警告", "请选择要处理的重复图片组")
            return

        data = selected_items[0].data(Qt.UserRole)
        if not data or len(data) != 2:
            return
        
        md5_hash, paths = data
        if not paths or len(paths) <= 1:
            return

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"该组有 {len(paths)} 张完全相同的图片，\n"
            f"将保留第一张，删除其余 {len(paths) - 1} 张，\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            deleted_paths = []
            for path in paths[1:]:
                try:
                    os.remove(path)
                    deleted_paths.append(path)
                    if path in self.processed_images:
                        self.processed_images.remove(path)
                except Exception as e:
                    QMessageBox.warning(self, "警告", f"删除 {path} 失败: {e}")
            
            self.classifier.add_processed_duplicate(md5_hash, deleted_paths)
            
            del self.duplicates[md5_hash]
            self.update_duplicate_list()
            self.refresh_groups()
            
            if not self.duplicates:
                self.status_label.setText("所有重复图片已处理完成")
                self.classifier.clear_duplicate_memory()

    def clear_storage(self):
        dialog = StorageCleanDialog(self)
        result = dialog.exec_()
        
        if result == QDialog.Accepted:
            self.load_shortcuts()
            self.update_recent_folders()
            self.status_label.setText("存储已清除")

    def refresh_groups(self):
        valid_groups = []
        for group in self.groups:
            valid_paths = [p for p in group if os.path.exists(p)]
            if valid_paths:
                valid_groups.append(valid_paths)
        self.groups = valid_groups
        
        if self.current_group_index >= len(self.groups):
            self.current_group_index = max(0, len(self.groups) - 1)
        
        if not self.groups and self.processed_images:
            self.classifier.clear_unfinished_session()
            self.status_label.setText("分类完成！")
        
        self.show_current_image()

    def classify_current_group(self, shortcut: str):
        if not self.groups:
            self.status_label.setText("没有可分类的图片")
            return
        
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
            if not self.groups:
                self.status_label.setText("没有可分类的图片")
                return
        
        current_group = self.groups[self.current_group_index]
        
        success_count = 0
        failed_paths = []
        
        for path in current_group:
            if self.classifier.classify_image(path, shortcut):
                success_count += 1
                self.processed_images.add(path)
            else:
                failed_paths.append(path)
        
        self.refresh_groups()
        
        folder_name = os.path.basename(self.classifier.get_folder(shortcut))
        if success_count > 0 and not failed_paths:
            self.status_label.setText(f"已将 {success_count} 张图片分类到 '{folder_name}'")
        elif success_count > 0 and failed_paths:
            self.status_label.setText(f"分类完成: {success_count}成功, {len(failed_paths)}失败")
        elif failed_paths:
            self.status_label.setText(f"分类失败: {len(failed_paths)}张图片")

    def closeEvent(self, event):
        if self.groups and self.classifier.current_folder:
            total_count = sum(len(g) for g in self.groups) + len(self.processed_images)
            processed_count = len(self.processed_images)
            
            if total_count > 0 and processed_count < total_count:
                session_data = {
                    'folder_path': self.classifier.current_folder,
                    'total_count': total_count,
                    'processed_count': processed_count,
                    'timestamp': datetime.now().isoformat()
                }
                self.classifier.save_unfinished_session(session_data)
            else:
                self.classifier.clear_unfinished_session()
        
        event.accept()

    def keyPressEvent(self, event):
        key = event.key()
        
        if key == Qt.Key_Left:
            self.prev_image()
        elif key == Qt.Key_Right:
            self.next_image()
        elif key == Qt.Key_Up:
            self.prev_group()
        elif key == Qt.Key_Down:
            self.next_group()
        else:
            key_str = chr(key).lower()
            if key_str in self.classifier.get_all_shortcuts():
                self.classify_current_group(key_str)
            else:
                super().keyPressEvent(event)

    def prev_image(self):
        if not self.groups:
            return
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        current_group = self.groups[self.current_group_index]
        self.current_image_index = (self.current_image_index - 1) % len(current_group)
        self.show_current_image()

    def next_image(self):
        if not self.groups:
            return
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        current_group = self.groups[self.current_group_index]
        self.current_image_index = (self.current_image_index + 1) % len(current_group)
        self.show_current_image()

    def prev_group(self):
        if not self.groups:
            return
        self.current_group_index = (self.current_group_index - 1) % len(self.groups)
        self.current_image_index = 0
        self.show_current_image()

    def next_group(self):
        if not self.groups:
            return
        self.current_group_index = (self.current_group_index + 1) % len(self.groups)
        self.current_image_index = 0
        self.show_current_image()

    def show_duplicate_detail(self):
        if not self.duplicates:
            QMessageBox.information(self, "提示", "暂无重复图片")
            return

        valid_groups = [(md5, paths) for md5, paths in self.duplicates.items() if paths and len(paths) > 1]
        if not valid_groups:
            QMessageBox.information(self, "提示", "暂无重复图片")
            return

        selected_items = self.duplicate_list.selectedItems()
        
        md5_hash, paths = None, None
        if selected_items:
            data = selected_items[0].data(Qt.UserRole)
            if data and len(data) == 2:
                md5_hash, paths = data
        
        if not paths or len(paths) <= 1:
            md5_hash, paths = valid_groups[0]

        try:
            detail_dialog = DuplicateDetailDialog(paths, self, md5_hash)
            result = detail_dialog.exec_()
            
            if result == QDialog.Accepted:
                if md5_hash and md5_hash in self.duplicates:
                    del self.duplicates[md5_hash]
                self.update_duplicate_list()
                self.refresh_groups()
                
                if not self.duplicates:
                    self.status_label.setText("所有重复图片已处理完成")
                    self.classifier.clear_duplicate_memory()
        except Exception as e:
            QMessageBox.critical(self, "错误", f"打开详情窗口失败: {str(e)}")


class DuplicateDetailDialog(QDialog):
    def __init__(self, paths: list, parent=None, md5_hash=None):
        super().__init__(parent)
        self.setWindowTitle("重复图片详情")
        self.setGeometry(100, 100, 900, 700)
        
        self.md5_hash = md5_hash
        self.paths = [p for p in paths if p and os.path.exists(p)]
        if len(self.paths) <= 1:
            QMessageBox.warning(self, "警告", "没有足够的重复图片")
            self.reject()
            return
        
        self.selected_paths = set(self.paths[1:])
        self.checkbox_map = {}
        
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout(self)
        
        info_label = QLabel(f"共发现 {len(self.paths)} 张完全相同的图片（MD5哈希值相同）")
        info_label.setFont(QFont("Arial", 12, QFont.Bold))
        info_label.setStyleSheet("color: #c0392b;")
        layout.addWidget(info_label)
        
        grid_layout = QGridLayout()
        
        for i, path in enumerate(self.paths):
            row = i // 2
            col = i % 2
            
            img_widget = QWidget()
            img_layout = QVBoxLayout(img_widget)
            
            checkbox = QCheckBox(f"图片 {i + 1}")
            checkbox.setChecked(i > 0)
            self.checkbox_map[path] = checkbox
            checkbox.stateChanged.connect(lambda state, p=path: self.toggle_path(p, state))
            img_layout.addWidget(checkbox)
            
            try:
                pixmap = QPixmap(path)
                if not pixmap.isNull():
                    scaled_pixmap = pixmap.scaled(QSize(350, 250), Qt.KeepAspectRatio, Qt.SmoothTransformation)
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
                info_text.setFont(QFont("Arial", 9))
                info_text.setStyleSheet("color: #7f8c8d;")
                img_layout.addWidget(info_text)
            except Exception:
                img_layout.addWidget(QLabel(f"文件名: {os.path.basename(path)}"))
            
            grid_layout.addWidget(img_widget, row, col)
        
        layout.addLayout(grid_layout)
        
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
        self.selected_paths = set(self.paths[1:])
        self.update_checkboxes()

    def deselect_all(self):
        self.selected_paths.clear()
        self.update_checkboxes()

    def keep_first_only(self):
        self.selected_paths = set(self.paths[1:])
        self.update_checkboxes()

    def update_checkboxes(self):
        for path, checkbox in self.checkbox_map.items():
            checkbox.setChecked(path in self.selected_paths)

    def delete_selected(self):
        if not self.selected_paths:
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
            
            for path in list(self.selected_paths):
                try:
                    os.remove(path)
                    success_count += 1
                    deleted_paths.append(path)
                except Exception as e:
                    failed_paths.append(f"{path}: {e}")
            
            if self.parent() and hasattr(self.parent(), 'classifier') and self.md5_hash:
                self.parent().classifier.add_processed_duplicate(self.md5_hash, deleted_paths)
            
            if success_count > 0:
                QMessageBox.information(self, "成功", f"已删除 {success_count} 张图片")
            
            if failed_paths:
                QMessageBox.warning(self, "警告", f"以下图片删除失败:\n{chr(10).join(failed_paths)}")
            
            self.accept()


class StorageCleanDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("清除存储占用")
        self.setGeometry(200, 200, 500, 450)
        
        self.selected_categories = []
        self.checkboxes = {}
        
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
        if not self.selected_categories:
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
            self.parent().classifier.clear_categories(self.selected_categories)
            QMessageBox.information(self, "成功", "存储已清除")
            self.accept()