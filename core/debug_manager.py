import os
import json
import time
import traceback
import threading
from typing import List, Dict, Optional


class DebugManager:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        
        self.logs: List[Dict] = []
        self.log_file = os.path.join('classifier_configs', 'debug_logs.json')
        self.debug_mode = True
        self.max_logs = 1000
        self._initialized = True
    
    def log(self, level: str, message: str, category: str = 'general', **kwargs):
        if not self.debug_mode:
            return
        
        log_entry = {
            'timestamp': time.strftime('%Y-%m-%d %H:%M:%S'),
            'level': level.upper(),
            'category': category,
            'message': message,
            **kwargs
        }
        
        self.logs.append(log_entry)
        
        if len(self.logs) > self.max_logs:
            self.logs = self.logs[-self.max_logs:]
        
        self._save_logs()
    
    def log_warning(self, message: str, category: str = 'general', **kwargs):
        self.log('WARNING', message, category, **kwargs)
    
    def log_error(self, message: str, category: str = 'general', **kwargs):
        self.log('ERROR', message, category, **kwargs)
    
    def log_info(self, message: str, category: str = 'general', **kwargs):
        self.log('INFO', message, category, **kwargs)
    
    def log_exception(self, ex: Exception, category: str = 'exception', **kwargs):
        trace = traceback.format_exc()
        self.log_error(
            str(ex),
            category,
            exception_type=type(ex).__name__,
            traceback=trace,
            **kwargs
        )
    
    def _save_logs(self):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.logs, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def get_logs(self, level: Optional[str] = None, category: Optional[str] = None) -> List[Dict]:
        result = self.logs
        
        if level:
            result = [log for log in result if log['level'] == level.upper()]
        
        if category:
            result = [log for log in result if log['category'] == category]
        
        return result
    
    def clear_logs(self):
        self.logs = []
        self._save_logs()


debug_manager = DebugManager()