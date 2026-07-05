import os
from PyQt5.QtWidgets import QLabel
from PyQt5.QtCore import Qt, QTimer, QRect, QSize
from PyQt5.QtGui import QPainter, QFontMetrics, QColor


class ScrollingLabel(QLabel):
    """自动滚动的文本标签（跑马灯效果）。

    当文本宽度超过控件可用宽度时，文本从右向左慢速滚动；
    文本较短能完整显示时，保持静止且左对齐。

    使用方式：
        label = ScrollingLabel()
        label.setText("很长的文件名.jpg")
        label.setScrollSpeed(30)   # 可选：调整滚动速度（像素/秒）
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self._full_text = ""
        self._scroll_pos = 0
        self._text_width = 0
        self._needs_scroll = False
        # 滚动速度：像素/秒
        self._scroll_speed = 25
        # 首尾停留时间（毫秒）
        self._pause_duration = 1000
        self._pause_remaining = 0

        self._timer = QTimer(self)
        self._timer.setInterval(30)
        self._timer.timeout.connect(self._on_tick)

        self.setMinimumHeight(18)
        self.setText("")

    def setText(self, text: str):
        """设置显示文本，重新计算是否需要滚动。"""
        self._full_text = text
        self._scroll_pos = 0
        self._pause_remaining = self._pause_duration
        self._recalc()
        super().setText(text)
        self.update()

    def setScrollSpeed(self, pixels_per_second: int):
        """设置滚动速度，单位：像素/秒。默认 25。"""
        self._scroll_speed = max(5, pixels_per_second)

    def sizeHint(self):
        """重写 sizeHint：返回一个合理的建议尺寸，不随文本长度增长。

        防止长文件名导致布局系统撑大窗口。
        宽度建议为 100px（可被布局拉伸），高度由字体决定。
        """
        fm = QFontMetrics(self.font())
        h = max(self.minimumHeight(), fm.height() + 4)
        return QSize(100, h)

    def minimumSizeHint(self):
        """重写 minimumSizeHint：返回最小建议尺寸。

        最小宽度设为 30px，确保不会被压缩到完全不可见。
        """
        fm = QFontMetrics(self.font())
        h = max(self.minimumHeight(), fm.height() + 4)
        return QSize(30, h)

    def resizeEvent(self, event):
        """控件尺寸变化时重新计算是否需要滚动。"""
        super().resizeEvent(event)
        self._recalc()
        self._scroll_pos = 0
        self._pause_remaining = self._pause_duration
        self.update()

    def _recalc(self):
        """计算文本宽度和是否需要滚动，并启动/停止定时器。"""
        if not self._full_text:
            self._text_width = 0
            self._needs_scroll = False
            self._timer.stop()
            return
        fm = QFontMetrics(self.font())
        self._text_width = fm.width(self._full_text)
        available = self.width() - 4
        self._needs_scroll = self._text_width > available
        if self._needs_scroll:
            if not self._timer.isActive():
                self._timer.start()
        else:
            self._timer.stop()

    def _on_tick(self):
        """定时器回调：推进滚动位置。"""
        if not self._needs_scroll:
            return

        # 首尾暂停逻辑
        if self._pause_remaining > 0:
            self._pause_remaining -= 30
            return

        # 每帧移动像素数 = 速度(px/s) * 间隔(s)
        delta = self._scroll_speed * 0.03
        self._scroll_pos += delta
        total_scroll = self._text_width - (self.width() - 4)

        # 滚到底部后重置位置并在开头暂停
        if self._scroll_pos >= total_scroll:
            self._scroll_pos = 0
            self._pause_remaining = self._pause_duration

        self.update()

    def paintEvent(self, event):
        """自定义绘制：支持滚动偏移。"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.TextAntialiasing)

        if not self._full_text:
            painter.end()
            return

        fm = QFontMetrics(self.font())
        y = (self.height() + fm.ascent() - fm.descent()) // 2
        painter.setPen(QColor("#7f8c8d"))
        painter.setFont(self.font())

        if self._needs_scroll:
            x = 2 - int(self._scroll_pos)
            painter.drawText(x, y, self._full_text)
        else:
            painter.drawText(2, y, self._full_text)

        painter.end()
