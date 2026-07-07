import os
import json
import time
import traceback
import threading
from typing import List, Dict, Optional
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs


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
        self.server = None
        self.server_thread = None
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
    
    def start_http_server(self, port: int = 8765):
        if self.server:
            return
        
        class DebugHandler(BaseHTTPRequestHandler):
            def _send_json_response(self, data, status=200):
                self.send_response(status)
                self.send_header('Content-Type', 'application/json; charset=utf-8')
                self.end_headers()
                self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))
            
            def do_GET(self):
                parsed = urlparse(self.path)
                query = parse_qs(parsed.query)
                
                if parsed.path == '/api/logs':
                    level = query.get('level', [None])[0]
                    category = query.get('category', [None])[0]
                    limit = int(query.get('limit', [100])[0])
                    
                    logs = self.server.debug_manager.get_logs(level, category)
                    self._send_json_response({
                        'status': 'success',
                        'count': len(logs),
                        'logs': logs[-limit:]
                    })
                
                elif parsed.path == '/api/clear':
                    self.server.debug_manager.clear_logs()
                    self._send_json_response({'status': 'success', 'message': '日志已清空'})
                
                elif parsed.path == '/api/status':
                    logs = self.server.debug_manager.logs
                    stats = {
                        'total': len(logs),
                        'errors': len([l for l in logs if l['level'] == 'ERROR']),
                        'warnings': len([l for l in logs if l['level'] == 'WARNING']),
                        'info': len([l for l in logs if l['level'] == 'INFO']),
                        'debug_mode': self.server.debug_manager.debug_mode
                    }
                    self._send_json_response({'status': 'success', 'stats': stats})
                
                else:
                    self._send_json_response({'status': 'error', 'message': '未知路径'}, 404)
            
            def do_POST(self):
                parsed = urlparse(self.path)
                
                if parsed.path == '/api/log':
                    try:
                        content_length = int(self.headers['Content-Length'])
                        body = self.rfile.read(content_length).decode('utf-8')
                        data = json.loads(body)
                        
                        level = data.get('level', 'INFO')
                        message = data.get('message', '')
                        category = data.get('category', 'general')
                        
                        if level.upper() == 'WARNING':
                            self.server.debug_manager.log_warning(message, category, **data.get('extra', {}))
                        elif level.upper() == 'ERROR':
                            self.server.debug_manager.log_error(message, category, **data.get('extra', {}))
                        else:
                            self.server.debug_manager.log_info(message, category, **data.get('extra', {}))
                        
                        self._send_json_response({'status': 'success'})
                    except Exception as e:
                        self._send_json_response({'status': 'error', 'message': str(e)}, 400)
                
                else:
                    self._send_json_response({'status': 'error', 'message': '未知路径'}, 404)
            
            def log_message(self, format, *args):
                pass
        
        self.server = HTTPServer(('localhost', port), DebugHandler)
        self.server.debug_manager = self
        self.server_thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.server_thread.start()


debug_manager = DebugManager()