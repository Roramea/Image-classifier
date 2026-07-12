import os
from typing import Dict, Optional

from core.config_manager import ConfigManager
from core.cache_manager import CacheManager
from core.memory_manager import MemoryManager
from core.session_manager import SessionManager
from core.storage_manager import StorageManager
from core.debug_manager import debug_manager


class ClassificationManager:
    def __init__(self):
        self.config_manager = ConfigManager()
        self.cache_manager = CacheManager()
        self.memory_manager = MemoryManager()
        self.session_manager = SessionManager()
        self.storage_manager = StorageManager()
        self.session_manager.load_unfinished_session()
        debug_manager.log_info('ClassificationManager 初始化完成（聚合模式）', 'config')

    @property
    def current_folder(self) -> str:
        return self.config_manager.current_folder

    @current_folder.setter
    def current_folder(self, value: str):
        self.config_manager.current_folder = value
        self.cache_manager.set_current_folder(value)
        self.memory_manager.set_current_folder(value)

    @property
    def last_folder(self) -> str:
        return self.config_manager.last_folder

    def get_config_file(self, folder_path: str) -> str:
        return self.config_manager.get_config_file(folder_path)

    def load_recent_folders(self):
        self.config_manager.load_recent_folders()

    def save_recent_folders(self, folder_path: str):
        self.config_manager.save_recent_folders(folder_path)

    def load_config(self, folder_path: str = ""):
        self.config_manager.load_config(folder_path)
        self.cache_manager.set_current_folder(self.config_manager.current_folder)
        self.memory_manager.set_current_folder(self.config_manager.current_folder)

    def save_config(self):
        return self.config_manager.save_config()

    def load_settings(self):
        self.config_manager.load_settings()

    def save_settings(self):
        self.config_manager.save_settings()

    def get_hash_threshold(self) -> int:
        return self.config_manager.get_hash_threshold()

    def set_hash_threshold(self, threshold: int):
        self.config_manager.set_hash_threshold(threshold)

    def get_recent_folders(self) -> list:
        return self.config_manager.get_recent_folders()

    def load_unfinished_session(self):
        self.session_manager.load_unfinished_session()

    def get_duplicate_memory_file(self) -> str:
        return self.memory_manager.get_duplicate_memory_file()

    def get_hash_cache_file(self) -> str:
        return self.cache_manager.get_hash_cache_file()

    def load_duplicate_memory(self):
        self.memory_manager.load_duplicate_memory()

    def load_hash_cache(self) -> dict:
        return self.cache_manager.load_hash_cache()

    def save_hash_cache(self, cache: dict):
        self.cache_manager.save_hash_cache(cache)

    def rename_in_hash_cache(self, old_path: str, new_path: str) -> bool:
        return self.cache_manager.rename_in_hash_cache(old_path, new_path)

    def check_files_changed(self, image_paths: list) -> tuple:
        return self.cache_manager.check_files_changed(image_paths)

    def create_file_cache(self, image_paths: list) -> dict:
        return self.cache_manager.create_file_cache(image_paths)

    def build_hash_cache(self, image_paths: list, groups: list, duplicates: dict,
                         hash_list: list = None) -> dict:
        return self.cache_manager.build_hash_cache(image_paths, groups, duplicates, hash_list)

    def save_unfinished_session(self, session_data: dict):
        self.session_manager.save_unfinished_session(session_data)

    def clear_unfinished_session(self):
        self.session_manager.clear_unfinished_session()

    def save_duplicate_memory(self):
        self.memory_manager.save_duplicate_memory()

    def add_processed_duplicate(self, md5_hash: str, deleted_paths: list):
        self.memory_manager.add_processed_duplicate(md5_hash, deleted_paths)

    def is_duplicate_processed(self, md5_hash: str) -> bool:
        return self.memory_manager.is_duplicate_processed(md5_hash)

    def clear_duplicate_memory(self):
        self.memory_manager.clear_duplicate_memory()

    def get_storage_size(self) -> int:
        return self.storage_manager.get_storage_size()

    def get_storage_details(self) -> dict:
        return self.storage_manager.get_storage_details()

    def clear_categories(self, categories: list) -> bool:
        result = self.storage_manager.clear_categories(categories)
        if 'shortcuts' in categories:
            self.config_manager.shortcut_map = {}
        if 'duplicates' in categories:
            self.memory_manager.processed_duplicates = {}
        if 'recent' in categories:
            self.config_manager.recent_folders = []
            self.config_manager.last_folder = ""
        if 'session' in categories:
            self.session_manager.unfinished_session = None
        return result

    def get_unfinished_session(self) -> Optional[dict]:
        return self.session_manager.get_unfinished_session()

    def _is_valid_path(self, path: str) -> bool:
        return self.config_manager._is_valid_path(path)

    def add_shortcut(self, shortcut: str, folder_path: str) -> bool:
        return self.config_manager.add_shortcut(shortcut, folder_path)

    def remove_shortcut(self, shortcut: str) -> bool:
        return self.config_manager.remove_shortcut(shortcut)

    def get_folder(self, shortcut: str) -> Optional[str]:
        return self.config_manager.get_folder(shortcut)

    def get_all_shortcuts(self) -> Dict[str, str]:
        return self.config_manager.get_all_shortcuts()

    def classify_image(self, image_path: str, shortcut: str) -> Optional[str]:
        folder_path = self.get_folder(shortcut)
        if not folder_path:
            debug_manager.log_error('找不到快捷键对应的文件夹', 'classify', shortcut=shortcut)
            return None

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                debug_manager.log_info('创建分类文件夹', 'classify', folder_path=folder_path)
            except Exception as e:
                debug_manager.log_exception(e, 'classify', folder_path=folder_path)
                return None

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
            debug_manager.log_info('图片分类成功', 'classify', image_path=image_path, dest_path=dest_path)
            return dest_path
        except Exception as e:
            debug_manager.log_exception(e, 'classify', image_path=image_path, folder_path=folder_path)
            return None