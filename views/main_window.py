import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox,
    QListWidget, QListWidgetItem, QScrollArea, QSplitter,
    QGroupBox, QComboBox, QSlider, QShortcut, QSizePolicy,
    QDialog
)
from PyQt5.QtGui import QPixmap, QFont, QTransform, QKeySequence, QColor
from PyQt5.QtCore import Qt, QSize, QTimer

from dialogs.duplicate_detail_dialog import DuplicateDetailDialog
from dialogs.storage_clean_dialog import StorageCleanDialog
from dialogs.folder_select_dialog import FolderSelectDialog
from dialogs.shortcut_input_dialog import ShortcutInputDialog
from dialogs.hash_analysis_dialog import HashAnalysisDialog
from core.debug_manager import debug_manager
from presenters.main_presenter import MainPresenter


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分类器")
        self.setGeometry(100, 100, 1200, 800)

        # 阈值滑块防抖定时器：拖动时只更新数字显示，停止 300ms 后才执行重分组
        self._threshold_timer = QTimer(self)
        self._threshold_timer.setSingleShot(True)
        self._threshold_timer.setInterval(300)
        self._threshold_timer.timeout.connect(self._apply_threshold)
        self._pending_threshold = None

        self.presenter = MainPresenter(self)
        self.init_ui()
        self.connect_signals()
        self.presenter.load_initial_data()

        debug_manager.log_info('主窗口初始化完成', 'main')

    def init_ui(self):
        self.setStyleSheet("""
            QMainWindow {
                background-color: #2d2d2d;
            }
            QWidget {
                background-color: #2d2d2d;
                color: #ffffff;
            }
            QGroupBox {
                font-weight: bold;
                color: #ecf0f1;
                border: 1px solid #34495e;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: #3498db;
            }
            QPushButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #2c3e50;
                border-radius: 3px;
                padding: 6px 12px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
            QLabel {
                color: #ecf0f1;
            }
            QComboBox {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #2c3e50;
                border-radius: 3px;
                padding: 4px;
            }
            QListWidget {
                background-color: #1e1e1e;
                color: #ecf0f1;
                border: 1px solid #2c3e50;
                border-radius: 3px;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #2c3e50;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #3498db;
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }
            QScrollArea {
                border: none;
            }
        """)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet("QSplitter::handle { background-color: #34495e; }")
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([300, 900])

        main_layout.addWidget(splitter)

    def _create_left_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(8)
        layout.setContentsMargins(10, 10, 10, 10)

        select_btn = QPushButton("选择图片文件夹")
        select_btn.clicked.connect(self.select_folder)
        select_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border-color: #2980b9;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        layout.addWidget(select_btn)

        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("最近分类的文件夹")
        layout.addWidget(self.recent_combo)

        self.status_label = QLabel("请选择图片文件夹开始分类")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        layout.addWidget(self.status_label)

        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setVisible(False)
        self.threshold_group = threshold_group
        threshold_layout = QVBoxLayout(threshold_group)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(8)
        slider_label = QLabel("阈值:")
        slider_label.setStyleSheet("color: #3498db;")
        slider_layout.addWidget(slider_label)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(2, 25)
        self.threshold_slider.setValue(10)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        slider_layout.addWidget(self.threshold_slider)

        self.threshold_value_label = QLabel("10")
        self.threshold_value_label.setStyleSheet("color: #3498db; font-weight: bold;")
        slider_layout.addWidget(self.threshold_value_label)

        threshold_layout.addLayout(slider_layout)

        threshold_tip = QLabel("阈值越小，相似度要求越高 (2-25)")
        threshold_tip.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        threshold_layout.addWidget(threshold_tip)

        layout.addWidget(threshold_group)

        shortcut_group = QGroupBox("分类快捷键")
        shortcut_layout = QVBoxLayout(shortcut_group)

        self.shortcut_list = QListWidget()
        self.shortcut_list.setMinimumHeight(100)
        self.shortcut_list.setMaximumHeight(150)
        shortcut_layout.addWidget(self.shortcut_list)

        add_shortcut_btn = QPushButton("添加快捷键")
        add_shortcut_btn.clicked.connect(self.add_shortcut)
        shortcut_layout.addWidget(add_shortcut_btn)

        del_shortcut_btn = QPushButton("删除快捷键")
        del_shortcut_btn.clicked.connect(self.remove_shortcut)
        shortcut_layout.addWidget(del_shortcut_btn)

        layout.addWidget(shortcut_group)

        duplicate_group = self._create_duplicate_group()
        layout.addWidget(duplicate_group)

        storage_btn = QPushButton("清除存储占用")
        storage_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border-color: #c0392b;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
        """)
        storage_btn.clicked.connect(self.clear_storage)
        layout.addWidget(storage_btn)

        return panel

    def _create_duplicate_group(self):
        group = QGroupBox("重复图片")
        group.setVisible(True)
        self.duplicate_group = group
        layout = QVBoxLayout(group)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        self.duplicate_list = QListWidget()
        self.duplicate_list.setMinimumHeight(100)
        self.duplicate_list.setMaximumHeight(180)
        self.duplicate_list.setStyleSheet("""
            QListWidget {
                background-color: #1e1e1e;
                border: 1px solid #34495e;
                border-radius: 3px;
                color: #ecf0f1;
                font-size: 13px;
            }
            QListWidget::item {
                padding: 5px 8px;
                border-bottom: 1px solid #2c3e50;
                height: 32px;
            }
            QListWidget::item:alternate {
                background-color: #252525;
            }
            QListWidget::item:hover {
                background-color: #34495e;
            }
            QListWidget::item:selected {
                background-color: #34495e;
                color: #ecf0f1;
            }
        """)
        self.duplicate_list.itemClicked.connect(self.on_duplicate_item_clicked)
        layout.addWidget(self.duplicate_list)

        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(4)
        
        select_all_btn = QPushButton("全选")
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border-color: #2980b9;
                color: white;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_duplicates)
        btn_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消")
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                border-color: #707b7c;
                color: white;
                padding: 4px 10px;
                font-size: 11px;
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

        view_btn = QPushButton("查看")
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                border-color: #8e44ad;
                color: white;
                padding: 4px 10px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
        """)
        view_btn.clicked.connect(self.show_duplicate_detail)
        btn_layout.addWidget(view_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border-color: #c0392b;
                color: white;
                padding: 4px 10px;
                font-size: 11px;
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

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #34495e;
                border-radius: 5px;
            }
        """)
        layout.addWidget(self.image_label)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(20)

        self.group_info_label = QLabel("组: /")
        self.group_info_label.setStyleSheet("color: #3498db; font-weight: bold;")
        info_layout.addWidget(self.group_info_label)

        self.image_info_label = QLabel("图片: /")
        self.image_info_label.setStyleSheet("color: #9b59b6; font-weight: bold;")
        info_layout.addWidget(self.image_info_label)

        self.path_label = QLabel("")
        self.path_label.setStyleSheet("color: #7f8c8d; font-size: 11px;")
        self.path_label.setMaximumWidth(400)
        info_layout.addWidget(self.path_label)

        layout.addLayout(info_layout)

        nav_layout = self._create_navigation_layout()
        layout.addLayout(nav_layout)

        return panel

    def _create_navigation_layout(self):
        layout = QVBoxLayout()

        view_layout = QHBoxLayout()
        view_layout.setSpacing(4)

        rotate_180_ccw_btn = QPushButton("↻ 180°逆 (Ctrl+↑)")
        rotate_180_ccw_btn.clicked.connect(lambda: self.rotate_image(False, 180))
        rotate_180_ccw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border-color: #2c3e50;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
        """)
        view_layout.addWidget(rotate_180_ccw_btn)

        rotate_ccw_btn = QPushButton("↻ 90°逆 (Ctrl+←)")
        rotate_ccw_btn.clicked.connect(lambda: self.rotate_image(False))
        rotate_ccw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border-color: #2c3e50;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
        """)
        view_layout.addWidget(rotate_ccw_btn)

        rotate_cw_btn = QPushButton("↺ 90°顺 (Ctrl+→)")
        rotate_cw_btn.clicked.connect(lambda: self.rotate_image(True))
        rotate_cw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border-color: #2c3e50;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
        """)
        view_layout.addWidget(rotate_cw_btn)

        rotate_180_cw_btn = QPushButton("↺ 180°顺 (Ctrl+↓)")
        rotate_180_cw_btn.clicked.connect(lambda: self.rotate_image(True, 180))
        rotate_180_cw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border-color: #2c3e50;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
        """)
        view_layout.addWidget(rotate_180_cw_btn)

        layout.addLayout(view_layout)

        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(4)

        prev_group_btn = QPushButton("上一组 (↑)")
        prev_group_btn.setShortcut("Up")
        prev_group_btn.clicked.connect(self.prev_group)
        prev_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border-color: #1e8449;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        switch_layout.addWidget(prev_group_btn)

        prev_img_btn = QPushButton("上一张 (←)")
        prev_img_btn.setShortcut("Left")
        prev_img_btn.clicked.connect(self.prev_image)
        prev_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border-color: #1e8449;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        switch_layout.addWidget(prev_img_btn)

        next_img_btn = QPushButton("下一张 (→)")
        next_img_btn.setShortcut("Right")
        next_img_btn.clicked.connect(self.next_image)
        next_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border-color: #1e8449;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        switch_layout.addWidget(next_img_btn)

        next_group_btn = QPushButton("下一组 (↓)")
        next_group_btn.setShortcut("Down")
        next_group_btn.clicked.connect(self.next_group)
        next_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border-color: #1e8449;
                padding: 5px 12px;
                font-size: 11px;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
        """)
        switch_layout.addWidget(next_group_btn)

        layout.addLayout(switch_layout)

        return layout

    def connect_signals(self):
        self.recent_combo.currentIndexChanged.connect(self.on_recent_folder_selected)

        self.shortcut_rotate_ccw = QShortcut(QKeySequence("Ctrl+Left"), self)
        self.shortcut_rotate_ccw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_ccw.activated.connect(lambda: self.rotate_image(False))

        self.shortcut_rotate_cw = QShortcut(QKeySequence("Ctrl+Right"), self)
        self.shortcut_rotate_cw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_cw.activated.connect(lambda: self.rotate_image(True))

        self.shortcut_rotate_180_ccw = QShortcut(QKeySequence("Ctrl+Up"), self)
        self.shortcut_rotate_180_ccw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_180_ccw.activated.connect(lambda: self.rotate_image(False, 180))

        self.shortcut_rotate_180_cw = QShortcut(QKeySequence("Ctrl+Down"), self)
        self.shortcut_rotate_180_cw.setContext(Qt.ApplicationShortcut)
        self.shortcut_rotate_180_cw.activated.connect(lambda: self.rotate_image(True, 180))

    def show_current_image(self):
        current_path = self.presenter.get_current_image_path()
        if not current_path or not os.path.exists(current_path):
            self.image_label.clear()
            self.group_info_label.setText("组: /")
            self.image_info_label.setText("图片: /")
            self.path_label.setText("")
            return

        total_groups = self.presenter.get_total_groups()
        current_group_index = self.presenter.get_current_group_index()
        current_image_index = self.presenter.get_current_image_index()
        current_group_size = self.presenter.get_current_group_size()

        self.group_info_label.setText(f"组: {current_group_index + 1}/{total_groups}")
        self.image_info_label.setText(f"图片: {current_image_index + 1}/{current_group_size}")

        path_display = current_path
        if len(path_display) > 50:
            path_display = "..." + path_display[-47:]
        self.path_label.setText(path_display)

        try:
            pixmap = QPixmap(current_path)
            if pixmap.isNull():
                self.image_label.setText("无法加载图片")
                return

            rotation = self.presenter.get_current_rotation()
            if rotation != 0:
                transform = QTransform()
                transform.rotate(rotation)
                pixmap = pixmap.transformed(transform, Qt.SmoothTransformation)

            display_size = self.image_label.size() - QSize(40, 40)
            scaled_pixmap = pixmap.scaled(display_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
            self.image_label.setPixmap(scaled_pixmap)
        except Exception as e:
            debug_manager.log_exception('加载图片失败', 'image', error=e)
            self.image_label.setText(f"加载失败: {str(e)}")

    def update_shortcuts(self, shortcuts: dict):
        self.shortcut_list.clear()
        for key, path in shortcuts.items():
            item = QListWidgetItem(f"{key} -> {os.path.basename(path)}")
            item.setData(Qt.UserRole, key)
            self.shortcut_list.addItem(item)

    def update_recent_folders(self, recent_folders: list):
        self.recent_combo.clear()
        self.recent_combo.addItem("选择最近的文件夹", "")
        for folder in recent_folders:
            folder_name = os.path.basename(folder) or folder
            self.recent_combo.addItem(folder_name, folder)

    def update_duplicate_list(self, duplicates: dict):
        self.duplicate_list.clear()
        for md5, paths in duplicates.items():
            filename = os.path.basename(paths[0])
            if len(filename) > 25:
                filename = filename[:22] + "..."
            
            item = QListWidgetItem(f"重复 ({len(paths)}张): {filename}")
            item.setData(Qt.UserRole, (md5, paths))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Unchecked)
            self.duplicate_list.addItem(item)
        
        if not duplicates:
            item = QListWidgetItem("暂无重复图片")
            item.setFlags(item.flags() & ~Qt.ItemIsSelectable & ~Qt.ItemIsEnabled)
            item.setForeground(QColor("#7f8c8d"))
            self.duplicate_list.addItem(item)

    def update_threshold(self, threshold: int):
        # 程序设置阈值时阻塞信号，避免触发 on_threshold_changed 防抖流程
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(threshold)
        self.threshold_slider.blockSignals(False)
        self.threshold_value_label.setText(str(threshold))

    def show_threshold_group(self):
        self.threshold_group.setVisible(True)

    def hide_threshold_group(self):
        self.threshold_group.setVisible(False)

    def set_status(self, text: str):
        self.status_label.setText(text)

    def show_info_message(self, message: str):
        QMessageBox.information(self, "提示", message)

    def show_warning_message(self, message: str):
        QMessageBox.warning(self, "警告", message)

    def show_error_message(self, message: str):
        QMessageBox.critical(self, "错误", message)

    def show_folder_dialog(self, callback):
        dialog = FolderSelectDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            callback(dialog.get_selected_path())
        else:
            callback("")

    def show_unfinished_session_dialog(self, folder_path, total_count, processed_count, remaining, continue_callback, cancel_callback):
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
            continue_callback(folder_path)
        else:
            cancel_callback()

    def show_hash_analysis_dialog(self, hash_service,
                                  progress_callback, finished_callback,
                                  canceled_callback, error_callback, threshold_callback):
        """打开哈希分析对话框。

        传入 total_count 和 initial_threshold 替代让对话框直接读取 service 属性；
        连接 cancel_requested 信号到 service.cancel，使取消操作通过信号链传递。
        """
        total_count = len(hash_service.image_paths) if hasattr(hash_service, 'image_paths') else 0
        initial_threshold = hash_service.threshold
        self.hash_dialog = HashAnalysisDialog(hash_service, total_count, initial_threshold, self)
        self.hash_dialog.progress_updated_signal.connect(progress_callback)
        self.hash_dialog.analysis_finished_signal.connect(finished_callback)
        self.hash_dialog.analysis_canceled_signal.connect(canceled_callback)
        self.hash_dialog.analysis_error_signal.connect(error_callback)
        self.hash_dialog.threshold_changed.connect(threshold_callback)
        self.hash_dialog.cancel_requested.connect(hash_service.cancel)
        self.hash_dialog.show()

    def show_delete_confirm_dialog(self, group_count, total_paths, total_deletions, callback):
        reply = QMessageBox.question(
            self,
            "确认删除",
            f"共选择 {group_count} 组重复图片，\n"
            f"总计 {total_paths} 张图片，\n"
            f"将保留每组第一张，删除其余 {total_deletions} 张，\n"
            f"是否继续？",
            QMessageBox.Yes | QMessageBox.No
        )

        if reply == QMessageBox.Yes:
            selected_items = self.get_selected_duplicates()
            callback(selected_items)

    def show_duplicate_detail_dialog(self, selected_groups, selected_md5s, callback):
        """打开重复图片详情对话框。

        Args:
            selected_groups: 用户选中的重复组路径列表
            selected_md5s: 对应的 MD5 列表
            callback: 关闭后回调，签名为 callback(deletions)，deletions 为
                      [(md5_hash, [paths]), ...] 列表（取消时为空列表）
        """
        detail_dialog = DuplicateDetailDialog(selected_groups, self, selected_md5s)
        result = detail_dialog.exec_()
        if result == QDialog.Accepted:
            deletions = detail_dialog.get_deletion_result()
        else:
            deletions = []
        callback(deletions)

    def show_storage_clean_dialog(self, storage_size: int, storage_details: dict):
        """打开存储清理对话框。

        Args:
            storage_size: 总存储占用字节数
            storage_details: 各类别详情字典

        Returns:
            选中类别键列表，或 None（用户取消）
        """
        dialog = StorageCleanDialog(storage_size, storage_details, self)
        if dialog.exec_() == QDialog.Accepted:
            return dialog.get_selected_categories()
        return None

    def select_folder(self):
        self.presenter.select_folder()

    def on_folder_selected(self, folder_path):
        self.presenter.on_folder_selected(folder_path)

    def on_recent_folder_selected(self, index: int):
        if index == 0:
            return

        folder_path = self.recent_combo.itemData(index)
        if folder_path and os.path.exists(folder_path):
            self.presenter.start_scanning(folder_path)
        elif folder_path:
            debug_manager.log_warning('最近文件夹不存在', 'folder', folder_path=folder_path)
            QMessageBox.warning(self, "警告", f"文件夹不存在: {folder_path}")
            self.update_recent_folders(self.presenter.get_recent_folders())

    def on_threshold_changed(self, threshold: int):
        """滑块值变化：立即更新数字显示（即时反馈），重启防抖定时器延迟执行重分组。

        拖动时 valueChanged 高频触发，若每次都执行 group_by_similarity(O(n²)) +
        磁盘 IO + UI 刷新会导致明显卡顿。防抖 300ms 后才调用 Presenter 执行重量级操作。
        """
        self.threshold_value_label.setText(str(threshold))
        self._pending_threshold = threshold
        self._threshold_timer.start()

    def _apply_threshold(self):
        """防抖超时后执行：调用 Presenter 进行重分组等重量级操作。"""
        if self._pending_threshold is not None:
            threshold = self._pending_threshold
            self._pending_threshold = None
            self.presenter.on_threshold_changed(threshold)

    def next_image(self):
        self.presenter.next_image()

    def prev_image(self):
        self.presenter.prev_image()

    def next_group(self):
        self.presenter.next_group()

    def prev_group(self):
        self.presenter.prev_group()

    def rotate_image(self, clockwise: bool, angle: int = 90):
        self.presenter.rotate_image(clockwise, angle)

    def add_shortcut(self):
        dialog = ShortcutInputDialog(self)
        if dialog.exec_() == QDialog.Accepted:
            # get_key() 返回的 selected_key 已经是 key_to_string 转换后的字符串
            key = dialog.get_key()
            if key:
                folder_dialog = FolderSelectDialog(self)
                if folder_dialog.exec_() == QDialog.Accepted:
                    folder_path = folder_dialog.get_selected_path()
                    if folder_path:
                        self.presenter.add_shortcut(key, folder_path)

    def remove_shortcut(self):
        current_item = self.shortcut_list.currentItem()
        if not current_item:
            QMessageBox.warning(self, "警告", "请选择要删除的快捷键")
            return

        key = current_item.data(Qt.UserRole)
        self.presenter.remove_shortcut(key)

    def select_all_duplicates(self):
        for i in range(self.duplicate_list.count()):
            item = self.duplicate_list.item(i)
            if item and (item.flags() & Qt.ItemIsEnabled):
                item.setCheckState(Qt.Checked)

    def deselect_all_duplicates(self):
        for i in range(self.duplicate_list.count()):
            item = self.duplicate_list.item(i)
            if item and (item.flags() & Qt.ItemIsEnabled):
                item.setCheckState(Qt.Unchecked)

    def on_duplicate_item_clicked(self, item):
        if item and (item.flags() & Qt.ItemIsEnabled):
            if item.checkState() == Qt.Checked:
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)

    def get_selected_duplicates(self):
        selected_items = []
        for i in range(self.duplicate_list.count()):
            item = self.duplicate_list.item(i)
            if item and item.checkState() == Qt.Checked:
                data = item.data(Qt.UserRole)
                if data and len(data) == 2:
                    selected_items.append(data)
        return selected_items

    def delete_selected_duplicates(self):
        self.presenter.delete_selected_duplicates()

    def show_duplicate_detail(self):
        self.presenter.show_duplicate_detail()

    def on_duplicate_detail_closed(self, result, selected_md5s):
        self.presenter.on_duplicate_detail_closed(result, selected_md5s)

    def clear_storage(self):
        self.presenter.clear_storage()

    def on_image_classified(self, old_path, new_path):
        debug_manager.log_info('图片分类完成', 'classification', old_path=old_path, new_path=new_path)

    def refresh_groups(self):
        self.show_current_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_current_image()
