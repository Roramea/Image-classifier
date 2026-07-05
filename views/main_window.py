import os
from collections import OrderedDict

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QLineEdit, QToolButton,
    QListWidget, QListWidgetItem, QScrollArea, QSplitter,
    QGroupBox, QComboBox, QSlider, QShortcut, QSizePolicy,
    QDialog
)
from PyQt5.QtGui import QPixmap, QFont, QTransform, QKeySequence, QColor, QKeyEvent
from PyQt5.QtCore import Qt, QSize, QTimer

from dialogs.duplicate_detail_dialog import DuplicateDetailDialog
from dialogs.storage_clean_dialog import StorageCleanDialog
from dialogs.folder_select_dialog import FolderSelectDialog
from dialogs.shortcut_input_dialog import ShortcutInputDialog
from dialogs.hash_analysis_dialog import HashAnalysisDialog
from core.debug_manager import debug_manager
from core.utils import key_to_string
from presenters.main_presenter import MainPresenter
from widgets.scrolling_label import ScrollingLabel


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

        # 图片缓存（LRU）：避免重复解码大图，提升切换浏览速度
        self._image_cache = OrderedDict()
        self._image_cache_max = 10

        self.presenter = MainPresenter(self)
        self.init_ui()
        self.connect_signals()
        self.presenter.load_initial_data()

        debug_manager.log_info('主窗口初始化完成', 'main')

    def closeEvent(self, event):
        """应用关闭时通知 Presenter 保存未完成会话等清理工作。"""
        self.presenter.on_app_close()
        super().closeEvent(event)

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
        panel.setMinimumWidth(220)
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
        self.recent_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.recent_combo.setMinimumContentsLength(15)
        self.recent_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.recent_combo.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.recent_combo)

        status_layout = QHBoxLayout()
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)

        self.status_label = ScrollingLabel()
        self.status_label.setText("请选择图片文件夹开始分类")
        self.status_label.setStyleSheet("color: #95a5a6; font-size: 12px;")
        self.status_label.setScrollSpeed(30)
        self.status_label.setMinimumHeight(20)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_layout.addWidget(self.status_label)

        # 最小化哈希分析弹窗后显示的恢复按钮，默认隐藏
        self.restore_hash_dialog_btn = QToolButton()
        self.restore_hash_dialog_btn.setText("恢复分析")
        self.restore_hash_dialog_btn.setStyleSheet("""
            QToolButton {
                background-color: #3498db;
                color: white;
                border: none;
                border-radius: 3px;
                padding: 2px 8px;
                font-size: 11px;
            }
            QToolButton:hover {
                background-color: #2980b9;
            }
        """)
        self.restore_hash_dialog_btn.setVisible(False)
        self.restore_hash_dialog_btn.clicked.connect(self.restore_hash_dialog)
        status_layout.addWidget(self.restore_hash_dialog_btn)

        layout.addLayout(status_layout)

        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setVisible(True)
        self.threshold_group = threshold_group
        threshold_layout = QVBoxLayout(threshold_group)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(2)
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

        # 减号按钮
        self.threshold_minus_btn = QToolButton()
        self.threshold_minus_btn.setText("−")
        self.threshold_minus_btn.setFixedSize(16, 16)
        self.threshold_minus_btn.setStyleSheet("""
            QToolButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #2c3e50;
                border-radius: 2px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QToolButton:hover { background-color: #3d566e; }
            QToolButton:pressed { background-color: #2c3e50; }
            QToolButton:disabled { background-color: #2c3e50; color: #7f8c8d; }
        """)
        self.threshold_minus_btn.clicked.connect(self.on_threshold_minus)
        slider_layout.addWidget(self.threshold_minus_btn)

        # 数值输入框（可键盘输入）
        self.threshold_value_edit = QLineEdit("10")
        self.threshold_value_edit.setFixedWidth(30)
        self.threshold_value_edit.setAlignment(Qt.AlignCenter)
        self.threshold_value_edit.setMaxLength(2)
        self.threshold_value_edit.setStyleSheet("""
            QLineEdit {
                background-color: #1e1e1e;
                color: #3498db;
                font-weight: bold;
                border: 1px solid #2c3e50;
                border-radius: 2px;
                padding: 0px;
                font-size: 12px;
            }
            QLineEdit:focus { border: 1px solid #3498db; }
        """)
        self.threshold_value_edit.returnPressed.connect(self.on_threshold_edit_finished)
        self.threshold_value_edit.editingFinished.connect(self.on_threshold_edit_finished)
        slider_layout.addWidget(self.threshold_value_edit)

        # 加号按钮
        self.threshold_plus_btn = QToolButton()
        self.threshold_plus_btn.setText("+")
        self.threshold_plus_btn.setFixedSize(16, 16)
        self.threshold_plus_btn.setStyleSheet("""
            QToolButton {
                background-color: #34495e;
                color: #ecf0f1;
                border: 1px solid #2c3e50;
                border-radius: 2px;
                font-size: 13px;
                font-weight: bold;
                padding: 0px;
                margin: 0px;
            }
            QToolButton:hover { background-color: #3d566e; }
            QToolButton:pressed { background-color: #2c3e50; }
            QToolButton:disabled { background-color: #2c3e50; color: #7f8c8d; }
        """)
        self.threshold_plus_btn.clicked.connect(self.on_threshold_plus)
        slider_layout.addWidget(self.threshold_plus_btn)

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
        self.shortcut_list.setTextElideMode(Qt.ElideRight)
        self.shortcut_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.shortcut_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.shortcut_list.setFocusPolicy(Qt.NoFocus)
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
        self.duplicate_list.setTextElideMode(Qt.ElideRight)
        self.duplicate_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.duplicate_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.duplicate_list.setFocusPolicy(Qt.NoFocus)
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

        # 按钮区：两行布局，每行两个等宽按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 第一行：全选 + 取消
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)

        select_all_btn = QPushButton("全选")
        select_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        select_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #3498db;
                border: 1px solid #2980b9;
                border-radius: 3px;
                color: white;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2980b9;
            }
            QPushButton:pressed {
                background-color: #1a5276;
            }
        """)
        select_all_btn.clicked.connect(self.select_all_duplicates)
        row1_layout.addWidget(select_all_btn)

        deselect_all_btn = QPushButton("取消")
        deselect_all_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        deselect_all_btn.setStyleSheet("""
            QPushButton {
                background-color: #7f8c8d;
                border: 1px solid #707b7c;
                border-radius: 3px;
                color: white;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #95a5a6;
            }
            QPushButton:pressed {
                background-color: #566573;
            }
        """)
        deselect_all_btn.clicked.connect(self.deselect_all_duplicates)
        row1_layout.addWidget(deselect_all_btn)

        btn_layout.addLayout(row1_layout)

        # 第二行：查看 + 删除
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)

        view_btn = QPushButton("查看")
        view_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        view_btn.setStyleSheet("""
            QPushButton {
                background-color: #9b59b6;
                border: 1px solid #8e44ad;
                border-radius: 3px;
                color: white;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #8e44ad;
            }
            QPushButton:pressed {
                background-color: #6c3483;
            }
        """)
        view_btn.clicked.connect(self.show_duplicate_detail)
        row2_layout.addWidget(view_btn)

        delete_btn = QPushButton("删除")
        delete_btn.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        delete_btn.setStyleSheet("""
            QPushButton {
                background-color: #e74c3c;
                border: 1px solid #c0392b;
                border-radius: 3px;
                color: white;
                padding: 5px 8px;
                font-size: 12px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #c0392b;
            }
            QPushButton:pressed {
                background-color: #922b21;
            }
        """)
        delete_btn.clicked.connect(self.delete_selected_duplicates)
        row2_layout.addWidget(delete_btn)

        btn_layout.addLayout(row2_layout)

        layout.addLayout(btn_layout)
        return group

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet("""
            QLabel {
                background-color: #1a1a1a;
                border: 2px solid #34495e;
                border-radius: 6px;
            }
        """)
        self.image_label.setMinimumHeight(300)
        layout.addWidget(self.image_label, 1)

        info_layout = QHBoxLayout()
        info_layout.setSpacing(16)
        info_layout.setContentsMargins(4, 0, 4, 0)

        self.group_info_label = QLabel("组: /")
        self.group_info_label.setStyleSheet("color: #3498db; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.group_info_label)

        self.image_info_label = QLabel("图片: /")
        self.image_info_label.setStyleSheet("color: #9b59b6; font-weight: bold; font-size: 13px;")
        info_layout.addWidget(self.image_info_label)

        self.path_label = QLineEdit()
        self.path_label.setStyleSheet("""
            QLineEdit {
                background-color: transparent;
                color: #7f8c8d;
                font-size: 12px;
                border: none;
                border-bottom: 1px solid transparent;
                padding: 0px;
            }
            QLineEdit:hover {
                border-bottom: 1px solid #34495e;
            }
            QLineEdit:focus {
                border-bottom: 1px solid #3498db;
                color: #ecf0f1;
                background-color: #1e1e1e;
            }
        """)
        self.path_label.setReadOnly(False)
        self.path_label.setCursorPosition(0)
        self.path_label.returnPressed.connect(self.on_filename_edited)
        self.path_label.editingFinished.connect(self.on_filename_editing_finished)
        info_layout.addWidget(self.path_label, 1)

        layout.addLayout(info_layout)

        nav_layout = self._create_navigation_layout()
        layout.addLayout(nav_layout)

        return panel

    def _create_navigation_layout(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        view_layout = QHBoxLayout()
        view_layout.setSpacing(6)

        rotate_180_ccw_btn = QPushButton("↻ 180°逆 (Ctrl+↑)")
        rotate_180_ccw_btn.clicked.connect(lambda: self.rotate_image(False, 180))
        rotate_180_ccw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        view_layout.addWidget(rotate_180_ccw_btn)

        rotate_ccw_btn = QPushButton("↻ 90°逆 (Ctrl+←)")
        rotate_ccw_btn.clicked.connect(lambda: self.rotate_image(False))
        rotate_ccw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        view_layout.addWidget(rotate_ccw_btn)

        rotate_cw_btn = QPushButton("↺ 90°顺 (Ctrl+→)")
        rotate_cw_btn.clicked.connect(lambda: self.rotate_image(True))
        rotate_cw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        view_layout.addWidget(rotate_cw_btn)

        rotate_180_cw_btn = QPushButton("↺ 180°顺 (Ctrl+↓)")
        rotate_180_cw_btn.clicked.connect(lambda: self.rotate_image(True, 180))
        rotate_180_cw_btn.setStyleSheet("""
            QPushButton {
                background-color: #34495e;
                border: 1px solid #2c3e50;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ecf0f1;
            }
            QPushButton:hover {
                background-color: #3d566e;
            }
            QPushButton:pressed {
                background-color: #2c3e50;
            }
        """)
        view_layout.addWidget(rotate_180_cw_btn)

        layout.addLayout(view_layout)

        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(6)

        prev_group_btn = QPushButton("上一组 (↑)")
        prev_group_btn.setShortcut("Up")
        prev_group_btn.clicked.connect(self.prev_group)
        prev_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: 1px solid #1e8449;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        switch_layout.addWidget(prev_group_btn)

        prev_img_btn = QPushButton("上一张 (←)")
        prev_img_btn.setShortcut("Left")
        prev_img_btn.clicked.connect(self.prev_image)
        prev_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: 1px solid #1e8449;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        switch_layout.addWidget(prev_img_btn)

        next_img_btn = QPushButton("下一张 (→)")
        next_img_btn.setShortcut("Right")
        next_img_btn.clicked.connect(self.next_image)
        next_img_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: 1px solid #1e8449;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
            }
        """)
        switch_layout.addWidget(next_img_btn)

        next_group_btn = QPushButton("下一组 (↓)")
        next_group_btn.setShortcut("Down")
        next_group_btn.clicked.connect(self.next_group)
        next_group_btn.setStyleSheet("""
            QPushButton {
                background-color: #27ae60;
                border: 1px solid #1e8449;
                border-radius: 5px;
                padding: 7px 10px;
                font-size: 12px;
                color: #ffffff;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #2ecc71;
            }
            QPushButton:pressed {
                background-color: #1e8449;
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

    def keyPressEvent(self, event: QKeyEvent):
        """捕获按键，匹配快捷键映射触发分类。

        当文件名输入框或阈值输入框有焦点时不拦截，保证正常编辑。
        修饰键单独按下（Ctrl/Shift/Alt）不触发分类。
        """
        # 输入框聚焦时放行，避免编辑文件名/阈值时误触发分类
        if self.path_label.hasFocus() or self.threshold_value_edit.hasFocus():
            super().keyPressEvent(event)
            return

        key = event.key()
        # 忽略纯修饰键
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            super().keyPressEvent(event)
            return

        key_str = key_to_string(key)
        if not key_str:
            super().keyPressEvent(event)
            return

        key_str = key_str.lower()
        shortcuts = self.presenter.get_shortcuts()
        if key_str in shortcuts:
            debug_manager.log_info('快捷键触发分类', 'shortcut', key=key_str)
            self.presenter.classify_image(key_str)
            event.accept()
        else:
            super().keyPressEvent(event)

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

        # 仅显示文件名；用户正在编辑时不覆盖
        filename = os.path.basename(current_path)
        if not self.path_label.hasFocus():
            self.path_label.setText(filename)
            self.path_label.setCursorPosition(0)

        try:
            # 从 LRU 缓存读取原图，避免重复磁盘解码
            if current_path in self._image_cache:
                pixmap = self._image_cache.pop(current_path)
                self._image_cache[current_path] = pixmap
            else:
                pixmap = QPixmap(current_path)
                if pixmap.isNull():
                    self.image_label.setText("无法加载图片")
                    return
                # 缓存原图
                self._image_cache[current_path] = pixmap
                if len(self._image_cache) > self._image_cache_max:
                    self._image_cache.popitem(last=False)

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

    def on_filename_edited(self):
        """用户在文件名输入框按 Enter 时触发重命名。"""
        new_filename = self.path_label.text().strip()
        if not new_filename:
            # 空文件名：恢复原文件名
            current_path = self.presenter.get_current_image_path()
            if current_path:
                self.path_label.setText(os.path.basename(current_path))
            return
        success, message = self.presenter.rename_current_image(new_filename)
        if success:
            self.set_status(f"已重命名: {message}")
            # 重命名成功后光标移到开头
            self.path_label.setCursorPosition(0)
            # 清除焦点，确保后续快捷键能正常触发
            self.path_label.clearFocus()
        else:
            self.set_status(f"重命名失败: {message}")
            # 失败时恢复原文件名
            current_path = self.presenter.get_current_image_path()
            if current_path:
                self.path_label.setText(os.path.basename(current_path))

    def on_filename_editing_finished(self):
        """文件名输入框失去焦点时：若内容未变则什么都不做。

        实际重命名仅在 Enter 时触发（on_filename_edited），
        避免点击其他地方时意外触发重命名。
        """
        current_path = self.presenter.get_current_image_path()
        if not current_path:
            return
        current_filename = os.path.basename(current_path)
        if self.path_label.text() != current_filename:
            # 内容有变化但用户没按 Enter，提示一下但不自动执行
            # 将光标移到开头便于查看完整文件名
            self.path_label.setCursorPosition(0)

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
        self.threshold_value_edit.setText(str(threshold))

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
        # 最小化时显示恢复按钮，恢复时隐藏
        self.hash_dialog.minimization_changed.connect(self.on_hash_dialog_minimized)
        self.hash_dialog.show()

    def on_hash_dialog_minimized(self, minimized: bool):
        """哈希分析弹窗最小化/恢复时切换恢复按钮的可见性。"""
        self.restore_hash_dialog_btn.setVisible(minimized)
        if minimized:
            self.set_status("哈希分析已最小化，点击右侧「恢复分析」重新展开")

    def restore_hash_dialog(self):
        """恢复最小化的哈希分析弹窗。"""
        if hasattr(self, 'hash_dialog') and self.hash_dialog and self.hash_dialog.isVisible():
            self.hash_dialog.setWindowState(self.hash_dialog.windowState() & ~Qt.WindowMinimized)
            self.hash_dialog.raise_()
            self.hash_dialog.activateWindow()
            self.restore_hash_dialog_btn.setVisible(False)

    def sync_hash_dialog_threshold(self, threshold: int):
        """将主界面的阈值同步到正在显示的哈希分析弹窗。

        阻塞弹窗滑块的 valueChanged 信号，避免反向触发 threshold_changed
        造成主界面与弹窗之间的循环同步。
        """
        if hasattr(self, 'hash_dialog') and self.hash_dialog and self.hash_dialog.isVisible():
            self.hash_dialog.sync_threshold(threshold)

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
        # 输入框有焦点时（用户正在编辑）不覆盖其文本，避免干扰输入
        if not self.threshold_value_edit.hasFocus():
            self.threshold_value_edit.setText(str(threshold))
        self._pending_threshold = threshold
        self._threshold_timer.start()

    def _apply_threshold(self):
        """防抖超时后执行：调用 Presenter 进行重分组等重量级操作。"""
        if self._pending_threshold is not None:
            threshold = self._pending_threshold
            self._pending_threshold = None
            self.presenter.on_threshold_changed(threshold)

    def on_threshold_minus(self):
        """减号按钮：阈值减 1（下限 2）。通过设置滑块值触发统一变更流程。"""
        new_val = max(2, self.threshold_slider.value() - 1)
        self.threshold_slider.setValue(new_val)

    def on_threshold_plus(self):
        """加号按钮：阈值加 1（上限 25）。通过设置滑块值触发统一变更流程。"""
        new_val = min(25, self.threshold_slider.value() + 1)
        self.threshold_slider.setValue(new_val)

    def on_threshold_edit_finished(self):
        """输入框编辑完成（Enter 或失去焦点）：验证输入并同步滑块。

        无效输入（非数字、超出范围）会被校正到最近的合法值。
        通过设置滑块值触发 valueChanged，走统一的防抖变更流程。
        """
        text = self.threshold_value_edit.text().strip()
        try:
            val = int(text)
        except ValueError:
            val = self.threshold_slider.value()
        # 校正到合法范围
        val = max(2, min(25, val))
        # 同步输入框显示为校正后的值
        self.threshold_value_edit.setText(str(val))
        # 若与当前滑块值不同则更新滑块，触发防抖变更流程
        if val != self.threshold_slider.value():
            self.threshold_slider.setValue(val)
        # 清除焦点，确保后续快捷键能正常触发
        self.threshold_value_edit.clearFocus()

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
        # 分类后清除已移动图片的缓存
        if old_path in self._image_cache:
            del self._image_cache[old_path]

    def invalidate_image_cache(self, path: str = None):
        """清除图片缓存。若指定路径则只清除该路径，否则清除全部。"""
        if path:
            if path in self._image_cache:
                del self._image_cache[path]
        else:
            self._image_cache.clear()

    def refresh_groups(self):
        self.show_current_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_current_image()
