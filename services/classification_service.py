import os
from typing import List

from PyQt5.QtCore import QObject, pyqtSignal

from core.debug_manager import debug_manager


class ClassificationService(QObject):
    classification_progress = pyqtSignal(int, int, str)
    classification_complete = pyqtSignal()
    image_moved = pyqtSignal(str, str, bool)
    group_changed = pyqtSignal(int, int, int, int)
    
    def __init__(self, classifier):
        super().__init__()
        self.classifier = classifier
        self.groups: List[List[str]] = []
        self.current_group_index = 0
        self.current_image_index = 0
        self.processed_images = set()
        debug_manager.log_info('ClassificationService 初始化完成', 'classification')
    
    def set_groups(self, groups: List[List[str]]):
        self.groups = groups
        debug_manager.log_info('设置分组', 'classification', group_count=len(groups), total_images=sum(len(g) for g in groups))
    
    def get_groups(self) -> List[List[str]]:
        return self.groups
    
    def get_current_group(self) -> List[str]:
        if not self.groups:
            return []
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        return self.groups[self.current_group_index]
    
    def get_current_image(self) -> str:
        current_group = self.get_current_group()
        if not current_group:
            return ""
        if self.current_image_index < 0 or self.current_image_index >= len(current_group):
            self.current_image_index = 0
        return current_group[self.current_image_index]
    
    def classify_current_group(self, shortcut: str) -> tuple:
        debug_manager.log_info('开始分类当前组', 'classification', shortcut=shortcut, group_index=self.current_group_index)
        if not self.groups:
            debug_manager.log_warning('没有分组可分类', 'classification')
            return 0, []
        
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        
        current_group = self.groups[self.current_group_index]
        folder_name = os.path.basename(self.classifier.get_folder(shortcut))
        debug_manager.log_info('分类组信息', 'classification', group_size=len(current_group), folder_name=folder_name)
        
        success_count = 0
        failed_paths = []
        
        for path in current_group:
            success = self.classifier.classify_image(path, shortcut)
            if success:
                success_count += 1
                self.processed_images.add(path)
                self.image_moved.emit(path, folder_name, True)
            else:
                failed_paths.append(path)
                self.image_moved.emit(path, folder_name, False)
        
        self.refresh_groups()
        
        total_images = sum(len(g) for g in self.groups) + len(self.processed_images)
        progress_str = f"已分类 {len(self.processed_images)}/{total_images}"
        self.classification_progress.emit(len(self.processed_images), total_images, progress_str)
        
        if self.is_classification_complete():
            self.classification_complete.emit()
        
        return success_count, failed_paths
    
    def refresh_groups(self):
        debug_manager.log_info('刷新分组', 'classification', before_count=len(self.groups))
        valid_groups = []
        for group in self.groups:
            valid_paths = [p for p in group if os.path.exists(p)]
            if valid_paths:
                valid_groups.append(valid_paths)
        self.groups = valid_groups
        
        if self.current_group_index >= len(self.groups):
            self.current_group_index = max(0, len(self.groups) - 1)
        debug_manager.log_info('分组刷新完成', 'classification', after_count=len(self.groups), new_group_index=self.current_group_index)
    
    def prev_image(self):
        debug_manager.log_info('上一张图片', 'classification', group_index=self.current_group_index, image_index=self.current_image_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换图片', 'classification')
            return
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        current_group = self.groups[self.current_group_index]
        if len(current_group) == 1:
            debug_manager.log_info('当前组只有一张图片，跳转到上一组', 'classification')
            self.prev_group()
        else:
            self.current_image_index = (self.current_image_index - 1) % len(current_group)
            self.group_changed.emit(self.current_group_index, len(self.groups), self.current_image_index, len(current_group))
    
    def next_image(self):
        debug_manager.log_info('下一张图片', 'classification', group_index=self.current_group_index, image_index=self.current_image_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换图片', 'classification')
            return
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        current_group = self.groups[self.current_group_index]
        if len(current_group) == 1:
            debug_manager.log_info('当前组只有一张图片，跳转到下一组', 'classification')
            self.next_group()
        else:
            self.current_image_index = (self.current_image_index + 1) % len(current_group)
            self.group_changed.emit(self.current_group_index, len(self.groups), self.current_image_index, len(current_group))
    
    def prev_group(self):
        debug_manager.log_info('上一个分组', 'classification', group_index=self.current_group_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换分组', 'classification')
            return
        self.current_group_index = (self.current_group_index - 1) % len(self.groups)
        self.current_image_index = 0
        current_group = self.groups[self.current_group_index]
        self.group_changed.emit(self.current_group_index, len(self.groups), self.current_image_index, len(current_group))
    
    def next_group(self):
        debug_manager.log_info('下一个分组', 'classification', group_index=self.current_group_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换分组', 'classification')
            return
        self.current_group_index = (self.current_group_index + 1) % len(self.groups)
        self.current_image_index = 0
        current_group = self.groups[self.current_group_index]
        self.group_changed.emit(self.current_group_index, len(self.groups), self.current_image_index, len(current_group))
    
    def get_group_count(self) -> int:
        return len(self.groups)
    
    def get_image_count_in_current_group(self) -> int:
        current_group = self.get_current_group()
        return len(current_group)
    
    def get_current_group_index(self) -> int:
        return self.current_group_index
    
    def get_current_image_index(self) -> int:
        return self.current_image_index
    
    def is_classification_complete(self) -> bool:
        return len(self.groups) == 0
    
    def reset(self):
        self.groups = []
        self.current_group_index = 0
        self.current_image_index = 0
        self.processed_images = set()