import sys
import os
import traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PyQt5.QtWidgets import QApplication
from views.main_window import MainWindow
from core.debug_manager import debug_manager
from core.theme_manager import theme_manager


def handle_exception(exc_type, exc_value, exc_traceback):
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
        return
    
    debug_manager.log_error(
        f"未处理异常: {exc_type.__name__}: {exc_value}",
        'app',
        traceback=''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
    )
    sys.__excepthook__(exc_type, exc_value, exc_traceback)


def main():
    sys.excepthook = handle_exception
    debug_manager.log_info('应用启动', 'app')
    
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    
    try:
        sys.exit(app.exec_())
    except Exception as e:
        debug_manager.log_exception(e, 'app')
        raise


if __name__ == "__main__":
    main()