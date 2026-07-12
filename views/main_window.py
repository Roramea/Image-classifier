import os

from PyQt5.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QMessageBox, QLineEdit, QToolButton,
    QListWidget, QListWidgetItem, QScrollArea, QSplitter,
    QGroupBox, QComboBox, QSlider, QShortcut, QSizePolicy,
    QDialog
)
from PyQt5.QtGui import QPixmap, QFont, QTransform, QKeySequence, QColor, QKeyEvent
from PyQt5.QtCore import Qt, QSize, QEvent

from dialogs.duplicate_detail_dialog import DuplicateDetailDialog
from dialogs.storage_clean_dialog import StorageCleanDialog
from dialogs.folder_select_dialog import FolderSelectDialog
from dialogs.shortcut_input_dialog import ShortcutInputDialog
from dialogs.hash_analysis_dialog import HashAnalysisDialog
from dialogs.settings_dialog import SettingsDialog
from core.debug_manager import debug_manager
from core.utils import key_to_string
from core.theme_manager import theme_manager
from views.i_main_view import IMainView
from widgets.scrolling_label import ScrollingLabel


class MainWindow(QMainWindow, IMainView):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("图片分类器")
        self.setGeometry(100, 100, 1200, 800)

        from presenters.main_presenter import MainPresenter
        self.presenter = MainPresenter(self)
        self.init_ui()
        self.connect_signals()
        self.presenter.load_initial_data()

        if hasattr(self, 'undo_btn'):
            self.undo_btn.setEnabled(False)

        theme_manager.theme_changed.connect(self.on_theme_changed)

        debug_manager.log_info('主窗口初始化完成', 'main')

    def closeEvent(self, event):
        """应用关闭时通知 Presenter 保存未完成会话等清理工作。"""
        self.presenter.on_app_close()
        super().closeEvent(event)

    def on_theme_changed(self, colors):
        """主题变化时重新应用样式。"""
        self._apply_theme()
        self.status_label.setStyleSheet(f"color: {colors.text_secondary}; font-size: 12px;")

    def _create_button_style(self, bg_color, border_color, hover_color,
                             pressed_color, text_color, font_weight="normal",
                             padding="6px 12px", font_size="12px",
                             disabled_bg=None, disabled_text=None,
                             border_radius="5px", border_style="1px solid") -> str:
        c = theme_manager.colors
        disabled_bg = disabled_bg if disabled_bg is not None else border_color
        disabled_text = disabled_text if disabled_text is not None else c.text_disabled
        return f"""
            QPushButton {{
                background-color: {bg_color};
                border: {border_style} {border_color};
                border-radius: {border_radius};
                padding: {padding};
                font-size: {font_size};
                color: {text_color};
                font-weight: {font_weight};
            }}
            QPushButton:hover {{
                background-color: {hover_color};
            }}
            QPushButton:pressed {{
                background-color: {pressed_color};
            }}
            QPushButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
                border-color: {disabled_bg};
            }}
        """

    def _create_tool_button_style(self, bg_color, border_color, hover_color,
                                   pressed_color, text_color, font_weight="normal",
                                   padding="2px 8px", font_size="11px",
                                   disabled_bg=None, disabled_text=None,
                                   border_radius="3px", border_style="1px solid",
                                   min_width="", min_height="") -> str:
        c = theme_manager.colors
        disabled_bg = disabled_bg if disabled_bg is not None else border_color
        disabled_text = disabled_text if disabled_text is not None else c.text_disabled
        min_width_style = f"min-width: {min_width};" if min_width else ""
        min_height_style = f"min-height: {min_height};" if min_height else ""
        return f"""
            QToolButton {{
                background-color: {bg_color};
                border: {border_style} {border_color};
                border-radius: {border_radius};
                padding: {padding};
                font-size: {font_size};
                color: {text_color};
                font-weight: {font_weight};
                {min_width_style}
                {min_height_style}
            }}
            QToolButton:hover {{
                background-color: {hover_color};
            }}
            QToolButton:pressed {{
                background-color: {pressed_color};
            }}
            QToolButton:disabled {{
                background-color: {disabled_bg};
                color: {disabled_text};
                border-color: {disabled_bg};
            }}
        """

    def _create_line_edit_style(self, bg_color, text_color, border_color,
                                 accent_color, font_weight="normal",
                                 padding="0px", font_size="12px") -> str:
        return f"""
            QLineEdit {{
                background-color: {bg_color};
                color: {text_color};
                font-weight: {font_weight};
                border: 1px solid {border_color};
                border-radius: 2px;
                padding: {padding};
                font-size: {font_size};
            }}
            QLineEdit:focus {{ border: 1px solid {accent_color}; }}
        """

    def _create_button(self, text, callback,
                       bg_color=None, border_color=None,
                       hover_color=None, pressed_color=None,
                       text_color=None, font_weight="normal",
                       padding="6px 12px", font_size="12px",
                       disabled_bg=None, disabled_text=None,
                       border_radius="5px", border_style="1px solid",
                       shortcut=None, tooltip=None, enabled=True,
                       size_policy=None) -> QPushButton:
        c = theme_manager.colors
        btn = QPushButton(text)
        btn.clicked.connect(callback)

        if shortcut:
            btn.setShortcut(shortcut)
        if tooltip:
            btn.setToolTip(tooltip)
        btn.setEnabled(enabled)

        if size_policy:
            btn.setSizePolicy(*size_policy)

        btn.setStyleSheet(self._create_button_style(
            bg_color=bg_color or c.button_bg,
            border_color=border_color or c.button_border,
            hover_color=hover_color or c.button_hover,
            pressed_color=pressed_color or c.button_pressed,
            text_color=text_color or c.text_primary,
            font_weight=font_weight,
            padding=padding,
            font_size=font_size,
            disabled_bg=disabled_bg,
            disabled_text=disabled_text,
            border_radius=border_radius,
            border_style=border_style
        ))

        return btn

    def _create_tool_button(self, text, callback,
                            bg_color=None, border_color=None,
                            hover_color=None, pressed_color=None,
                            text_color=None, font_weight="normal",
                            padding="2px 8px", font_size="11px",
                            disabled_bg=None, disabled_text=None,
                            border_radius="3px", border_style="1px solid",
                            min_width="", min_height="",
                            tooltip=None, enabled=True,
                            fixed_size=None, auto_raise=True) -> QToolButton:
        c = theme_manager.colors
        btn = QToolButton()
        btn.setText(text)
        btn.clicked.connect(callback)

        if tooltip:
            btn.setToolTip(tooltip)
        btn.setEnabled(enabled)
        btn.setAutoRaise(auto_raise)

        if fixed_size:
            btn.setFixedSize(*fixed_size)

        btn.setStyleSheet(self._create_tool_button_style(
            bg_color=bg_color or c.button_bg,
            border_color=border_color or c.button_border,
            hover_color=hover_color or c.button_hover,
            pressed_color=pressed_color or c.button_pressed,
            text_color=text_color or c.text_primary,
            font_weight=font_weight,
            padding=padding,
            font_size=font_size,
            disabled_bg=disabled_bg,
            disabled_text=disabled_text,
            border_radius=border_radius,
            border_style=border_style,
            min_width=min_width,
            min_height=min_height
        ))

        return btn

    def init_ui(self):
        self._apply_theme()

    def _apply_theme(self):
        c = theme_manager.colors
        stylesheet = f"""
            QMainWindow {{
                background-color: {c.window_bg};
            }}
            QWidget {{
                background-color: {c.widget_bg};
                color: {c.text_primary};
            }}
            QGroupBox {{
                font-weight: bold;
                color: {c.text_primary};
                border: 1px solid {c.group_box_border};
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 15px;
            }}
            QGroupBox::title {{
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
                color: {c.group_box_title};
            }}
            QPushButton {{
                background-color: {c.button_bg};
                color: {c.text_primary};
                border: 1px solid {c.button_border};
                border-radius: 3px;
                padding: 6px 12px;
                min-width: 80px;
            }}
            QPushButton:hover {{
                background-color: {c.button_hover};
            }}
            QPushButton:pressed {{
                background-color: {c.button_pressed};
            }}
            QLabel {{
                color: {c.text_primary};
            }}
            QComboBox {{
                background-color: {c.button_bg};
                color: {c.text_primary};
                border: 1px solid {c.button_border};
                border-radius: 3px;
                padding: 4px;
            }}
            QListWidget {{
                background-color: {c.list_bg};
                color: {c.text_primary};
                border: 1px solid {c.border_light};
                border-radius: 3px;
            }}
            QSlider::groove:horizontal {{
                height: 6px;
                background: {c.slider_groove};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {c.slider_handle};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QScrollArea {{
                border: none;
            }}
        """
        self.setStyleSheet(stylesheet)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QHBoxLayout(central_widget)

        left_panel = self._create_left_panel()
        right_panel = self._create_right_panel()

        c = theme_manager.colors
        splitter = QSplitter(Qt.Horizontal)
        splitter.setStyleSheet(f"QSplitter::handle {{ background-color: {c.border}; }}")
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

        c = theme_manager.colors
        select_btn = self._create_button(
            "选择图片文件夹", self.select_folder,
            bg_color=c.accent,
            border_color=c.accent_hover,
            hover_color=c.accent_hover,
            pressed_color=c.accent_dark,
            text_color="white",
            font_weight="bold"
        )
        layout.addWidget(select_btn)

        self.recent_combo = QComboBox()
        self.recent_combo.setPlaceholderText("最近分类的文件夹")
        self.recent_combo.setSizeAdjustPolicy(QComboBox.AdjustToMinimumContentsLengthWithIcon)
        self.recent_combo.setMinimumContentsLength(15)
        self.recent_combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.recent_combo.setFocusPolicy(Qt.NoFocus)
        layout.addWidget(self.recent_combo)

        status_container = QWidget()
        status_container_layout = QVBoxLayout(status_container)
        status_container_layout.setContentsMargins(0, 0, 0, 0)
        status_container_layout.setSpacing(2)

        c = theme_manager.colors
        self.status_label = ScrollingLabel()
        self.status_label.setText("请选择图片文件夹开始分类")
        self.status_label.setStyleSheet(f"color: {c.text_secondary}; font-size: 12px;")
        self.status_label.setScrollSpeed(30)
        self.status_label.setMinimumHeight(20)
        self.status_label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        status_container_layout.addWidget(self.status_label)

        # 最小化哈希分析弹窗后显示的恢复按钮，默认隐藏
        # 使用单独一行布局，避免挤压状态标签的显示空间
        c = theme_manager.colors
        self.restore_hash_dialog_btn = self._create_tool_button(
            "查看分析状态", self.restore_hash_dialog,
            bg_color=c.accent,
            border_color=c.accent,
            hover_color=c.accent_hover,
            pressed_color=c.accent_dark,
            text_color="white",
            padding="2px 8px",
            font_size="11px",
            border_style="none",
            auto_raise=False
        )
        self.restore_hash_dialog_btn.setVisible(False)
        status_container_layout.addWidget(self.restore_hash_dialog_btn)

        layout.addWidget(status_container)

        threshold_group = QGroupBox("相似度阈值")
        threshold_group.setVisible(True)
        self.threshold_group = threshold_group
        threshold_layout = QVBoxLayout(threshold_group)

        slider_layout = QHBoxLayout()
        slider_layout.setSpacing(2)
        c = theme_manager.colors
        slider_label = QLabel("阈值:")
        slider_label.setStyleSheet(f"color: {c.accent};")
        slider_layout.addWidget(slider_label)

        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setRange(2, 25)
        self.threshold_slider.setValue(10)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        slider_layout.addWidget(self.threshold_slider)

        c = theme_manager.colors
        self.threshold_minus_btn = self._create_tool_button(
            "−", self.on_threshold_minus,
            bg_color=c.button_bg,
            border_color=c.button_border,
            hover_color=c.button_hover,
            pressed_color=c.button_pressed,
            text_color=c.text_primary,
            font_weight="bold",
            padding="0px",
            font_size="13px",
            disabled_bg=c.button_pressed,
            disabled_text=c.text_disabled,
            fixed_size=(16, 16),
            auto_raise=False
        )
        slider_layout.addWidget(self.threshold_minus_btn)

        self.threshold_value_edit = QLineEdit("10")
        self.threshold_value_edit.setFixedWidth(30)
        self.threshold_value_edit.setAlignment(Qt.AlignCenter)
        self.threshold_value_edit.setMaxLength(2)
        self.threshold_value_edit.setStyleSheet(self._create_line_edit_style(
            bg_color=c.input_bg,
            text_color=c.accent,
            border_color=c.border_light,
            accent_color=c.accent,
            font_weight="bold",
            padding="0px",
            font_size="12px"
        ))
        self.threshold_value_edit.returnPressed.connect(self.on_threshold_edit_finished)
        self.threshold_value_edit.editingFinished.connect(self.on_threshold_edit_finished)
        slider_layout.addWidget(self.threshold_value_edit)

        self.threshold_plus_btn = self._create_tool_button(
            "+", self.on_threshold_plus,
            bg_color=c.button_bg,
            border_color=c.button_border,
            hover_color=c.button_hover,
            pressed_color=c.button_pressed,
            text_color=c.text_primary,
            font_weight="bold",
            padding="0px",
            font_size="13px",
            disabled_bg=c.button_pressed,
            disabled_text=c.text_disabled,
            fixed_size=(16, 16),
            auto_raise=False
        )
        slider_layout.addWidget(self.threshold_plus_btn)

        threshold_layout.addLayout(slider_layout)

        c = theme_manager.colors
        threshold_tip = QLabel("阈值越小，相似度要求越高 (2-25)")
        threshold_tip.setStyleSheet(f"color: {c.text_hint}; font-size: 11px;")
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

        add_shortcut_btn = self._create_button("添加快捷键", self.add_shortcut)
        shortcut_layout.addWidget(add_shortcut_btn)

        del_shortcut_btn = self._create_button("删除快捷键", self.remove_shortcut)
        shortcut_layout.addWidget(del_shortcut_btn)

        layout.addWidget(shortcut_group)

        duplicate_group = self._create_duplicate_group()
        layout.addWidget(duplicate_group)

        c = theme_manager.colors
        storage_btn = self._create_button(
            "清除存储占用", self.clear_storage,
            bg_color=c.danger,
            border_color=c.danger_pressed,
            hover_color=c.danger_hover,
            pressed_color=c.danger_pressed,
            text_color="white"
        )
        layout.addWidget(storage_btn)

        settings_btn = self._create_button("设置", self.show_settings)
        layout.addWidget(settings_btn)

        return panel

    def _create_duplicate_group(self):
        group = QGroupBox("重复图片")
        group.setVisible(True)
        self.duplicate_group = group
        layout = QVBoxLayout(group)
        layout.setSpacing(6)
        layout.setContentsMargins(6, 6, 6, 6)

        c = theme_manager.colors
        self.duplicate_list = QListWidget()
        self.duplicate_list.setMinimumHeight(100)
        self.duplicate_list.setMaximumHeight(180)
        self.duplicate_list.setTextElideMode(Qt.ElideRight)
        self.duplicate_list.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.duplicate_list.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.duplicate_list.setFocusPolicy(Qt.NoFocus)
        self.duplicate_list.setStyleSheet(f"""
            QListWidget {{
                background-color: {c.list_bg};
                border: 1px solid {c.border};
                border-radius: 3px;
                color: {c.text_primary};
                font-size: 13px;
            }}
            QListWidget::item {{
                padding: 5px 8px;
                border-bottom: 1px solid {c.border_light};
                height: 32px;
            }}
            QListWidget::item:alternate {{
                background-color: {c.item_alternate};
            }}
            QListWidget::item:hover {{
                background-color: {c.item_hover};
            }}
            QListWidget::item:selected {{
                background-color: {c.item_selected};
                color: {c.text_primary};
            }}
        """)
        self.duplicate_list.itemClicked.connect(self.on_duplicate_item_clicked)
        layout.addWidget(self.duplicate_list)

        # 按钮区：两行布局，每行两个等宽按钮
        btn_layout = QVBoxLayout()
        btn_layout.setSpacing(4)

        # 第一行：全选 + 取消
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(4)

        c = theme_manager.colors
        select_all_btn = self._create_button(
            "全选", self.select_all_duplicates,
            bg_color=c.accent,
            border_color=c.accent_hover,
            hover_color=c.accent_hover,
            pressed_color=c.accent_dark,
            text_color="white",
            font_weight="bold",
            padding="5px 8px",
            border_radius="3px",
            size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        row1_layout.addWidget(select_all_btn)

        deselect_all_btn = self._create_button(
            "取消", self.deselect_all_duplicates,
            bg_color=c.neutral,
            border_color=c.neutral_pressed,
            hover_color=c.neutral_hover,
            pressed_color=c.neutral_pressed,
            text_color="white",
            font_weight="bold",
            padding="5px 8px",
            border_radius="3px",
            size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        row1_layout.addWidget(deselect_all_btn)

        btn_layout.addLayout(row1_layout)

        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(4)

        view_btn = self._create_button(
            "查看", self.show_duplicate_detail,
            bg_color=c.info,
            border_color=c.info_hover,
            hover_color=c.info_hover,
            pressed_color=c.info_pressed,
            text_color="white",
            font_weight="bold",
            padding="5px 8px",
            border_radius="3px",
            size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        row2_layout.addWidget(view_btn)

        delete_btn = self._create_button(
            "删除", self.delete_selected_duplicates,
            bg_color=c.danger,
            border_color=c.danger_pressed,
            hover_color=c.danger_hover,
            pressed_color=c.danger_pressed,
            text_color="white",
            font_weight="bold",
            padding="5px 8px",
            border_radius="3px",
            size_policy=(QSizePolicy.Expanding, QSizePolicy.Fixed)
        )
        row2_layout.addWidget(delete_btn)

        btn_layout.addLayout(row2_layout)

        layout.addLayout(btn_layout)
        return group

    def _create_right_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setSpacing(12)

        c = theme_manager.colors
        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignCenter)
        self.image_label.setStyleSheet(f"""
            QLabel {{
                background-color: {c.image_bg};
                border: 2px solid {c.border};
                border-radius: 6px;
            }}
        """)
        self.image_label.setMinimumHeight(300)
        layout.addWidget(self.image_label, 1)

        self.info_layout = QHBoxLayout()
        self.info_layout.setSpacing(16)
        self.info_layout.setContentsMargins(4, 0, 4, 0)

        c = theme_manager.colors
        self.group_info_label = QLabel("组: /")
        self.group_info_label.setStyleSheet(f"color: {c.accent}; font-weight: bold; font-size: 13px;")
        self.info_layout.addWidget(self.group_info_label)

        c = theme_manager.colors
        self.image_info_label = QLabel("图片: /")
        self.image_info_label.setStyleSheet(f"color: {c.info}; font-weight: bold; font-size: 13px;")
        self.info_layout.addWidget(self.image_info_label)

        c = theme_manager.colors
        self.path_label = QLineEdit()
        self.path_label.setStyleSheet(f"""
            QLineEdit {{
                background-color: transparent;
                color: {c.text_hint};
                font-size: 12px;
                border: none;
                border-bottom: 1px solid transparent;
                padding: 0px;
            }}
            QLineEdit:hover {{
                border-bottom: 1px solid {c.border};
            }}
            QLineEdit:focus {{
                border-bottom: 1px solid {c.accent};
                color: {c.text_primary};
                background-color: {c.list_bg};
            }}
        """)
        self.path_label.setReadOnly(False)
        self.path_label.setCursorPosition(0)
        self.path_label.returnPressed.connect(self.on_filename_edited)
        self.path_label.editingFinished.connect(self.on_filename_editing_finished)
        self.path_label.textChanged.connect(self.on_path_label_text_changed)
        self.path_label.installEventFilter(self)

        c = theme_manager.colors
        self.cancel_rename_btn = self._create_tool_button(
            "✕", self.on_cancel_rename,
            bg_color=c.danger,
            border_color=c.danger,
            hover_color=c.danger_hover,
            pressed_color=c.danger_pressed,
            text_color="white",
            padding="2px 8px",
            font_size="12px",
            border_style="none",
            min_width="24px",
            min_height="20px",
            auto_raise=False
        )
        self.cancel_rename_btn.hide()
        

        self.path_container = QWidget()
        self.path_container_layout = QHBoxLayout(self.path_container)
        self.path_container_layout.setSpacing(4)
        self.path_container_layout.setContentsMargins(0, 0, 0, 0)
        self.path_container_layout.addWidget(self.path_label, 1)
        self.path_container_layout.addWidget(self.cancel_rename_btn)
        
        self.info_layout.addWidget(self.path_container, 1)

        layout.addLayout(self.info_layout)

        nav_layout = self._create_navigation_layout()
        layout.addLayout(nav_layout)

        return panel

    def _create_navigation_layout(self):
        layout = QVBoxLayout()
        layout.setSpacing(8)

        view_layout = QHBoxLayout()
        view_layout.setSpacing(6)

        c = theme_manager.colors
        rotate_180_ccw_btn = self._create_button(
            "↻ 180°逆 (Ctrl+↑)", lambda: self.rotate_image(False, 180),
            padding="7px 10px"
        )
        view_layout.addWidget(rotate_180_ccw_btn)

        rotate_ccw_btn = self._create_button(
            "↻ 90°逆 (Ctrl+←)", lambda: self.rotate_image(False),
            padding="7px 10px"
        )
        view_layout.addWidget(rotate_ccw_btn)

        rotate_cw_btn = self._create_button(
            "↺ 90°顺 (Ctrl+→)", lambda: self.rotate_image(True),
            padding="7px 10px"
        )
        view_layout.addWidget(rotate_cw_btn)

        rotate_180_cw_btn = self._create_button(
            "↺ 180°顺 (Ctrl+↓)", lambda: self.rotate_image(True, 180),
            padding="7px 10px"
        )
        view_layout.addWidget(rotate_180_cw_btn)

        layout.addLayout(view_layout)

        switch_layout = QHBoxLayout()
        switch_layout.setSpacing(6)

        prev_group_btn = self._create_button(
            "上一组 (↑)", self.prev_group,
            bg_color=c.success,
            border_color=c.success_pressed,
            hover_color=c.success_hover,
            pressed_color=c.success_pressed,
            text_color=c.text_on_accent,
            font_weight="bold",
            padding="7px 10px",
            shortcut="Up"
        )
        switch_layout.addWidget(prev_group_btn)

        prev_img_btn = self._create_button(
            "上一张 (←)", self.prev_image,
            bg_color=c.success,
            border_color=c.success_pressed,
            hover_color=c.success_hover,
            pressed_color=c.success_pressed,
            text_color=c.text_on_accent,
            font_weight="bold",
            padding="7px 10px",
            shortcut="Left"
        )
        switch_layout.addWidget(prev_img_btn)

        next_img_btn = self._create_button(
            "下一张 (→)", self.next_image,
            bg_color=c.success,
            border_color=c.success_pressed,
            hover_color=c.success_hover,
            pressed_color=c.success_pressed,
            text_color=c.text_on_accent,
            font_weight="bold",
            padding="7px 10px",
            shortcut="Right"
        )
        switch_layout.addWidget(next_img_btn)

        next_group_btn = self._create_button(
            "下一组 (↓)", self.next_group,
            bg_color=c.success,
            border_color=c.success_pressed,
            hover_color=c.success_hover,
            pressed_color=c.success_pressed,
            text_color=c.text_on_accent,
            font_weight="bold",
            padding="7px 10px",
            shortcut="Down"
        )
        switch_layout.addWidget(next_group_btn)

        self.undo_btn = self._create_button(
            "撤回 (Ctrl+Z)", self.undo_classify,
            bg_color=c.warning,
            border_color=c.warning_pressed,
            hover_color=c.warning_hover,
            pressed_color=c.warning_pressed,
            text_color=c.text_on_accent,
            font_weight="bold",
            padding="7px 10px",
            disabled_bg=c.text_disabled,
            disabled_text=c.text_primary,
            shortcut="Ctrl+Z",
            tooltip="当前无可撤回的操作",
            enabled=False
        )
        switch_layout.addWidget(self.undo_btn)

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

        self.shortcut_escape = QShortcut(QKeySequence(Qt.Key_Escape), self)
        self.shortcut_escape.setContext(Qt.ApplicationShortcut)
        self.shortcut_escape.activated.connect(self.on_escape_pressed)

    def eventFilter(self, obj, event):
        """事件过滤器：处理 path_label 的鼠标点击事件。"""
        if obj == self.path_label:
            if event.type() == QEvent.MouseButtonPress:
                debug_manager.log_info('path_label鼠标点击', 'rename', is_read_only=self.path_label.isReadOnly())
                if self.path_label.isReadOnly():
                    self.path_label.setReadOnly(False)
                    self.path_label.setFocus()
                    self.cancel_rename_btn.show()
                    return True
        return super().eventFilter(obj, event)

    def keyPressEvent(self, event: QKeyEvent):
        """捕获按键，委托给 Presenter 处理快捷键映射。

        当文件名输入框或阈值输入框有焦点时不拦截，保证正常编辑。
        修饰键单独按下（Ctrl/Shift/Alt）不触发分类。
        """
        if self.path_label.hasFocus() or self.threshold_value_edit.hasFocus():
            super().keyPressEvent(event)
            return

        key = event.key()
        if key in (Qt.Key_Control, Qt.Key_Shift, Qt.Key_Alt, Qt.Key_Meta):
            super().keyPressEvent(event)
            return

        key_str = key_to_string(key)
        if not key_str:
            super().keyPressEvent(event)
            return

        key_str = key_str.lower()
        if self.presenter.handle_key_press(key_str):
            event.accept()
        else:
            super().keyPressEvent(event)

    def show_current_image(self):
        current_path = self.presenter.get_current_image_path()
        debug_manager.log_info('show_current_image', 'image', 
                              current_path=current_path,
                              path_exists=os.path.exists(current_path) if current_path else False)
        if not current_path or not os.path.exists(current_path):
            debug_manager.log_warning('show_current_image: 路径为空或不存在，尝试刷新', 'image')
            self.presenter.refresh_groups()
            current_path = self.presenter.get_current_image_path()
            debug_manager.log_info('show_current_image: 刷新后路径', 'image', 
                                  current_path=current_path,
                                  path_exists=os.path.exists(current_path) if current_path else False)
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

        filename = os.path.basename(current_path)
        filename_no_ext = os.path.splitext(filename)[0]
        if not self.path_label.hasFocus():
            self.path_label.setText(filename_no_ext)
            self.path_label.setCursorPosition(0)
            self.cancel_rename_btn.show()
            debug_manager.log_info('测试：强制显示取消按钮', 'rename', is_visible=self.cancel_rename_btn.isVisible())

        try:
            pixmap = self.presenter.get_image_from_cache(current_path)
            if pixmap is None:
                pixmap = QPixmap(current_path)
                if pixmap.isNull():
                    self.image_label.setText("无法加载图片")
                    return
                self.presenter.cache_image(current_path, pixmap)

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
            # 空文件名：恢复原文件名（不含扩展名）
            current_path = self.presenter.get_current_image_path()
            if current_path:
                filename = os.path.basename(current_path)
                filename_no_ext = os.path.splitext(filename)[0]
                self.path_label.setText(filename_no_ext)
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
            # 失败时恢复原文件名（不含扩展名）
            current_path = self.presenter.get_current_image_path()
            if current_path:
                filename = os.path.basename(current_path)
                filename_no_ext = os.path.splitext(filename)[0]
                self.path_label.setText(filename_no_ext)

    def on_filename_editing_finished(self):
        """文件名输入框失去焦点时：若内容有变化则恢复原始文件名。

        实际重命名仅在 Enter 时触发（on_filename_edited），
        避免点击其他地方时意外触发重命名。
        """
        current_path = self.presenter.get_current_image_path()
        if not current_path:
            return
        current_filename = os.path.basename(current_path)
        current_filename_no_ext = os.path.splitext(current_filename)[0]
        if self.path_label.text() != current_filename_no_ext:
            self.path_label.setText(current_filename_no_ext)
            self.path_label.setCursorPosition(0)

    def on_path_label_text_changed(self, text):
        """文件名输入框内容变化时：显示/隐藏取消按钮。"""
        debug_manager.log_info('on_path_label_text_changed触发', 'rename', text=text)
        
        current_path = self.presenter.get_current_image_path()
        debug_manager.log_info('当前图片路径', 'rename', current_path=current_path)
        
        if not current_path:
            debug_manager.log_info('当前路径为空，返回', 'rename')
            return
        
        original_filename = os.path.basename(current_path)
        original_filename_no_ext = os.path.splitext(original_filename)[0]
        debug_manager.log_info('原始文件名（不含扩展名）', 'rename', original_filename=original_filename_no_ext)
        
        if text != original_filename_no_ext:
            debug_manager.log_info('文件名有变化，显示取消按钮', 'rename')
            self.cancel_rename_btn.show()
            debug_manager.log_info('按钮显示状态', 'rename', is_visible=self.cancel_rename_btn.isVisible(), btn_geometry=self.cancel_rename_btn.geometry())
        else:
            debug_manager.log_info('文件名无变化，隐藏取消按钮', 'rename')
            self.cancel_rename_btn.hide()

    def on_escape_pressed(self):
        """ESC 键按下时：若 path_label 有焦点则取消重命名。"""
        debug_manager.log_info('ESC键按下', 'rename', path_label_has_focus=self.path_label.hasFocus())
        
        if self.path_label.hasFocus():
            debug_manager.log_info('path_label有焦点，触发取消重命名', 'rename')
            self.on_cancel_rename()

    def on_cancel_rename(self):
        """取消重命名，恢复原始文件名并设置为只读模式。"""
        debug_manager.log_info('取消重命名', 'rename')
        
        current_path = self.presenter.get_current_image_path()
        debug_manager.log_info('当前图片路径', 'rename', current_path=current_path)
        
        if current_path:
            original_filename = os.path.basename(current_path)
            original_filename_no_ext = os.path.splitext(original_filename)[0]
            debug_manager.log_info('恢复原始文件名（不含扩展名）', 'rename', original_filename=original_filename_no_ext)
            self.path_label.setText(original_filename_no_ext)
        else:
            debug_manager.log_info('当前路径为空，无法恢复文件名', 'rename')
        
        self.path_label.setReadOnly(True)
        self.path_label.clearFocus()
        self.set_status("")
        
        debug_manager.log_info('取消重命名完成', 'rename')

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
            item.setForeground(QColor(theme_manager.colors.text_disabled))
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
        # 对话框以任何方式关闭（完成/取消/出错）时，确保恢复按钮也被隐藏
        # 防止对话框处于隐藏态被 accept() 关闭时不触发 minimization_changed 信号
        self.hash_dialog.finished.connect(lambda: self.on_hash_dialog_minimized(False))
        self.hash_dialog.show()

    def on_hash_dialog_minimized(self, minimized: bool):
        """哈希分析弹窗最小化/恢复时切换恢复按钮的可见性。"""
        self.restore_hash_dialog_btn.setVisible(minimized)
        if minimized:
            self.set_status("后台分析相似度：计算图像哈希")

    def restore_hash_dialog(self):
        """恢复哈希分析弹窗（从隐藏状态显示，而非从系统最小化还原）。

        弹窗的最小化按钮已被重定义为「隐藏」，因此恢复时用 show() 显示窗口，
        同时确保窗口处于正常状态并提到前台。
        """
        if hasattr(self, 'hash_dialog') and self.hash_dialog:
            self.hash_dialog.show()
            self.hash_dialog.setWindowState(Qt.WindowNoState)
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
        """滑块值变化：立即更新数字显示（即时反馈），调用 Presenter 启动防抖。"""
        if not self.threshold_value_edit.hasFocus():
            self.threshold_value_edit.setText(str(threshold))
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

    def undo_classify(self):
        """撤回最后一次分类操作。"""
        self.presenter.undo_classify()
        self.update_undo_btn_state()

    def update_undo_btn_state(self):
        """更新撤回按钮的启用/禁用状态和提示信息。"""
        if hasattr(self, 'undo_btn'):
            has_history = self.presenter.has_undo_history()
            self.undo_btn.setEnabled(has_history)
            if has_history:
                self.undo_btn.setToolTip("撤回上一次分类操作<br>（最高记录10次，切换文件夹后记录清除）")
            else:
                self.undo_btn.setToolTip("当前无可撤回的操作<br>（执行分类后可撤回）")

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

    def show_settings(self):
        dialog = SettingsDialog(self)
        dialog.exec_()

    def on_image_classified(self, old_path, new_path):
        debug_manager.log_info('图片分类完成', 'classification', old_path=old_path, new_path=new_path)
        self.presenter.invalidate_image_cache(old_path)

    def invalidate_image_cache(self, path: str = None):
        """清除图片缓存。若指定路径则只清除该路径，否则清除全部。"""
        self.presenter.invalidate_image_cache(path)

    def refresh_groups(self):
        self.show_current_image()

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.show_current_image()


