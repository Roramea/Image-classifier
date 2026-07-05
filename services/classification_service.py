import os
from typing import List

from core.debug_manager import debug_manager


class ClassificationService:
    """分类服务：管理图片分组和当前定位状态。

    职责：维护分组数据、当前组/图片索引、已处理图片集合；
    提供分组切换和分类操作。不直接操作 UI，状态变化由 Presenter 读取并刷新视图。

    注：原继承 Observer 的事件机制因无订阅者已移除（死代码清理）。
    HashAnalysisService 仍保留 Observer，因其事件被 HashAnalysisDialog 真实订阅。
    """

    def __init__(self, classifier):
        self.classifier = classifier
        self.groups: List[List[str]] = []
        self.current_group_index = 0
        self.current_image_index = 0
        self.processed_images = set()
        debug_manager.log_info('ClassificationService 初始化完成', 'classification')

    def set_groups(self, groups: List[List[str]]):
        """设置当前分组数据。"""
        self.groups = groups
        debug_manager.log_info('设置分组', 'classification', group_count=len(groups), total_images=sum(len(g) for g in groups))

    def get_groups(self) -> List[List[str]]:
        return self.groups

    def get_current_group(self) -> List[str]:
        """获取当前组，自动校正越界索引。"""
        if not self.groups:
            return []
        if self.current_group_index < 0 or self.current_group_index >= len(self.groups):
            self.current_group_index = 0
        return self.groups[self.current_group_index]

    def get_current_image(self) -> str:
        """获取当前图片路径，自动校正越界索引。"""
        current_group = self.get_current_group()
        if not current_group:
            return ""
        if self.current_image_index < 0 or self.current_image_index >= len(current_group):
            self.current_image_index = 0
        return current_group[self.current_image_index]

    def remove_path(self, path: str) -> bool:
        """从分组中增量移除指定路径，避免全量 os.path.exists 扫描。

        Returns:
            是否找到了并移除了该路径
        """
        found = False
        new_groups = []
        for group in self.groups:
            if path in group:
                found = True
                filtered = [p for p in group if p != path]
                if filtered:
                    new_groups.append(filtered)
            else:
                new_groups.append(group)
        if found:
            self.groups = new_groups
            # 校正当前索引
            if self.current_group_index >= len(self.groups):
                self.current_group_index = max(0, len(self.groups) - 1)
            # 校正当前图片索引
            if self.groups and self.current_image_index >= len(self.groups[self.current_group_index]):
                self.current_image_index = max(0, len(self.groups[self.current_group_index]) - 1)
            debug_manager.log_info('增量移除路径', 'classification', path=path, remaining_groups=len(self.groups))
            return True
        return False

    def refresh_groups(self):
        """刷新分组：移除已不存在的图片路径，校正当前索引。

        仅用于需要全量校验的场景（如外部修改了文件）。
        分类等已知路径移除操作应使用 remove_path() 以获得更好性能。
        """
        debug_manager.log_info('刷新分组', 'classification', before_count=len(self.groups))
        valid_groups = []
        for group in self.groups:
            valid_paths = [p for p in group if os.path.exists(p)]
            if valid_paths:
                valid_groups.append(valid_paths)
        self.groups = valid_groups

        if self.current_group_index >= len(self.groups):
            self.current_group_index = max(0, len(self.groups) - 1)
        if self.groups and self.current_image_index >= len(self.groups[self.current_group_index]):
            self.current_image_index = max(0, len(self.groups[self.current_group_index]) - 1)
        debug_manager.log_info('分组刷新完成', 'classification', after_count=len(self.groups), new_group_index=self.current_group_index)

    def apply_similar_groups(self, similar_groups: list) -> list:
        """用相似度分组更新当前分组。

        过滤已处理图片，未分组的图片单独成组。此方法封装"合并相似分组与剩余单图"的逻辑，
        避免表现层直接操作 groups 内部状态。

        Args:
            similar_groups: 哈希分析得到的相似度分组结果

        Returns:
            更新后的分组列表
        """
        current_groups = self.groups
        processed_images = self.processed_images

        if not similar_groups:
            debug_manager.log_info('未找到相似图片，保留原始分组', 'classification', original_group_count=len(current_groups))
            return current_groups

        filtered_groups = []
        similar_images = set()
        for group in similar_groups:
            filtered_group = [path for path in group if path not in processed_images]
            if filtered_group:
                filtered_groups.append(filtered_group)
                similar_images.update(filtered_group)

        for group in current_groups:
            for path in group:
                if path not in similar_images and path not in processed_images:
                    filtered_groups.append([path])

        debug_manager.log_info('应用相似分组完成', 'classification', final_group_count=len(filtered_groups))
        self.groups = filtered_groups
        return filtered_groups

    def prev_image(self):
        """切换到上一张图片；当前组只有一张时跳转到上一组。"""
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

    def next_image(self):
        """切换到下一张图片；当前组只有一张时跳转到下一组。"""
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

    def prev_group(self):
        """切换到上一个分组，重置图片索引为 0。"""
        debug_manager.log_info('上一个分组', 'classification', group_index=self.current_group_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换分组', 'classification')
            return
        self.current_group_index = (self.current_group_index - 1) % len(self.groups)
        self.current_image_index = 0

    def next_group(self):
        """切换到下一个分组，重置图片索引为 0。"""
        debug_manager.log_info('下一个分组', 'classification', group_index=self.current_group_index)
        if not self.groups:
            debug_manager.log_warning('没有分组，无法切换分组', 'classification')
            return
        self.current_group_index = (self.current_group_index + 1) % len(self.groups)
        self.current_image_index = 0

    def mark_processed(self, path: str):
        """标记图片为已处理并从分组中移除该路径（增量操作，性能更好）。"""
        self.processed_images.add(path)
        self.remove_path(path)

    def rename_path(self, old_path: str, new_path: str) -> bool:
        """将分组和已处理集合中的旧路径替换为新路径。

        返回是否找到了旧路径并替换成功。
        """
        found = False
        # 更新 groups 中的路径
        for i, group in enumerate(self.groups):
            for j, img_path in enumerate(group):
                if img_path == old_path:
                    self.groups[i][j] = new_path
                    found = True
                    # 如果是当前图片，当前索引不需要变（位置没变）
        # 更新 processed_images
        if old_path in self.processed_images:
            self.processed_images.remove(old_path)
            self.processed_images.add(new_path)
            found = True
        if found:
            debug_manager.log_info('路径重命名', 'classification', old=old_path, new=new_path)
        return found
