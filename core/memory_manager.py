import os
import json
import hashlib
from typing import Dict, List

from core.debug_manager import debug_manager


class MemoryManager:
    CONFIG_DIR = 'classifier_configs'

    def __init__(self):
        self.current_folder: str = ""
        self.processed_duplicates: Dict[str, list] = {}

    def set_current_folder(self, folder_path: str):
        self.current_folder = folder_path

    def get_duplicate_memory_file(self) -> str:
        if not self.current_folder:
            return ""
        folder_hash = hashlib.md5(self.current_folder.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}_duplicates.json')

    def load_duplicate_memory(self):
        debug_manager.log_info('加载重复图片记忆', 'config', current_folder=self.current_folder)
        if not self.current_folder:
            self.processed_duplicates = {}
            debug_manager.log_info('无当前文件夹，使用空记忆', 'config')
            return
        memory_file = self.get_duplicate_memory_file()
        debug_manager.log_info('重复图片记忆文件路径', 'config', file=memory_file)
        if os.path.exists(memory_file):
            try:
                with open(memory_file, 'r', encoding='utf-8') as f:
                    self.processed_duplicates = json.load(f)
                debug_manager.log_info('重复图片记忆加载成功', 'config', groups_count=len(self.processed_duplicates))
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=memory_file)
                self.processed_duplicates = {}
        else:
            self.processed_duplicates = {}
            debug_manager.log_info('重复图片记忆文件不存在', 'config', file=memory_file)

    def save_duplicate_memory(self):
        if not self.current_folder:
            debug_manager.log_warning('无法保存重复图片记忆', 'config', reason='current_folder为空')
            return
        memory_file = self.get_duplicate_memory_file()
        debug_manager.log_info('保存重复图片记忆', 'config', file=memory_file, groups_count=len(self.processed_duplicates))
        try:
            with open(memory_file, 'w', encoding='utf-8') as f:
                json.dump(self.processed_duplicates, f, ensure_ascii=False, indent=2)
            debug_manager.log_info('重复图片记忆保存成功', 'config', file=memory_file)
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=memory_file)

    def add_processed_duplicate(self, md5_hash: str, deleted_paths: list):
        debug_manager.log_info('添加已处理重复图片', 'config', md5_hash=md5_hash, deleted_count=len(deleted_paths))
        self.processed_duplicates[md5_hash] = deleted_paths
        self.save_duplicate_memory()

    def is_duplicate_processed(self, md5_hash: str) -> bool:
        return md5_hash in self.processed_duplicates

    def clear_duplicate_memory(self):
        memory_file = self.get_duplicate_memory_file()
        debug_manager.log_info('清除重复图片记忆', 'config', file=memory_file)
        self.processed_duplicates = {}
        if os.path.exists(memory_file):
            try:
                os.remove(memory_file)
                debug_manager.log_info('重复图片记忆文件已删除', 'config', file=memory_file)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=memory_file)