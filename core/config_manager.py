import os
import json
import hashlib
from typing import Dict, Optional

from core.debug_manager import debug_manager


class ConfigManager:
    CONFIG_DIR = 'classifier_configs'
    MAX_RECENT_FOLDERS = 10

    def __init__(self):
        self.shortcut_map: Dict[str, str] = {}
        self.current_folder: str = ""
        self.last_folder: str = ""
        self.recent_folders: list = []
        self.hash_threshold: int = 10
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)
            debug_manager.log_info('创建配置目录', 'config', path=self.CONFIG_DIR)
        self.load_recent_folders()
        self.load_settings()
        debug_manager.log_info('ConfigManager 初始化完成', 'config')

    def get_config_file(self, folder_path: str) -> str:
        folder_hash = hashlib.md5(folder_path.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}.json')

    def load_recent_folders(self):
        recent_file = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
        debug_manager.log_info('加载最近文件夹', 'config', file=recent_file)
        if os.path.exists(recent_file):
            try:
                with open(recent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_folders = data.get('recent_folders', [])
                debug_manager.log_info('最近文件夹加载成功', 'config', count=len(self.recent_folders))
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=recent_file)
                self.recent_folders = []
        else:
            self.recent_folders = []
            debug_manager.log_info('最近文件夹文件不存在', 'config', file=recent_file)
        self.last_folder = self.recent_folders[0] if self.recent_folders else ""
        debug_manager.log_info('最近文件夹加载完成', 'config', last_folder=self.last_folder)

    def save_recent_folders(self, folder_path: str):
        debug_manager.log_info('保存最近文件夹', 'config', folder_path=folder_path)
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
            debug_manager.log_info('最近文件夹保存成功', 'config', count=len(self.recent_folders))
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=recent_file)

    def load_config(self, folder_path: str = ""):
        debug_manager.log_info('加载配置', 'config', folder_path=folder_path)
        if folder_path:
            self.current_folder = folder_path
            config_file = self.get_config_file(folder_path)
        elif self.last_folder:
            self.current_folder = self.last_folder
            config_file = self.get_config_file(self.last_folder)
        else:
            self.shortcut_map = {}
            self.current_folder = ""
            debug_manager.log_info('无配置文件，使用空映射', 'config')
            return

        debug_manager.log_info('配置文件路径', 'config', file=config_file)
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.shortcut_map = json.load(f)
                debug_manager.log_info('配置加载成功', 'config', shortcuts_count=len(self.shortcut_map))
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=config_file)
                self.shortcut_map = {}
        else:
            self.shortcut_map = {}
            debug_manager.log_info('配置文件不存在', 'config', file=config_file)

    def save_config(self):
        if not self.current_folder:
            debug_manager.log_error('无法保存配置', 'config', reason='current_folder为空')
            return False
        config_file = self.get_config_file(self.current_folder)
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.shortcut_map, f, ensure_ascii=False, indent=2)
            self.save_recent_folders(self.current_folder)
            debug_manager.log_info('配置保存成功', 'config', file=config_file, shortcuts_count=len(self.shortcut_map))
            return True
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=config_file)
            return False

    def load_settings(self):
        settings_file = os.path.join(self.CONFIG_DIR, 'settings.json')
        debug_manager.log_info('加载全局设置', 'config', file=settings_file)
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.hash_threshold = settings.get('hash_threshold', 10)
                debug_manager.log_info('全局设置加载成功', 'config', hash_threshold=self.hash_threshold)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=settings_file)
                self.hash_threshold = 10
        else:
            self.hash_threshold = 10
            debug_manager.log_info('全局设置文件不存在，使用默认值', 'config', hash_threshold=self.hash_threshold)

    def save_settings(self):
        settings_file = os.path.join(self.CONFIG_DIR, 'settings.json')
        debug_manager.log_info('保存全局设置', 'config', file=settings_file, hash_threshold=self.hash_threshold)
        try:
            settings = {
                'hash_threshold': self.hash_threshold
            }
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            debug_manager.log_info('全局设置保存成功', 'config')
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=settings_file)

    def get_hash_threshold(self) -> int:
        return self.hash_threshold

    def set_hash_threshold(self, threshold: int):
        self.hash_threshold = threshold
        self.save_settings()
        debug_manager.log_info('设置哈希阈值', 'config', threshold=threshold)

    def get_recent_folders(self) -> list:
        return self.recent_folders.copy()

    def _is_valid_path(self, path: str) -> bool:
        if not path or not isinstance(path, str):
            debug_manager.log_warning('路径无效', 'config', path=path)
            return False

        invalid_chars = '<>"|?*'
        for char in invalid_chars:
            if char in path:
                debug_manager.log_warning('路径包含无效字符', 'config', path=path, invalid_char=char)
                return False

        colon_count = path.count(':')
        if colon_count > 1:
            debug_manager.log_warning('路径包含多个冒号', 'config', path=path)
            return False

        if colon_count == 1 and not (len(path) >= 2 and path[1] == ':' and path[0].isalpha()):
            debug_manager.log_warning('冒号位置无效', 'config', path=path)
            return False

        return True

    def add_shortcut(self, shortcut: str, folder_path: str) -> bool:
        if not self.current_folder:
            debug_manager.log_error('无法添加快捷键：未选择图片文件夹', 'config', shortcut=shortcut)
            return False

        if shortcut in self.shortcut_map:
            debug_manager.log_warning('快捷键已存在', 'config', shortcut=shortcut)
            return False

        if not self._is_valid_path(folder_path):
            debug_manager.log_error('路径验证失败', 'config', shortcut=shortcut, folder_path=folder_path)
            return False

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                debug_manager.log_info('创建文件夹', 'config', folder_path=folder_path)
            except Exception as e:
                debug_manager.log_exception(e, 'config', folder_path=folder_path)
                return False

        self.shortcut_map[shortcut] = folder_path
        result = self.save_config()
        if result:
            debug_manager.log_info('快捷键添加成功', 'config', shortcut=shortcut, folder_path=folder_path,
                                   current_folder=self.current_folder)
        else:
            del self.shortcut_map[shortcut]
            debug_manager.log_error('快捷键保存失败', 'config', shortcut=shortcut)
        return result

    def remove_shortcut(self, shortcut: str) -> bool:
        if shortcut in self.shortcut_map:
            removed_path = self.shortcut_map.pop(shortcut)
            result = self.save_config()
            if not result:
                self.shortcut_map[shortcut] = removed_path
            return result
        return False

    def get_folder(self, shortcut: str) -> Optional[str]:
        return self.shortcut_map.get(shortcut)

    def get_all_shortcuts(self) -> Dict[str, str]:
        return self.shortcut_map.copy()