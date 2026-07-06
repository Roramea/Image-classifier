import time

from PyQt5.QtWidgets import QDialog, QLabel, QProgressBar, QVBoxLayout, QWidget, QHBoxLayout, QSlider
from PyQt5.QtCore import Qt, QTimer, pyqtSignal, QEvent
from PyQt5.QtGui import QFont

from core.debug_manager import debug_manager
from core.theme_manager import theme_manager


class HashAnalysisDialog(QDialog):
    """哈希分析进度对话框。

    职责：展示分析进度、阶段、剩余时间；让用户调整阈值；接收取消请求。
    通过 Observer 模式订阅 hash_service 的事件更新进度（这是正确的解耦方向）；
    通过信号向 Presenter 上报用户操作（阈值调整、取消请求），不直接调用 service 的状态修改方法。

    注：start_analysis 仍由 showEvent 直接触发，因对话框管理自身显示生命周期，可接受。
    """

    progress_updated_signal = pyqtSignal(int, int, str, str, int, int)
    analysis_finished_signal = pyqtSignal(list, dict, list)
    analysis_canceled_signal = pyqtSignal()
    analysis_error_signal = pyqtSignal(str)
    analysis_stage_changed_signal = pyqtSignal(str, int, int)
    analysis_file_processed_signal = pyqtSignal(str, int, int)
    threshold_changed = pyqtSignal(int)
    # 用户请求取消时发出，由 Presenter 连接到 hash_service.cancel
    cancel_requested = pyqtSignal()
    # 窗口最小化/恢复时发出，参数为是否最小化
    minimization_changed = pyqtSignal(bool)

    def __init__(self, hash_service, total_count: int, initial_threshold: int, parent=None):
        """初始化对话框。

        Args:
            hash_service: 哈希分析服务实例（仅用于订阅事件和启动分析，不直接修改其状态）
            total_count: 图片总数（替代直接读取 hash_service.image_paths）
            initial_threshold: 初始相似度阈值（替代直接读取 hash_service.threshold）
            parent: 父组件
        """
        super().__init__(parent)
        self.setWindowTitle("图片相似度分析")
        # 允许窗口自由缩放（最大化按钮可用），仅约束最小尺寸避免控件被挤压
        self.setMinimumSize(550, 400)
        self.setModal(False)
        # 保留最小化与最大化按钮，移除帮助按钮
        self.setWindowFlags(
            self.windowFlags()
            & ~Qt.WindowContextHelpButtonHint
            | Qt.WindowMinimizeButtonHint
            | Qt.WindowMaximizeButtonHint
        )
        self.setWindowModality(Qt.NonModal)
        c = theme_manager.colors
        self.setStyleSheet(f"""
            QDialog {{
                background-color: {c.window_bg};
            }}
            QLabel {{
                color: {c.text_primary};
            }}
        """)

        self.hash_service = hash_service
        self.total_count = total_count
        self.start_time = None
        self.is_canceled = False
        # 标记分析是否正在进行中，防止 showEvent 重复触发
        self._is_analyzing = False
        # 本地跟踪阶段，替代直接读取 hash_service.current_stage
        self._current_stage = 0
        self.threshold = initial_threshold

        self.init_ui()
        self.connect_signals()
    
    def init_ui(self):
        layout = QVBoxLayout()
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title_label = QLabel("图片相似度分析")
        title_label.setFont(QFont("Microsoft YaHei", 14, QFont.Bold))
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)

        threshold_layout = QHBoxLayout()
        threshold_layout.setSpacing(10)

        c = theme_manager.colors
        threshold_label = QLabel("相似度阈值:")
        threshold_label.setFont(QFont("Microsoft YaHei", 10))
        threshold_label.setStyleSheet(f"color: {c.text_secondary};")
        threshold_layout.addWidget(threshold_label)

        c = theme_manager.colors
        self.threshold_slider = QSlider(Qt.Horizontal)
        self.threshold_slider.setMinimum(2)
        self.threshold_slider.setMaximum(25)
        self.threshold_slider.setValue(self.threshold)
        self.threshold_slider.setTickPosition(QSlider.TicksBelow)
        self.threshold_slider.setTickInterval(1)
        self.threshold_slider.valueChanged.connect(self.on_threshold_changed)
        self.threshold_slider.setStyleSheet(f"""
            QSlider::groove:horizontal {{
                height: 6px;
                background: {c.slider_groove};
                border-radius: 3px;
            }}
            QSlider::handle:horizontal {{
                background: {c.slider_handle};
                border: 2px solid {c.accent_hover};
                width: 16px;
                margin: -5px 0;
                border-radius: 8px;
            }}
            QSlider::sub-page:horizontal {{
                background: {c.slider_handle};
                border-radius: 3px;
            }}
            QSlider::tick:horizontal {{
                background: {c.slider_tick};
                width: 1px;
                height: 6px;
            }}
        """)
        threshold_layout.addWidget(self.threshold_slider)

        c = theme_manager.colors
        self.threshold_value_label = QLabel(f"{self.threshold}")
        self.threshold_value_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.threshold_value_label.setStyleSheet(f"color: {c.accent}; min-width: 30px;")
        self.threshold_value_label.setAlignment(Qt.AlignCenter)
        threshold_layout.addWidget(self.threshold_value_label)

        layout.addLayout(threshold_layout)

        c = theme_manager.colors
        threshold_hint = QLabel("阈值越小，相似度要求越高（2-25，默认10）")
        threshold_hint.setFont(QFont("Microsoft YaHei", 9))
        threshold_hint.setStyleSheet(f"color: {c.text_hint};")
        threshold_hint.setAlignment(Qt.AlignCenter)
        layout.addWidget(threshold_hint)

        c = theme_manager.colors
        self.progress_bar = QProgressBar()
        self.progress_bar.setMaximum(self.total_count * 3)
        self.progress_bar.setValue(0)
        self.progress_bar.setTextVisible(True)
        self.progress_bar.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {c.border};
                border-radius: 5px;
                text-align: center;
                font-size: 12px;
                color: {c.text_primary};
                background-color: {c.progress_bg};
            }}
            QProgressBar::chunk {{
                background-color: {c.progress_bar};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(self.progress_bar)

        self.progress_text = QLabel("0 / 0 (0%)")
        self.progress_text.setAlignment(Qt.AlignCenter)
        self.progress_text.setFont(QFont("Microsoft YaHei", 11))
        layout.addWidget(self.progress_text)

        stage_layout = QHBoxLayout()
        stage_layout.setSpacing(10)

        c = theme_manager.colors
        stage_label_text = QLabel("阶段:")
        stage_label_text.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        stage_label_text.setStyleSheet(f"color: {c.text_secondary};")
        stage_layout.addWidget(stage_label_text)

        c = theme_manager.colors
        self.stage_label = QLabel("准备中...")
        self.stage_label.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        self.stage_label.setStyleSheet(f"color: {c.accent};")
        stage_layout.addWidget(self.stage_label)

        stage_layout.addStretch()

        c = theme_manager.colors
        self.time_label = QLabel("预计剩余: --")
        self.time_label.setFont(QFont("Microsoft YaHei", 10))
        self.time_label.setStyleSheet(f"color: {c.text_secondary};")
        stage_layout.addWidget(self.time_label)

        layout.addLayout(stage_layout)

        c = theme_manager.colors
        self.current_stage_progress = QProgressBar()
        self.current_stage_progress.setMaximum(100)
        self.current_stage_progress.setValue(0)
        self.current_stage_progress.setTextVisible(False)
        self.current_stage_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 1px solid {c.border};
                border-radius: 3px;
                height: 6px;
                background-color: {c.progress_bg};
            }}
            QProgressBar::chunk {{
                background-color: {c.progress_bar};
                border-radius: 2px;
            }}
        """)
        layout.addWidget(self.current_stage_progress)

        file_label_title = QLabel("当前处理:")
        file_label_title.setFont(QFont("Microsoft YaHei", 10, QFont.Bold))
        layout.addWidget(file_label_title)

        c = theme_manager.colors
        self.file_label = QLabel("")
        self.file_label.setWordWrap(True)
        self.file_label.setAlignment(Qt.AlignLeft)
        self.file_label.setStyleSheet(f"color: {c.text_primary}; font-size: 12px; background-color: {c.list_bg}; padding: 8px; border: 1px solid {c.border}; border-radius: 4px; min-height: 40px;")
        layout.addWidget(self.file_label)

        speed_layout = QHBoxLayout()
        speed_layout.setSpacing(15)

        c = theme_manager.colors
        self.speed_label = QLabel("处理速度: --")
        self.speed_label.setFont(QFont("Microsoft YaHei", 10))
        self.speed_label.setStyleSheet(f"color: {c.text_secondary};")
        speed_layout.addWidget(self.speed_label)

        self.elapsed_label = QLabel("已用时: --")
        self.elapsed_label.setFont(QFont("Microsoft YaHei", 10))
        self.elapsed_label.setStyleSheet(f"color: {c.text_secondary};")
        speed_layout.addWidget(self.elapsed_label)

        layout.addLayout(speed_layout)

        self.setLayout(layout)

    def connect_signals(self):
        """订阅 service 事件并连接 Qt 信号。

        Observer 回调在 service 的后台线程中执行，不能直接操作 UI。
        因此 Observer 回调只 emit Qt 信号，Qt 信号跨线程时自动使用队列连接，
        槽函数在主线程执行，避免线程违规。
        """
        # Observer 回调（后台线程）-> emit Qt 信号
        self.hash_service.on('progress_updated', self._relay_progress_updated)
        self.hash_service.on('analysis_finished', self._relay_analysis_finished)
        self.hash_service.on('analysis_canceled', self._relay_analysis_canceled)
        self.hash_service.on('analysis_error', self._relay_analysis_error)
        self.hash_service.on('analysis_stage_changed', self._relay_stage_changed)
        self.hash_service.on('analysis_file_processed', self._relay_file_processed)

        # Qt 信号 -> UI 更新方法（主线程执行，自动跨线程队列）
        self.progress_updated_signal.connect(self.on_update_progress)
        self.analysis_finished_signal.connect(self.on_analysis_finished)
        self.analysis_canceled_signal.connect(self.on_analysis_canceled)
        self.analysis_error_signal.connect(self.on_analysis_error)
        self.analysis_stage_changed_signal.connect(self.on_stage_changed)

    # --- Observer 回调中转方法（后台线程执行，仅 emit 信号）---

    def _relay_progress_updated(self, current, total, stage_name, filename, processed_count, stage_progress=0):
        self.progress_updated_signal.emit(current, total, stage_name, filename, processed_count, stage_progress)

    def _relay_analysis_finished(self, groups, duplicates, hash_list=None):
        self.analysis_finished_signal.emit(groups, duplicates, hash_list if hash_list else [])

    def _relay_analysis_canceled(self):
        self.analysis_canceled_signal.emit()

    def _relay_analysis_error(self, error):
        self.analysis_error_signal.emit(error)

    def _relay_stage_changed(self, stage, current, total):
        self.analysis_stage_changed_signal.emit(stage, current, total)

    def _relay_file_processed(self, filename, current, total):
        self.analysis_file_processed_signal.emit(filename, current, total)

    def showEvent(self, event):
        debug_manager.log_info('哈希对话框显示', 'hash')
        super().showEvent(event)
        self.start_analysis()

    def start_analysis(self):
        if self._is_analyzing:
            debug_manager.log_info('哈希分析已在进行中，跳过重复启动', 'hash')
            return
        debug_manager.log_info('开始哈希分析', 'hash', image_count=self.total_count, threshold=self.threshold)
        self._is_analyzing = True
        self.start_time = time.time()
        self.is_canceled = False
        self._current_stage = 0

        self.hash_service.start_analysis(self.hash_service.image_paths)

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_time_display)
        self.timer.start(500)
    
    def on_threshold_changed(self, value: int):
        """用户调整阈值：仅更新本地显示并上报信号，不直接修改 service 状态。

        service 的阈值更新由 Presenter 的 on_hash_threshold_changed 回调统一处理，
        保证数据流向单一（View -> Presenter -> Service）。
        """
        self.threshold = value
        self.threshold_value_label.setText(str(value))
        self.threshold_changed.emit(value)
        debug_manager.log_info('用户调整相似度阈值', 'hash', threshold=value)

    def sync_threshold(self, threshold: int):
        """从主界面同步阈值到弹窗滑块。

        阻塞 valueChanged 信号避免反向触发 threshold_changed，
        防止主界面与弹窗之间形成循环同步。
        """
        if threshold == self.threshold:
            return
        self.threshold = threshold
        self.threshold_slider.blockSignals(True)
        self.threshold_slider.setValue(threshold)
        self.threshold_slider.blockSignals(False)
        self.threshold_value_label.setText(str(threshold))
        debug_manager.log_info('从主界面同步阈值到弹窗', 'hash', threshold=threshold)

    def on_update_progress(self, current: int, total: int, stage_name: str, filename: str, processed_count: int, stage_progress: int = 0):
        self.progress_bar.setMaximum(total)
        self.progress_bar.setValue(current)

        percentage = int((current / total) * 100) if total > 0 else 0
        self.progress_text.setText(f"{processed_count} / {self.total_count} ({percentage}%)")

        # 使用本地跟踪的 stage，替代直接读取 hash_service.current_stage
        self.stage_label.setText(f"{self._current_stage}/3: {stage_name}")
        self.current_stage_progress.setValue(stage_progress)

        if filename:
            if len(filename) > 60:
                filename = filename[:25] + "..." + filename[-30:]
            self.file_label.setText(filename)
        else:
            self.file_label.setText("...")

        if current > 0 and self.start_time:
            self._update_time_info(current, total, processed_count)

    def _update_time_info(self, current: int, total: int, processed_count: int):
        elapsed = time.time() - self.start_time
        avg_time_per_file = elapsed / processed_count if processed_count > 0 else 0
        remaining_files = self.total_count - processed_count
        estimated_remaining = avg_time_per_file * remaining_files

        self.time_label.setText(self._format_remaining_time(estimated_remaining))
        self.elapsed_label.setText(self._format_elapsed_time(elapsed))

        if elapsed > 0:
            speed = processed_count / elapsed
            if speed >= 1:
                speed_str = f"处理速度: {speed:.1f} 张/秒"
            else:
                speed_str = f"处理速度: {elapsed / processed_count:.1f} 秒/张"
            self.speed_label.setText(speed_str)

    @staticmethod
    def _format_remaining_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"预计剩余: {hours}h{minutes}m{secs}s"
        elif minutes > 0:
            return f"预计剩余: {minutes}m{secs}s"
        else:
            return f"预计剩余: {secs}s"

    @staticmethod
    def _format_elapsed_time(seconds: float) -> str:
        hours = int(seconds // 3600)
        minutes = int((seconds % 3600) // 60)
        secs = int(seconds % 60)

        if hours > 0:
            return f"已用时: {hours}h{minutes}m{secs}s"
        elif minutes > 0:
            return f"已用时: {minutes}m{secs}s"
        else:
            return f"已用时: {secs}s"

    def update_time_display(self):
        if self.start_time:
            elapsed = time.time() - self.start_time
            self.elapsed_label.setText(self._format_elapsed_time(elapsed))

    def on_analysis_finished(self, groups: list, duplicates: dict, hash_list: list = None):
        """分析完成回调（主线程执行）：停止计时器并关闭对话框。

        信号由 _relay_analysis_finished 在后台线程 emit，Qt 队列到主线程执行此方法。
        Presenter 的 on_hash_finished 也通过 analysis_finished_signal 连接，同样在主线程执行。
        """
        debug_manager.log_info('哈希分析完成', 'hash', group_count=len(groups), duplicate_groups=len(duplicates))
        self.timer.stop()
        # 标记已结束，防止 closeEvent 再次触发取消请求
        self.is_canceled = True
        self._is_analyzing = False
        self.accept()

    def on_analysis_canceled(self):
        """分析取消回调（主线程执行）：停止计时器并关闭对话框。"""
        self.is_canceled = True
        self._is_analyzing = False
        self.timer.stop()
        self.accept()

    def on_analysis_error(self, error: str):
        """分析出错回调（主线程执行）：停止计时器并关闭对话框。"""
        self.timer.stop()
        debug_manager.log_error('哈希分析出错', 'hash', error=error)
        # 标记已结束，防止 closeEvent 再次触发取消请求
        self.is_canceled = True
        self._is_analyzing = False
        self.accept()

    def on_stage_changed(self, stage: str, current: int, total: int):
        """阶段变更回调（主线程执行）：本地递增 _current_stage 用于显示。"""
        self._current_stage += 1
        debug_manager.log_info('哈希分析阶段变更', 'hash', stage=stage, current=current, total=total)

    def cancel_analysis(self):
        """取消分析：仅发出信号，由 Presenter 连接到 hash_service.cancel。

        不直接调用 service.cancel，保证取消操作通过信号链传递。
        """
        self.is_canceled = True
        self.cancel_requested.emit()

    def closeEvent(self, event):
        if not self.is_canceled:
            self.cancel_analysis()
        event.accept()

    def changeEvent(self, event):
        """拦截最小化事件：不使用系统最小化，而是直接隐藏窗口。

        系统最小化会在任务栏留下独立图标/条目，与「隐藏到主窗口恢复按钮」的设计不符。
        因此捕获最小化动作后改为 hide()，让窗口从屏幕和任务栏完全消失，
        仅通过主界面的「恢复分析」按钮重新显示。
        """
        if event.type() == QEvent.WindowStateChange:
            was_minimized = bool(event.oldState() & Qt.WindowMinimized)
            is_minimized = bool(self.windowState() & Qt.WindowMinimized)
            if is_minimized and not was_minimized:
                # 用户触发了最小化：先重置为正常状态，再隐藏窗口
                # 这样窗口不会残留在任务栏或屏幕上
                self.setWindowState(Qt.WindowNoState)
                self.minimization_changed.emit(True)
                debug_manager.log_info('哈希弹窗最小化（改为隐藏）', 'hash')
                self.hide()
                return
        super().changeEvent(event)