from PyQt5.QtCore import QThread, pyqtSignal

from core.image_scanner import ImageScanner
from core.debug_manager import debug_manager


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
            debug_manager.log_info('开始扫描文件夹', 'scan', folder_path=self.folder_path)
            count = self.scanner.scan_folder(self.folder_path)
            self.progress_updated.emit(count, count)
            debug_manager.log_info('扫描完成', 'scan', folder_path=self.folder_path, image_count=count)
            self.scanning_finished.emit(self.scanner.image_paths)
        except Exception as e:
            debug_manager.log_exception(e, 'scan', folder_path=self.folder_path)
            self.error_occurred.emit(str(e))