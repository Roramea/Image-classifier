import os
from typing import Dict, List

from PyQt5.QtCore import QObject, pyqtSignal

from core.debug_manager import debug_manager


class DuplicateService(QObject):
    duplicate_deleted = pyqtSignal(str, int, int)
    duplicate_processing = pyqtSignal(int, int)
    duplicate_all_processed = pyqtSignal()
    duplicate_memory_cleared = pyqtSignal()
    
    def __init__(self, classifier):
        super().__init__()
        self.classifier = classifier
        self.duplicates: Dict[str, List[str]] = {}
        self.processed_images = set()
        debug_manager.log_info('DuplicateService 初始化完成', 'duplicate')
    
    def set_duplicates(self, duplicates: Dict[str, List[str]]):
        debug_manager.log_info('设置重复图片', 'duplicate', total_groups=len(duplicates))
        remaining_duplicates = {}
        processed_count = 0
        for md5_hash, paths in duplicates.items():
            if not self.classifier.is_duplicate_processed(md5_hash):
                remaining_duplicates[md5_hash] = paths
            else:
                processed_count += 1
        self.duplicates = remaining_duplicates
        debug_manager.log_info('重复图片设置完成', 'duplicate', remaining_groups=len(remaining_duplicates), already_processed=processed_count)
    
    def get_duplicates(self) -> Dict[str, List[str]]:
        return self.duplicates
    
    def get_valid_groups(self) -> List[tuple]:
        return [(md5, paths) for md5, paths in self.duplicates.items() if paths and len(paths) > 1]
    
    def delete_duplicate_group(self, md5_hash: str, paths: List[str]) -> tuple:
        deleted_paths = []
        failed_paths = []
        debug_manager.log_info('开始删除重复图片组', 'duplicate', md5_hash=md5_hash, path_count=len(paths))
        
        total_to_delete = len(paths) - 1
        for i, path in enumerate(paths[1:]):
            self.duplicate_processing.emit(i + 1, total_to_delete)
            try:
                os.remove(path)
                deleted_paths.append(path)
                debug_manager.log_info('删除图片成功', 'duplicate', path=path)
                if path in self.processed_images:
                    self.processed_images.remove(path)
            except Exception as e:
                failed_paths.append(f"{path}: {e}")
                debug_manager.log_exception(e, 'duplicate', path=path)
        
        self.classifier.add_processed_duplicate(md5_hash, deleted_paths)
        
        if md5_hash in self.duplicates:
            del self.duplicates[md5_hash]
        
        remaining_count = len(self.duplicates)
        self.duplicate_deleted.emit(md5_hash, len(deleted_paths), remaining_count)
        
        if self.is_all_processed():
            self.duplicate_all_processed.emit()
        
        debug_manager.log_info('重复图片组删除完成', 'duplicate', md5_hash=md5_hash, deleted_count=len(deleted_paths), failed_count=len(failed_paths))
        return deleted_paths, failed_paths
    
    def delete_selected_duplicates(self, md5_hash: str, selected_paths: List[str]) -> tuple:
        deleted_paths = []
        failed_paths = []
        debug_manager.log_info('开始删除选中的重复图片', 'duplicate', md5_hash=md5_hash, selected_count=len(selected_paths))
        
        total_to_delete = len(selected_paths)
        for i, path in enumerate(selected_paths):
            self.duplicate_processing.emit(i + 1, total_to_delete)
            try:
                os.remove(path)
                deleted_paths.append(path)
                debug_manager.log_info('删除选中图片成功', 'duplicate', path=path)
            except Exception as e:
                failed_paths.append(f"{path}: {e}")
                debug_manager.log_exception(e, 'duplicate', path=path)
        
        if md5_hash:
            self.classifier.add_processed_duplicate(md5_hash, deleted_paths)
        
        if md5_hash and md5_hash in self.duplicates:
            del self.duplicates[md5_hash]
        
        remaining_count = len(self.duplicates)
        self.duplicate_deleted.emit(md5_hash, len(deleted_paths), remaining_count)
        
        if self.is_all_processed():
            self.duplicate_all_processed.emit()
        
        debug_manager.log_info('选中重复图片删除完成', 'duplicate', md5_hash=md5_hash, deleted_count=len(deleted_paths), failed_count=len(failed_paths))
        return deleted_paths, failed_paths
    
    def is_all_processed(self) -> bool:
        return len(self.duplicates) == 0
    
    def clear_all_duplicate_memory(self):
        self.classifier.clear_duplicate_memory()
        self.duplicate_memory_cleared.emit()
    
    def add_processed_image(self, path: str):
        self.processed_images.add(path)
    
    def remove_processed_image(self, path: str):
        self.processed_images.discard(path)
    
    def load_cached_duplicates(self):
        debug_manager.log_info('加载缓存的重复图片', 'duplicate')
        cache = self.classifier.load_hash_cache()
        if cache and 'duplicates' in cache:
            self.set_duplicates(cache['duplicates'])
            debug_manager.log_info('缓存重复图片加载成功', 'duplicate', group_count=len(self.duplicates))
        else:
            debug_manager.log_info('缓存中无重复图片数据', 'duplicate')
            self.duplicates = {}