from PyQt5.QtCore import QObject, pyqtSignal
from threading import Thread

from core.image_scanner import ImageScanner
from core.debug_manager import debug_manager


class ScanThread(QObject):
    """文件夹扫描线程。

    使用 QObject + pyqtSignal 替代自定义回调，确保所有回调在主线程执行，
    避免 "QObject::setParent: Cannot set parent, new parent is in a different thread" 错误。

    信号列表：
    - progress(int, int): 扫描进度 (current, total)
    - finished(list): 扫描完成，返回图片路径列表
    - error(str): 扫描出错，返回错误信息
    """

    progress = pyqtSignal(int, int)
    finished = pyqtSignal(list)
    error = pyqtSignal(str)

    def __init__(self, folder_path: str):
        super().__init__()
        self.folder_path = folder_path
        self.scanner = ImageScanner()
        self._thread = None

    def start(self):
        """启动后台扫描线程。"""
        self._thread = Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self):
        """后台线程入口：执行扫描并通过信号上报结果。

        注意：pyqtSignal 在非 QObject 所属线程 emit 时，自动使用 Qt.QueuedConnection
        将事件投递到对象所属线程（主线程），因此槽函数在主线程执行。
        """
        try:
            debug_manager.log_info('开始扫描文件夹', 'scan', folder_path=self.folder_path)
            count = self.scanner.scan_folder(self.folder_path)
            self.progress.emit(count, count)
            debug_manager.log_info('扫描完成', 'scan', folder_path=self.folder_path, image_count=count)
            self.finished.emit(self.scanner.image_paths)
        except Exception as e:
            debug_manager.log_exception(e, 'scan', folder_path=self.folder_path)
            self.error.emit(str(e))
