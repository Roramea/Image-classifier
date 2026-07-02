import os
import json
import hashlib
from typing import Dict, Optional


class ClassificationManager:
    CONFIG_DIR = 'classifier_configs'
    MAX_RECENT_FOLDERS = 10
    
    def __init__(self):
        self.shortcut_map: Dict[str, str] = {}
        self.current_folder: str = ""
        self.last_folder: str = ""
        self.recent_folders: list = []
        self.unfinished_session = None
        self.processed_duplicates: Dict[str, list] = {}
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)
        self.load_recent_folders()
        self.load_unfinished_session()
        self.load_duplicate_memory()
    
    def get_config_file(self, folder_path: str) -> str:
        folder_hash = hashlib.md5(folder_path.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}.json')
    
    def load_recent_folders(self):
        recent_file = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
        if os.path.exists(recent_file):
            try:
                with open(recent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_folders = data.get('recent_folders', [])
            except Exception:
                self.recent_folders = []
        else:
            self.recent_folders = []
        self.last_folder = self.recent_folders[0] if self.recent_folders else ""
    
    def save_recent_folders(self, folder_path: str):
        if folder_path in self.recent_folders:
            self.recent_folders.remove(folder_path)
        self.recent_folders.insert(0, folder_path)
        if len(self.recent_folders) > self.MAX_RECENT_FOLDERS:
            self.recent_folders = self.recent_folders[:self.MAX_RECENT_FOLDERS]
        
        recent_file = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
        try:
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump({'recent_folders': self.recent_folders}, f, ensure_ascii=False, indent=2)
            self.last_folder = self.recent_folders[0]
        except Exception:
            pass
    
    def load_config(self, folder_path: str = ""):
        if folder_path:
            self.current_folder = folder_path
            config_file = self.get_config_file(folder_path)
        elif self.last_folder:
            self.current_folder = self.last_folder
            config_file = self.get_config_file(self.last_folder)
        else:
            self.shortcut_map = {}
            return
        
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.shortcut_map = json.load(f)
            except Exception:
                self.shortcut_map = {}
        else:
            self.shortcut_map = {}
    
    def save_config(self):
        if not self.current_folder:
            return False
        config_file = self.get_config_file(self.current_folder)
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.shortcut_map, f, ensure_ascii=False, indent=2)
            self.save_recent_folders(self.current_folder)
            return True
        except Exception:
            return False
    
    def get_recent_folders(self) -> list:
        return self.recent_folders.copy()
    
    def load_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    self.unfinished_session = json.load(f)
            except Exception:
                self.unfinished_session = None
        else:
            self.unfinished_session = None
    
    def get_duplicate_memory_file(self) -> str:
        if not self.current_folder:
            return ""
        folder_hash = hashlib.md5(self.current_folder.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}_duplicates.json')
    
    def load_duplicate_memory(self):
        if not self.current_folder:
            self.processed_duplicates = {}
            return
        memory_file = self.get_duplicate_memory_file()
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.processed_duplicates = json.load(f)
            except Exception:
                self.processed_duplicates = {}
        else:
            self.processed_duplicates = {}
    
    def save_unfinished_session(self, session_data: dict):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            self.unfinished_session = session_data
        except Exception:
            pass
    
    def clear_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
            except Exception:
                pass
        self.unfinished_session = None
    
    def save_duplicate_memory(self):
        if not self.current_folder:
            return
        memory_file = self.get_duplicate_memory_file()
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_duplicates, f, ensure_ascii=False, indent=2)
        except Exception:
            pass
    
    def add_processed_duplicate(self, md5_hash: str, deleted_paths: list):
        self.processed_duplicates[md5_hash] = deleted_paths
        self.save_duplicate_memory()
    
    def is_duplicate_processed(self, md5_hash: str) -> bool:
        return md5_hash in self.processed_duplicates
    
    def get_processed_duplicate_paths(self, md5_hash: str) -> list:
        return self.processed_duplicates.get(md5_hash, [])
    
    def clear_duplicate_memory(self):
        self.processed_duplicates = {}
        memory_file = self.get_duplicate_memory_file()
        if os.path.exists(memory_file):
            try:
                os.remove(memory_file)
            except Exception:
                pass
    
    def check_all_duplicates_processed(self, all_duplicates: dict) -> bool:
        for md5_hash in all_duplicates.keys():
            if md5_hash not in self.processed_duplicates:
                return False
        return True
    
    def get_storage_size(self) -> int:
        total_size = 0
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def format_storage_size(self) -> str:
        size = self.get_storage_size()
        return self._format_size(size)
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"
    
    def get_storage_details(self) -> dict:
        details = {
            'shortcuts': {
                'name': '快捷键配置',
                'description': '各文件夹的快捷键绑定设置',
                'files': [],
                'size': 0
            },
            'duplicates': {
                'name': '重复图片处理记忆',
                'description': '已处理的重复图片组记录',
                'files': [],
                'size': 0
            },
            'recent': {
                'name': '最近文件夹记录',
                'description': '最近使用的文件夹列表',
                'files': [],
                'size': 0
            },
            'session': {
                'name': '未完成分类会话',
                'description': '上次未完成的分类进度',
                'files': [],
                'size': 0
            }
        }
        
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    file_size = os.path.getsize(filepath)
                    
                    if filename.endswith('_duplicates.json'):
                        details['duplicates']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['duplicates']['size'] += file_size
                    elif filename == 'recent_folders.json':
                        details['recent']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['recent']['size'] += file_size
                    elif filename == 'unfinished_session.json':
                        details['session']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['session']['size'] += file_size
                    elif filename.endswith('.json'):
                        details['shortcuts']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['shortcuts']['size'] += file_size
        
        return details
    
    def clear_categories(self, categories: list) -> bool:
        success = True
        
        if 'shortcuts' in categories:
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    if not filename.endswith('_duplicates.json') and \
                       filename != 'recent_folders.json' and \
                       filename != 'unfinished_session.json':
                        try:
                            os.remove(filepath)
                        except Exception:
                            success = False
            self.shortcut_map = {}
        
        if 'duplicates' in categories:
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith('_duplicates.json'):
                    try:
                        os.remove(filepath)
                    except Exception:
                        success = False
            self.processed_duplicates = {}
        
        if 'recent' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False
            self.recent_folders = []
            self.last_folder = ""
        
        if 'session' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False
            self.unfinished_session = None
        
        return success
    
    def clear_all_storage(self):
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        
        self.shortcut_map = {}
        self.recent_folders = []
        self.unfinished_session = None
        self.processed_duplicates = {}
        self.last_folder = ""
    
    def get_unfinished_session(self) -> Optional[dict]:
        if self.unfinished_session:
            folder_path = self.unfinished_session.get('folder_path', "")
            if os.path.exists(folder_path):
                return self.unfinished_session
        return None
    
    def add_shortcut(self, shortcut: str, folder_path: str) -> bool:
        if shortcut in self.shortcut_map:
            return False
        
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except Exception:
                return False
        
        self.shortcut_map[shortcut] = folder_path
        return self.save_config()
    
    def remove_shortcut(self, shortcut: str) -> bool:
        if shortcut in self.shortcut_map:
            del self.shortcut_map[shortcut]
            return self.save_config()
        return False
    
    def get_folder(self, shortcut: str) -> Optional[str]:
        return self.shortcut_map.get(shortcut)
    
    def get_all_shortcuts(self) -> Dict[str, str]:
        return self.shortcut_map.copy()
    
    def classify_image(self, image_path: str, shortcut: str) -> bool:
        folder_path = self.get_folder(shortcut)
        if not folder_path:
            return False
        
        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
            except Exception:
                return False
        
        try:
            filename = os.path.basename(image_path)
            dest_path = os.path.join(folder_path, filename)
            
            counter = 1
            while os.path.exists(dest_path):
                name, ext = os.path.splitext(filename)
                dest_path = os.path.join(folder_path, f"{name}_{counter}{ext}")
                counter += 1
            
            import shutil
            shutil.move(image_path, dest_path)
            return True
        except Exception:
            return False