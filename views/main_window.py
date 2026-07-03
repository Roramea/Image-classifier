import os
from datetime import datetime

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QFileDialog, QProgressBar,
    QMessageBox, QListWidget, QListWidgetItem,
    QScrollArea, QSplitter, QGroupBox, QDialog, QComboBox,
    QSlider, QShortcut, QTableWidget, QTableWidgetItem, QCheckBox,
    QSizePolicy
)
from PyQt5.QtGui import QPixmap, QFont, QTransform, QKeySequence, QColor
from PyQt5.QtCore import Qt, QSize

from core.scan_thread import ScanThread
from core.classification_manager import ClassificationManager
from services.duplicate_service import DuplicateService
from services.classification_service import ClassificationService
from dialogs.duplicate_detail_dialog import DuplicateDetailDialog
from dialogs.storage_clean_dialog import StorageCleanDialog
from dialogs.folder_select_dialog import FolderSelectDialog
from dialogs.shortcut_input_dialog import ShortcutInputDialog
from dialogs.hash_analysis_dialog import HashAnalysisDialog
from core.debug_manager import debug_manager
from core.utils import key_to_string


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分类器")
        self.setGeometry(100, 100, 1200, 800)

        self._init_services()
        self._init_state()
        self.init_ui()
        self.connect_signals()
        self._load_initial_data()

        debug_manager.log_info('主窗口初始化完成', 'main')

    def _init_services(self):
        self.classifier = ClassificationManager()
        self.duplicate_service = DuplicateService(self.classifier)
        self.classification_service = ClassificationService(self.classifier)

    def _init_state(self):
        self.hash_scanning = False
        self.hash_completed = False
        self.hash_list = []
        self.group_rotations = {}
        debug_manager.log_info('初始化旋转状态', 'rotation', group_rotations_empty=True)

    def _load_initial_data(self):
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

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

        select_btn = QPushButton("选择图片文件夹")
        select_btn.clicked.connect(self.select_folder)
        layout.addWidget(select_btn)

        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("最近分类的文件夹")
        self.recent_combo.setMaximumWidth(280)
        self.recent_combo.currentIndexChanged.connect(self.on_recent_folder_selected)
        layout.addWidget(self.recent_combo)
        self.update_recent_folders()

        self.status_label = QLabel("请选择图片文件夹开始分类")
        layout.addWidget(self.status_label)

        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setVisible(False)
        self.threshold_group = threshold_group
        threshold_layout = QVBoxLayout(threshold_group)

        slider_layout = QHBoxLayout()
        slider_label = QLabel("阈值:")
        slider_layout.addWidget(slider_label)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(2)
        self.threshold_slider.setMaximum(25)
        self.threshold_slider.setValue(self.classifier.get_hash_threshold())
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        slider_layout.addWidget(self.threshold_slider)

        self.threshold_value_label = QLabel(str(self.classifier.get_hash_threshold()))
        self.threshold_value_label.setStyleSheet("color: #4a90d9; font-weight: bold; min-width: 30px; text-align: center;")
        slider_layout.addWidget(self.threshold_value_label)

        threshold_layout.addLayout(slider_layout)

        hint_label = QLabel("阈值越小，相似度要求越高（2-25）")
        hint_label.setFont(QFont("Microsoft YaHei", 9))
        hint_label.setStyleSheet("color: #999999;")
        hint_label.setAlignment(Qt.AlignCenter)
        threshold_layout.addWidget(hint_label)

        layout.addWidget(threshold_group)

        layout.addWidget(self._create_shortcut_group())
        layout.addWidget(self._create_duplicate_group())

        clear_storage_btn = QPushButton("清除存储占用")
        clear_storage_btn.clicked.connect(self.clear_storage)
        clear_storage_btn.setStyleSheet("color: #c0392b;")
        layout.addWidget(clear_storage_btn)

        layout.addStretch()
        return panel

    def _create_shortcut_group(self):
        group = QGroupBox("分类快捷键")
        layout = QVBoxLayout(group)

        self.shortcut_list = QListWidget()
        layout.addWidget(self.shortcut_list)

        add_btn = QPushButton("添加快捷键")
        add_btn.clicked.connect(self.add_shortcut)
        layout.addWidget(add_btn)

        remove_btn = QPushButton("删除快捷键")
        remove_btn.clicked.connect(self.remove_shortcut)
        layout.addWidget(remove_btn)

        return group

    def _create_duplicate_group(self):
        group = QGroupBox("重复图片")
        group.setVisible(True)
        self.duplicate_group = group
        layout = QVBoxLayout(group)
        layout.setSpacing(8)
        layout.setContentsMargins(5, 5, 5, 5)

        self.duplicate_table = QTableWidget()
        self.duplicate_table.setColumnCount(2)
        self.duplicate_table.horizontalHeader().setVisible(False)
        self.duplicate_table.verticalHeader().setVisible(False)
        self.duplicate_table.setShowGrid(False)
        self.duplicate_table.setSelectionMode(QTableWidget.NoSelection)
        self.duplicate_table.setAlternatingRowColors(True)
        self.duplicate_table.setStyleSheet("""
            QTableWidget {
                background-color: #2d2d2d;
                alternate-background-color: #353535;
                border: none;
            }
            QTableWidget::item {
                padding: 6px;
                color: #ffffff;
                border: none;
            }
        """)
        self.duplicate_table.cellClicked.connect(self.on_duplicate_table_click)
        layout.addWidget(self.duplicate_table)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_duplicates)
        btn_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消全选")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselect_all_duplicates)
        btn_layout.addWidget(deselect_all_btn)

        spacer = QWidget()
        spacer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        btn_layout.addWidget(spacer)

        view_btn = QPushButton("查看详情")
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        view_btn.clicked.connect(self.show_duplicate_detail)
        btn_layout.addWidget(view_btn)

        delete_btn = QPushButton("删除选中")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                color: white;
                border: none;
                padding: 6px 12px;
                border-radius: 3px;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_duplicates)
        btn_layout.addWidget(delete_btn)

        layout.addLayout(btn_layout)
        return group

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)

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
        layout.addWidget(image_container)

        info_layout = QHBoxLayout()
        self.group_info = QLabel("组: 0/0")
        info_layout.addWidget(self.group_info)

        self.image_info = QLabel("图片: 0/0")
        info_layout.addWidget(self.image_info)

        self.path_label = QLabel("")
        self.path_label.setWordWrap(True)
        info_layout.addWidget(self.path_label)

        layout.addLayout(info_layout)
        layout.addLayout(self._create_navigation_layout())

        return panel

    def _create_navigation_layout(self):
        layout = QVBoxLayout()

        view_layout = QHBoxLayout()
        rotate_180_ccw_btn = QPushButton("↻ 180°逆 (Ctrl+↑)")
        rotate_180_ccw_btn.clicked.connect(lambda: self.rotate_image(False, 180))
        view_layout.addWidget(rotate_180_ccw_btn)

        rotate_ccw_btn = QPushButton("↻ 90°逆 (Ctrl+←)")
        rotate_ccw_btn.clicked.connect(lambda: self.rotate_image(False))
        view_layout.addWidget(rotate_ccw_btn)

        rotate_cw_btn = QPushButton("↺ 90°顺 (Ctrl+→)")
        rotate_cw_btn.clicked.connect(lambda: self.rotate_image(True))
        view_layout.addWidget(rotate_cw_btn)

        rotate_180_cw_btn = QPushButton("↺ 180°顺 (Ctrl+↓)")
        rotate_180_cw_btn.clicked.connect(lambda: self.rotate_image(True, 180))
        view_layout.addWidget(rotate_180_cw_btn)
        layout.addLayout(view_layout)

        switch_layout = QHBoxLayout()
        prev_group_btn = QPushButton("上一组 (↑)")
        prev_group_btn.setShortcut("Up")
        prev_group_btn.clicked.connect(self.prev_group)
        switch_layout.addWidget(prev_group_btn)

        prev_img_btn = QPushButton("上一张 (←)")
        prev_img_btn.setShortcut("Left")
        prev_img_btn.clicked.connect(self.prev_image)
        switch_layout.addWidget(prev_img_btn)

        next_img_btn = QPushButton("下一张 (→)")
        next_img_btn.setShortcut("Right")
        next_img_btn.clicked.connect(self.next_image)
        switch_layout.addWidget(next_img_btn)

        next_group_btn = QPushButton("下一组 (↓)")
        next_group_btn.setShortcut("Down")
        next_group_btn.clicked.connect(self.next_group)
        switch_layout.addWidget(next_group_btn)
        layout.addLayout(switch_layout)

        return layout

    def connect_signals(self):
        self.classification_service.classification_progress.connect(self.on_classification_progress)
        self.classification_service.classification_complete.connect(self.on_classification_complete)
        self.classification_service.image_moved.connect(self.on_image_moved)
        self.classification_service.group_changed.connect(self.on_group_changed)

        self.duplicate_service.duplicate_deleted.connect(self.on_duplicate_deleted)
        self.duplicate_service.duplicate_processing.connect(self.on_duplicate_processing)
        self.duplicate_service.duplicate_all_processed.connect(self.on_duplicate_all_processed)
        self.duplicate_service.duplicate_memory_cleared.connect(self.on_duplicate_memory_cleared)
        
        self.installEventFilter(self)
        self.centralWidget().installEventFilter(self)
        
        self.shortcut_rotate_ccw = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.shortcut_rotate_ccw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_ccw.activated.connect(lambda: self.rotate_image(False))
        debug_manager.log_info('注册快捷键 Ctrl+Left', 'keyboard', shortcut='rotate_image(False)', context='ApplicationShortcut')
        
        self.shortcut_rotate_cw = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.shortcut_rotate_cw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_cw.activated.connect(lambda: self.rotate_image(True))
        debug_manager.log_info('注册快捷键 Ctrl+Right', 'keyboard', shortcut='rotate_image(True)', context='ApplicationShortcut')
        
        self.shortcut_rotate_180_ccw = QShortcut(QKeySequence("Ctrl+Up"), self)
        self.shortcut_rotate_180_ccw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_180_ccw.activated.connect(lambda: self.rotate_image(False, 180))
        debug_manager.log_info('注册快捷键 Ctrl+Up', 'keyboard', shortcut='rotate_image(False, 180)', context='ApplicationShortcut')
        
        self.shortcut_rotate_180_cw = QShortcut(QKeySequence("Ctrl+Down"), self)
        self.shortcut_rotate_180_cw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_180_cw.activated.connect(lambda: self.rotate_image(True, 180))
        debug_manager.log_info('注册快捷键 Ctrl+Down', 'keyboard', shortcut='rotate_image(True, 180)', context='ApplicationShortcut')
    
    def eventFilter(self, obj, event):
        if event.type() == event.KeyPress:
            key = event.key()
            modifiers = event.modifiers()
            has_ctrl = bool(modifiers & Qt.ControlModifier)
            is_left = key == Qt.Key_Left
            is_right = key == Qt.Key_Right
            is_ctrl_key = key == Qt.Key_Control
            debug_manager.log_info('事件过滤器捕获键盘事件', 'keyboard', key=key, modifiers=modifiers, has_ctrl=has_ctrl, is_left=is_left, is_right=is_right, is_ctrl_key=is_ctrl_key, obj=type(obj).__name__)
            
            if is_ctrl_key:
                debug_manager.log_info('事件过滤器: 仅按下Ctrl键，不处理', 'keyboard')
                return False
                
            if has_ctrl:
                if is_left:
                    debug_manager.log_info('事件过滤器: Ctrl+Left -> 调用rotate_image(False)', 'keyboard')
                    self.rotate_image(False)
                    return True
                elif is_right:
                    debug_manager.log_info('事件过滤器: Ctrl+Right -> 调用rotate_image(True)', 'keyboard')
                    self.rotate_image(True)
                    return True
            else:
                debug_manager.log_info('事件过滤器: 无Ctrl修饰键，事件继续传递', 'keyboard')
        return super().eventFilter(obj, event)

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
            folder_name = os.path.basename(folder) or folder
            self.recent_combo.addItem(folder_name, folder)

    def on_recent_folder_selected(self, index: int):
        if index == 0:
            return

        folder_path = self.recent_combo.itemData(index)
        if folder_path and os.path.exists(folder_path):
            self._start_scanning(folder_path)
        elif folder_path:
            debug_manager.log_warning('最近文件夹不存在', 'folder', folder_path=folder_path)
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
            self._start_scanning(folder_path)
        else:
            self.classifier.clear_unfinished_session()

    def select_folder(self):
        folder_path = QFileDialog.getExistingDirectory(self, "选择图片文件夹")
        if not folder_path:
            debug_manager.log_info('用户取消选择文件夹', 'folder')
            return

        debug_manager.log_info('用户选择文件夹', 'folder', folder_path=folder_path)
        self._start_scanning(folder_path)

    def _start_scanning(self, folder_path: str):
        self.status_label.setText("正在扫描图片...")
        self.threshold_group.setVisible(False)
        self.hash_list = []

        self.scan_thread = ScanThread(folder_path)
        self.scan_thread.progress_updated.connect(self.update_scan_progress)
        self.scan_thread.scanning_finished.connect(self.on_scan_finished)
        self.scan_thread.error_occurred.connect(self.on_scan_error)
        self.scan_thread.start()

    def update_scan_progress(self, current: int, total: int):
        self.status_label.setText(f"正在扫描: {current}/{total}")

    def on_scan_finished(self, image_paths: list):
        debug_manager.log_info('扫描完成', 'scan', image_count=len(image_paths))

        folder_path = self.scan_thread.folder_path
        self._post_scan_setup(folder_path, image_paths)

        if not image_paths:
            self.status_label.setText("未找到图片")
            return

        self.show_current_image()
        self.status_label.setText(f"扫描完成，共 {len(image_paths)} 张图片")

        files_changed, changed_files = self.classifier.check_files_changed(image_paths)
        if files_changed:
            debug_manager.log_info('文件有变化，开始哈希分析', 'hash', changed_count=len(changed_files))
            self._start_hash_analysis(image_paths)
        else:
            debug_manager.log_info('文件无变化，跳过哈希分析', 'hash')
            self.hash_completed = True
            self._load_cached_hash_results(image_paths)

    def _post_scan_setup(self, folder_path: str, image_paths: list):
        self.classifier.load_config(folder_path)
        self.classifier.load_duplicate_memory()
        self.load_shortcuts()
        self.update_recent_folders()
        self.classification_service.set_groups([[path] for path in image_paths])
        self.group_rotations = {}
        debug_manager.log_info('新文件夹加载，重置组旋转状态', 'rotation')

    def _start_hash_analysis(self, image_paths: list):
        self.hash_scanning = True
        self.hash_completed = False

        threshold = self.classifier.get_hash_threshold()
        debug_manager.log_info('启动哈希分析对话框', 'hash', image_count=len(image_paths), threshold=threshold)
        
        cache = self.classifier.load_hash_cache()
        cached_file_hashes = cache.get('file_hashes', {})
        debug_manager.log_info('加载缓存文件哈希', 'hash', cached_count=len(cached_file_hashes))
        
        self.hash_dialog = HashAnalysisDialog(image_paths, threshold, self)
        self.hash_dialog.set_cached_hashes(cached_file_hashes)
        self.hash_dialog.progress_updated_signal.connect(self.on_hash_progress_update)
        self.hash_dialog.analysis_finished_signal.connect(self.on_hash_finished)
        self.hash_dialog.analysis_canceled_signal.connect(self.on_hash_canceled)
        self.hash_dialog.analysis_error_signal.connect(self.on_hash_error)
        self.hash_dialog.analysis_stage_changed_signal.connect(self.on_hash_stage_changed)
        self.hash_dialog.analysis_file_processed_signal.connect(self.on_hash_file_processed)
        self.hash_dialog.threshold_changed.connect(self.on_hash_threshold_changed)
        self.hash_dialog.show()

    def on_hash_progress_update(self, current: int, total: int, stage: str, filename: str, processed_count: int, stage_progress: int = 0):
        self.status_label.setText(f"后台分析相似度: {stage} ({current}/{total})")
    
    def on_hash_threshold_changed(self, threshold: int):
        debug_manager.log_info('用户调整哈希阈值', 'hash', threshold=threshold)
        self.classifier.set_hash_threshold(threshold)
        self.threshold_slider.setValue(threshold)
        self.threshold_value_label.setText(str(threshold))

    def on_threshold_changed(self, threshold: int):
        debug_manager.log_info('主窗口阈值变化', 'hash', threshold=threshold)
        self.threshold_value_label.setText(str(threshold))
        self.classifier.set_hash_threshold(threshold)
        
        if self.hash_completed and self.hash_list:
            debug_manager.log_info('重新分组', 'hash', threshold=threshold, hash_count=len(self.hash_list))
            from services.hash_analysis_service import HashAnalysisService
            groups = HashAnalysisService.group_by_similarity(self.hash_list, threshold)
            
            current_groups = self.classification_service.get_groups()
            processed_images = self.classification_service.processed_images
            
            if not groups:
                filtered_groups = current_groups
            else:
                filtered_groups = []
                similar_images = set()
                for group in groups:
                    filtered_group = [path for path in group if path not in processed_images]
                    if filtered_group:
                        filtered_groups.append(filtered_group)
                        similar_images.update(filtered_group)
                
                for group in current_groups:
                    for path in group:
                        if path not in similar_images and path not in processed_images:
                            filtered_groups.append([path])
            
            self.classification_service.set_groups(filtered_groups)
            
            all_image_paths = []
            for group in filtered_groups:
                all_image_paths.extend(group)
            cache = self.classifier.create_file_cache(all_image_paths)
            cache['duplicates'] = self.duplicate_service.get_duplicates()
            cache['similar_groups'] = groups
            cache['hash_list'] = self.hash_list
            self.classifier.save_hash_cache(cache)
            
            self.show_current_image()
            self.update_duplicate_list()
            self._update_hash_status(groups, self.duplicate_service.get_duplicates())

    def on_hash_canceled(self):
        self.hash_scanning = False
        self.status_label.setText("哈希分析已取消")
        debug_manager.log_info('哈希分析已取消', 'hash')

    def on_hash_stage_changed(self, stage: str, current: int, total: int):
        debug_manager.log_info('哈希分析阶段变更', 'hash', stage=stage, current=current, total=total)

    def on_hash_file_processed(self, filename: str, current: int, total: int):
        debug_manager.log_info('哈希分析文件处理', 'hash', filename=filename, current=current, total=total)

    def on_hash_finished(self, groups: list, duplicates: dict, hash_list: list = None):
        debug_manager.log_info('哈希分析完成', 'hash', group_count=len(groups), duplicate_groups=len(duplicates))
        self.hash_scanning = False
        self.hash_completed = True
        
        if hash_list:
            self.hash_list = hash_list
            debug_manager.log_info('保存哈希列表', 'hash', hash_count=len(hash_list))

        current_groups = self.classification_service.get_groups()
        processed_images = self.classification_service.processed_images
        
        if not groups:
            debug_manager.log_info('未找到相似图片，保留原始分组', 'hash', original_group_count=len(current_groups))
            filtered_groups = current_groups
        else:
            filtered_groups = []
            similar_images = set()
            for group in groups:
                filtered_group = [path for path in group if path not in processed_images]
                if filtered_group:
                    filtered_groups.append(filtered_group)
                    similar_images.update(filtered_group)
            
            for group in current_groups:
                for path in group:
                    if path not in similar_images and path not in processed_images:
                        filtered_groups.append([path])
        
        debug_manager.log_info('最终分组', 'hash', final_group_count=len(filtered_groups))
        self.classification_service.set_groups(filtered_groups)
        self.duplicate_service.set_duplicates(duplicates)

        all_image_paths = []
        for group in filtered_groups:
            all_image_paths.extend(group)
        cache = self.classifier.create_file_cache(all_image_paths)
        cache['duplicates'] = duplicates
        cache['similar_groups'] = groups
        
        if hash_list:
            cache['hash_list'] = hash_list
            file_hashes = {}
            for path, img_hash in hash_list:
                file_hashes[path] = {'img_hash': img_hash}
            cache['file_hashes'] = file_hashes
        
        md5_hash_map = {}
        for md5, paths in duplicates.items():
            for path in paths:
                if path not in md5_hash_map:
                    md5_hash_map[path] = md5
        if md5_hash_map:
            if 'file_hashes' not in cache:
                cache['file_hashes'] = {}
            for path, md5 in md5_hash_map.items():
                if path not in cache['file_hashes']:
                    cache['file_hashes'][path] = {}
                cache['file_hashes'][path]['md5'] = md5
        
        debug_manager.log_info('保存哈希缓存', 'hash', file_hashes_count=len(cache.get('file_hashes', {})))
        self.classifier.save_hash_cache(cache)

        self.threshold_group.setVisible(True)
        self.show_current_image()
        self.update_duplicate_list()
        self._update_hash_status(groups, duplicates)

    def _filter_processed_images(self, groups: list) -> list:
        processed_images = self.classification_service.processed_images
        filtered_groups = []
        for group in groups:
            filtered_group = [path for path in group if path not in processed_images]
            if filtered_group:
                filtered_groups.append(filtered_group)
        return filtered_groups

    def _load_cached_hash_results(self, image_paths: list):
        debug_manager.log_info('加载缓存的哈希结果', 'hash')
        self.status_label.setText("文件无变化，使用缓存结果")
        
        cache = self.classifier.load_hash_cache()
        similar_groups = cache.get('similar_groups', [])
        duplicates = cache.get('duplicates', {})
        hash_list = cache.get('hash_list', [])
        
        if hash_list:
            self.hash_list = hash_list
            self.hash_completed = True
            debug_manager.log_info('加载缓存的哈希列表', 'hash', hash_count=len(hash_list))
        
        current_groups = self.classification_service.get_groups()
        processed_images = self.classification_service.processed_images
        
        if similar_groups:
            filtered_groups = []
            similar_images = set()
            for group in similar_groups:
                filtered_group = [path for path in group if path not in processed_images]
                if filtered_group:
                    filtered_groups.append(filtered_group)
                    similar_images.update(filtered_group)
            
            for group in current_groups:
                for path in group:
                    if path not in similar_images and path not in processed_images:
                        filtered_groups.append([path])
            
            self.classification_service.set_groups(filtered_groups)
            debug_manager.log_info('缓存相似分组加载完成', 'hash', group_count=len(filtered_groups))
        elif current_groups:
            self.classification_service.set_groups(current_groups)
        
        self.duplicate_service.set_duplicates(duplicates)
        
        if self.hash_completed and self.hash_list:
            self.threshold_group.setVisible(True)
        
        self.show_current_image()
        self.update_duplicate_list()
        
        remaining_duplicates = self.duplicate_service.get_duplicates()
        if remaining_duplicates:
            total_duplicates = sum(len(p) - 1 for p in remaining_duplicates.values())
            self.status_label.setText(f"使用缓存: {len(self.classification_service.get_groups())}组, {len(remaining_duplicates)}组重复({total_duplicates}张)")
        else:
            self.status_label.setText(f"使用缓存，共 {len(self.classification_service.get_groups())} 组")

    def _update_hash_status(self, groups: list, duplicates: dict):
        remaining_duplicates = self.duplicate_service.get_duplicates()

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
        debug_manager.log_error('哈希分析出错', 'hash', error=error)
        QMessageBox.warning(self, "警告", f"后台分析时出错: {error}")

    def on_classification_progress(self, processed: int, total: int, message: str):
        self.status_label.setText(message)
        debug_manager.log_info('分类进度更新', 'classification', processed=processed, total=total)

    def on_classification_complete(self):
        self.status_label.setText("分类完成！")
        self.classifier.clear_unfinished_session()
        debug_manager.log_info('分类全部完成', 'classification')

    def on_image_moved(self, path: str, folder_name: str, success: bool):
        filename = os.path.basename(path)
        if success:
            debug_manager.log_info('图片移动成功', 'classification', filename=filename, folder=folder_name)
        else:
            debug_manager.log_warning('图片移动失败', 'classification', filename=filename)

    def on_group_changed(self, group_idx: int, total_groups: int, image_idx: int, total_images: int):
        self.group_info.setText(f"组: {group_idx + 1}/{total_groups}")
        self.image_info.setText(f"图片: {image_idx + 1}/{total_images}")
        debug_manager.log_info('分组切换', 'classification', group=group_idx + 1, total_groups=total_groups)

    def on_duplicate_deleted(self, md5_hash: str, deleted_count: int, remaining_count: int):
        debug_manager.log_info('重复图片删除', 'duplicate', deleted_count=deleted_count, remaining_count=remaining_count)

    def on_duplicate_processing(self, current: int, total: int):
        self.status_label.setText(f"正在删除重复图片: {current}/{total}")
        debug_manager.log_info('重复图片处理中', 'duplicate', current=current, total=total)

    def on_duplicate_all_processed(self):
        self.status_label.setText("所有重复图片已处理完成")
        self.duplicate_service.clear_all_duplicate_memory()
        debug_manager.log_info('重复图片全部处理完成', 'duplicate')

    def on_duplicate_memory_cleared(self):
        debug_manager.log_info('重复图片记忆已清除', 'duplicate')

    def on_scan_error(self, error: str):
        self.status_label.setText("扫描出错")
        debug_manager.log_error('扫描出错', 'scan', error=error)
        QMessageBox.critical(self, "错误", f"扫描图片时出错: {error}")

    def show_current_image(self):
        groups = self.classification_service.get_groups()
        current_group_index = self.classification_service.get_current_group_index()

        if not groups or current_group_index >= len(groups):
            debug_manager.log_info('没有图片组', 'image')
            self._clear_image_display()
            return

        current_group = groups[current_group_index]
        current_image_index = self.classification_service.get_current_image_index()

        if current_image_index >= len(current_group):
            current_image_index = 0

        image_path = current_group[current_image_index]

        current_group_index = self.classification_service.get_current_group_index() if hasattr(self.classification_service, 'get_current_group_index') else self.classification_service.current_group_index
        rotation = self.group_rotations.get(current_group_index, 0)
        
        try:
            debug_manager.log_info('开始加载图片', 'rotation', image_path=image_path, group_index=current_group_index, rotation=rotation)
            pixmap = QPixmap(image_path)
            if not pixmap.isNull():
                debug_manager.log_info('图片加载成功，准备应用旋转', 'rotation', pixmap_size=f"{pixmap.width()}x{pixmap.height()}", rotation=rotation)
                if rotation != 0:
                    debug_manager.log_info('应用旋转变换', 'rotation', angle=rotation)
                    transform = QTransform().rotate(rotation)
                    pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)
                    debug_manager.log_info('旋转变换完成', 'rotation', new_size=f"{pixmap.width()}x{pixmap.height()}")
                max_size = QSize(800, 600)
                scaled_pixmap = pixmap.scaled(max_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self.image_label.setPixmap(scaled_pixmap)
                debug_manager.log_info('图片显示完成', 'rotation', image_path=image_path, rotation=rotation, final_size=f"{scaled_pixmap.width()}x{scaled_pixmap.height()}")
            else:
                debug_manager.log_warning('图片加载失败', 'image', image_path=image_path, reason='pixmap is null')
                self.image_label.setText("无法加载图片")
        except Exception as e:
            debug_manager.log_exception(e, 'image', image_path=image_path)
            self.image_label.setText("无法加载图片")

        self.group_info.setText(f"组: {current_group_index + 1}/{len(groups)}")
        self.image_info.setText(f"图片: {current_image_index + 1}/{len(current_group)}")
        self.path_label.setText(image_path)

    def _clear_image_display(self):
        self.image_label.clear()
        self.group_info.setText("组: 0/0")
        self.image_info.setText("图片: 0/0")
        self.path_label.setText("")

    def update_duplicate_list(self):
        self.duplicate_table.setRowCount(0)
        duplicates = self.duplicate_service.get_duplicates()

        row = 0
        for md5, paths in duplicates.items():
            self.duplicate_table.insertRow(row)
            self.duplicate_table.setRowHeight(row, 36)
            
            checkbox = QCheckBox()
            checkbox.setChecked(False)
            checkbox.setStyleSheet("QCheckBox { width: 20px; height: 20px; }")
            checkbox.setAlignment(Qt.AlignCenter)
            self.duplicate_table.setCellWidget(row, 0, checkbox)
            
            filename = os.path.basename(paths[0])
            if len(filename) > 30:
                filename = filename[:27] + "..."
            
            item = QTableWidgetItem(f"重复 ({len(paths)}张): {filename}")
            item.setData(Qt.UserRole, (md5, paths))
            item.setFlags(item.flags() & ~Qt.ItemIsEditable)
            item.setTextAlignment(Qt.AlignVCenter | Qt.AlignLeft)
            self.duplicate_table.setItem(row, 1, item)
            
            row += 1
        
        if duplicates:
            self.duplicate_table.setColumnWidth(0, 40)
            self.duplicate_table.setColumnWidth(1, self.duplicate_table.width() - 40)
        
        if not duplicates:
            self.duplicate_table.insertRow(0)
            self.duplicate_table.setRowHeight(0, 60)
            
            empty_item = QTableWidgetItem("暂无重复图片")
            empty_item.setFlags(empty_item.flags() & ~Qt.ItemIsEditable)
            empty_item.setTextAlignment(Qt.AlignCenter)
            empty_item.setForeground(QColor("#7f8c8d"))
            self.duplicate_table.setItem(0, 0, empty_item)
            
            self.duplicate_table.setSpan(0, 0, 1, 2)

    def add_shortcut(self):
        debug_manager.log_info('开始添加快捷键', 'shortcut')
        dialog = ShortcutInputDialog(self)
        result = dialog.exec_()

        if result != QDialog.Accepted:
            return

        key = dialog.get_key()
        if not key:
            debug_manager.log_warning('按键为空', 'shortcut')
            return

        if key in self.classifier.get_all_shortcuts():
            debug_manager.log_warning('快捷键已存在', 'shortcut', key=key)
            QMessageBox.warning(self, "警告", "该快捷键已被使用")
            return

        folder_dialog = FolderSelectDialog(self)
        folder_result = folder_dialog.exec_()

        if folder_result != QDialog.Accepted:
            debug_manager.log_info('用户取消选择文件夹', 'shortcut')
            return

        folder_path = folder_dialog.get_selected_path()
        if not folder_path:
            debug_manager.log_warning('未选择文件夹', 'shortcut')
            return

        if not self.classifier.add_shortcut(key, folder_path):
            debug_manager.log_error('添加快捷键失败', 'shortcut', key=key, folder_path=folder_path)
            QMessageBox.warning(self, "警告", "添加快捷键失败")
            return

        debug_manager.log_info('快捷键添加成功', 'shortcut', key=key, folder_path=folder_path)
        self.load_shortcuts()
        QMessageBox.information(self, "成功", f"已将快捷键 '{key}' 绑定到文件夹")

    def remove_shortcut(self):
        debug_manager.log_info('开始删除快捷键', 'shortcut')
        selected_items = self.shortcut_list.selectedItems()
        if not selected_items:
            debug_manager.log_warning('未选择要删除的快捷键', 'shortcut')
            QMessageBox.warning(self, "警告", "请选择要删除的快捷键")
            return

        key = selected_items[0].data(Qt.UserRole)
        debug_manager.log_info('删除快捷键', 'shortcut', key=key)
        if self.classifier.remove_shortcut(key):
            self.load_shortcuts()
            debug_manager.log_info('快捷键删除成功', 'shortcut', key=key)
            QMessageBox.information(self, "成功", "快捷键已删除")
        else:
            debug_manager.log_error('快捷键删除失败', 'shortcut', key=key)
            QMessageBox.warning(self, "警告", "删除快捷键失败")

    def on_duplicate_table_click(self, row, column):
        checkbox = self.duplicate_table.cellWidget(row, 0)
        if checkbox:
            checkbox.setChecked(not checkbox.isChecked())

    def select_all_duplicates(self):
        debug_manager.log_info('全选重复图片组', 'duplicate')
        for row in range(self.duplicate_table.rowCount()):
            checkbox = self.duplicate_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(True)

    def deselect_all_duplicates(self):
        debug_manager.log_info('取消全选重复图片组', 'duplicate')
        for row in range(self.duplicate_table.rowCount()):
            checkbox = self.duplicate_table.cellWidget(row, 0)
            if checkbox:
                checkbox.setChecked(False)

    def delete_selected_duplicates(self):
        debug_manager.log_info('开始删除选中的重复图片', 'duplicate')
        selected_rows = []
        
        for row in range(self.duplicate_table.rowCount()):
            checkbox = self.duplicate_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                item = self.duplicate_table.item(row, 1)
                if item:
                    data = item.data(Qt.UserRole)
                    if data and len(data) == 2:
                        selected_rows.append(data)
        
        if not selected_rows:
            debug_manager.log_warning('未选择重复图片组', 'duplicate')
            QMessageBox.warning(self, "警告", "请选择要处理的重复图片组")
            return

        total_paths = sum(len(paths) for _, paths in selected_rows)
        total_deletions = sum(len(paths) - 1 for _, paths in selected_rows)

        reply = QMessageBox.question(
            self,
            "确认删除",
            f"共选择 {len(selected_rows)} 组重复图片，\n"
            f"总计 {total_paths} 张图片，\n"
            f"将保留每组第一张，删除其余 {total_deletions} 张，\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            debug_manager.log_info('用户确认删除', 'duplicate', group_count=len(selected_rows))
            
            for md5_hash, paths in selected_rows:
                deleted_paths, failed_paths = self.duplicate_service.delete_duplicate_group(md5_hash, paths)
                for path in failed_paths:
                    QMessageBox.warning(self, "警告", f"删除失败: {path}")

            self.update_duplicate_list()
            self.refresh_groups()

            if self.duplicate_service.is_all_processed():
                self.status_label.setText("所有重复图片已处理完成")
                self.duplicate_service.clear_all_duplicate_memory()

    def clear_storage(self):
        debug_manager.log_info('打开存储清除对话框', 'storage')
        dialog = StorageCleanDialog(self)
        result = dialog.exec_()

        if result == QDialog.Accepted:
            self.load_shortcuts()
            self.update_recent_folders()
            self.status_label.setText("存储已清除")
            debug_manager.log_info('存储清除完成', 'storage')

    def refresh_groups(self):
        self.classification_service.refresh_groups()

        if self.classification_service.is_classification_complete():
            self.classifier.clear_unfinished_session()
            self.status_label.setText("分类完成！")

        self.show_current_image()

    def classify_current_group(self, shortcut: str):
        success_count, failed_paths = self.classification_service.classify_current_group(shortcut)

        folder_name = os.path.basename(self.classifier.get_folder(shortcut))
        if success_count > 0 and not failed_paths:
            self.status_label.setText(f"已将 {success_count} 张图片分类到 '{folder_name}'")
        elif success_count > 0 and failed_paths:
            self.status_label.setText(f"分类完成: {success_count}成功, {len(failed_paths)}失败")
        elif failed_paths:
            self.status_label.setText(f"分类失败: {len(failed_paths)}张图片")

        self.show_current_image()

    def closeEvent(self, event):
        groups = self.classification_service.get_groups()

        if groups and self.classifier.current_folder:
            total_count = sum(len(g) for g in groups) + len(self.classification_service.processed_images)
            processed_count = len(self.classification_service.processed_images)

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
        modifiers = event.modifiers()
        has_ctrl = bool(modifiers & Qt.ControlModifier)
        is_left = key == Qt.Key_Left
        is_right = key == Qt.Key_Right
        is_up = key == Qt.Key_Up
        is_down = key == Qt.Key_Down
        debug_manager.log_info('keyPressEvent: 键盘事件', 'keyboard', key=key, modifiers=modifiers, has_ctrl=has_ctrl, is_left=is_left, is_right=is_right, is_up=is_up, is_down=is_down)

        if has_ctrl:
            if is_left:
                debug_manager.log_info('keyPressEvent: Ctrl+Left -> 调用rotate_image(False)', 'keyboard')
                self.rotate_image(False)
                return
            elif is_right:
                debug_manager.log_info('keyPressEvent: Ctrl+Right -> 调用rotate_image(True)', 'keyboard')
                self.rotate_image(True)
                return
            elif is_up:
                debug_manager.log_info('keyPressEvent: Ctrl+Up -> 调用rotate_image(False, 180)', 'keyboard')
                self.rotate_image(False, 180)
                return
            elif is_down:
                debug_manager.log_info('keyPressEvent: Ctrl+Down -> 调用rotate_image(True, 180)', 'keyboard')
                self.rotate_image(True, 180)
                return

        if is_left:
            debug_manager.log_info('keyPressEvent: Left -> 调用prev_image()', 'keyboard')
            self.prev_image()
        elif is_right:
            debug_manager.log_info('keyPressEvent: Right -> 调用next_image()', 'keyboard')
            self.next_image()
        elif is_up:
            debug_manager.log_info('keyPressEvent: Up -> 调用prev_group()', 'keyboard')
            self.prev_group()
        elif is_down:
            debug_manager.log_info('keyPressEvent: Down -> 调用next_group()', 'keyboard')
            self.next_group()
        else:
            key_str = key_to_string(key)
            debug_manager.log_info('keyPressEvent: 其他按键', 'keyboard', key_str=key_str, is_shortcut=key_str in self.classifier.get_all_shortcuts() if key_str else False)
            if key_str and key_str in self.classifier.get_all_shortcuts():
                self.classify_current_group(key_str)
            else:
                debug_manager.log_info('keyPressEvent: 调用父类keyPressEvent', 'keyboard')
                super().keyPressEvent(event)

    def prev_image(self):
        debug_manager.log_info('切换到上一张图片', 'rotation')
        self.classification_service.prev_image()
        self.show_current_image()

    def next_image(self):
        debug_manager.log_info('切换到下一张图片', 'rotation')
        self.classification_service.next_image()
        self.show_current_image()

    def prev_group(self):
        debug_manager.log_info('切换到上一组', 'rotation')
        self.classification_service.prev_group()
        self.show_current_image()

    def next_group(self):
        debug_manager.log_info('切换到下一组', 'rotation')
        self.classification_service.next_group()
        self.show_current_image()

    def rotate_image(self, clockwise: bool, degrees: int = 90):
        current_group_index = self.classification_service.get_current_group_index() if hasattr(self.classification_service, 'get_current_group_index') else self.classification_service.current_group_index
        current_rotation = self.group_rotations.get(current_group_index, 0)
        
        debug_manager.log_info('开始旋转图片', 'rotation', clockwise=clockwise, degrees=degrees, group_index=current_group_index, rotation_before=current_rotation)
        
        if clockwise:
            new_rotation = (current_rotation - degrees) % 360
        else:
            new_rotation = (current_rotation + degrees) % 360
        
        self.group_rotations[current_group_index] = new_rotation
        debug_manager.log_info('图片旋转完成', 'rotation', clockwise=clockwise, degrees=degrees, group_index=current_group_index, rotation_after=new_rotation)
        self.show_current_image()

    def show_duplicate_detail(self):
        duplicates = self.duplicate_service.get_duplicates()

        if not duplicates:
            debug_manager.log_info('暂无重复图片', 'duplicate')
            QMessageBox.information(self, "提示", "暂无重复图片")
            return

        valid_groups = self.duplicate_service.get_valid_groups()
        if not valid_groups:
            debug_manager.log_info('暂无有效重复图片组', 'duplicate')
            QMessageBox.information(self, "提示", "暂无重复图片")
            return

        selected_groups = []
        selected_md5s = []
        
        for row in range(self.duplicate_table.rowCount()):
            checkbox = self.duplicate_table.cellWidget(row, 0)
            if checkbox and checkbox.isChecked():
                item = self.duplicate_table.item(row, 1)
                if item:
                    data = item.data(Qt.UserRole)
                    if data and len(data) == 2:
                        md5_hash, paths = data
                        if paths and len(paths) > 1:
                            selected_groups.append(paths)
                            selected_md5s.append(md5_hash)

        if not selected_groups:
            selected_groups = [valid_groups[0][1]]
            selected_md5s = [valid_groups[0][0]]

        try:
            debug_manager.log_info('打开重复图片详情', 'duplicate', group_count=len(selected_groups))
            detail_dialog = DuplicateDetailDialog(selected_groups, self, selected_md5s)
            result = detail_dialog.exec_()

            if result == QDialog.Accepted:
                duplicates = self.duplicate_service.get_duplicates()
                for md5_hash in selected_md5s:
                    if md5_hash and md5_hash in duplicates:
                        del self.duplicate_service.duplicates[md5_hash]
                self.update_duplicate_list()
                self.refresh_groups()

                if self.duplicate_service.is_all_processed():
                    self.status_label.setText("所有重复图片已处理完成")
                    self.duplicate_service.clear_all_duplicate_memory()
        except Exception as e:
            debug_manager.log_exception(e, 'duplicate', group_count=len(selected_groups))
            QMessageBox.critical(self, "错误", f"打开详情窗口失败: {str(e)}")