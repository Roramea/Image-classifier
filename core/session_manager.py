import os
import json
from typing import Optional, Dict

from core.debug_manager import debug_manager


class SessionManager:
    CONFIG_DIR = 'classifier_configs'

    def __init__(self):
        self.unfinished_session = None

    def load_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('加载未完成会话', 'config', file=session_file)
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    self.unfinished_session = json.load(f)
                debug_manager.log_info('未完成会话加载成功', 'config', session=self.unfinished_session)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=session_file)
                self.unfinished_session = None
        else:
            self.unfinished_session = None
            debug_manager.log_info('未完成会话文件不存在', 'config', file=session_file)

    def save_unfinished_session(self, session_data: dict):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('保存未完成会话', 'config', session_data=session_data)
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            self.unfinished_session = session_data
            debug_manager.log_info('未完成会话保存成功', 'config', file=session_file)
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=session_file)

    def clear_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('清除未完成会话', 'config', file=session_file)
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                debug_manager.log_info('未完成会话文件已删除', 'config', file=session_file)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=session_file)
        self.unfinished_session = None

    def get_unfinished_session(self) -> Optional[dict]:
        if self.unfinished_session:
            folder_path = self.unfinished_session.get('folder_path', "")
            if os.path.exists(folder_path):
                return self.unfinished_session
        return None