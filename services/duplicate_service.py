import os
from typing import Dict, List

from core.debug_manager import debug_manager


class DuplicateService:
    """重复图片服务：管理重复图片组的展示与删除。

    职责：维护 duplicates 字典（{md5: [paths]}）、执行重复图片删除、
    保存已处理记忆到 classifier。不直接操作 UI，状态变化由 Presenter 读取并刷新视图。

    注：原继承 Observer 的事件机制因无订阅者已移除（死代码清理）。
    """

    def __init__(self, classifier):
        self.classifier = classifier
        self.duplicates: Dict[str, List[str]] = {}
        self.processed_images = set()
        debug_manager.log_info('DuplicateService 初始化完成', 'duplicate')

    def set_duplicates(self, duplicates: Dict[str, List[str]]):
        """设置重复图片，过滤已处理的组。

        已通过 classifier.is_duplicate_processed 标记的组会被排除，
        避免已处理的重复组再次出现在列表中。
        """
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
        """返回有效重复组（路径数 > 1）的 (md5, paths) 列表。"""
        return [(md5, paths) for md5, paths in self.duplicates.items() if paths and len(paths) > 1]

    def delete_duplicate_group(self, md5_hash: str, paths: List[str]) -> tuple:
        """删除重复组：保留首张，删除其余。

        执行文件删除、记录已处理重复组到 classifier 记忆、从 duplicates 字典移除该组。
        此方法是批量删除（保留首张）场景的入口。

        Returns:
            (deleted_paths, failed_paths) 元组
        """
        deleted_paths = []
        failed_paths = []
        debug_manager.log_info('开始删除重复图片组', 'duplicate', md5_hash=md5_hash, path_count=len(paths))

        total_to_delete = len(paths) - 1
        for i, path in enumerate(paths[1:]):
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

        debug_manager.log_info('重复图片组删除完成', 'duplicate', md5_hash=md5_hash, deleted_count=len(deleted_paths), failed_count=len(failed_paths))
        return deleted_paths, failed_paths

    def delete_selected_duplicates(self, md5_hash: str, selected_paths: List[str]) -> tuple:
        """删除用户选中的重复图片（不强制保留首张）。

        执行文件删除、记录已处理重复组到 classifier 记忆、从 duplicates 字典移除该组。
        此方法是详情对话框选中删除场景的入口，由 Presenter 调用。

        Args:
            md5_hash: 重复组的 MD5 哈希值，可为 None（无 MD5 的相似组）
            selected_paths: 用户选中要删除的文件路径列表

        Returns:
            (deleted_paths, failed_paths) 元组
        """
        deleted_paths = []
        failed_paths = []
        debug_manager.log_info('开始删除选中的重复图片', 'duplicate', md5_hash=md5_hash, selected_count=len(selected_paths))

        for path in selected_paths:
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

        debug_manager.log_info('选中重复图片删除完成', 'duplicate', md5_hash=md5_hash, deleted_count=len(deleted_paths), failed_count=len(failed_paths))
        return deleted_paths, failed_paths

    def is_all_processed(self) -> bool:
        """是否所有重复组都已处理完成。"""
        return len(self.duplicates) == 0

    def clear_all_duplicate_memory(self):
        """清空 classifier 中已处理重复组的记忆。"""
        self.classifier.clear_duplicate_memory()

    def add_processed_image(self, path: str):
        self.processed_images.add(path)

    def remove_processed_image(self, path: str):
        self.processed_images.discard(path)

    def load_cached_duplicates(self):
        """从 classifier 哈希缓存加载重复图片。"""
        debug_manager.log_info('加载缓存的重复图片', 'duplicate')
        cache = self.classifier.load_hash_cache()
        if cache and 'duplicates' in cache:
            self.set_duplicates(cache['duplicates'])
            debug_manager.log_info('缓存重复图片加载成功', 'duplicate', group_count=len(self.duplicates))
        else:
            debug_manager.log_info('缓存中无重复图片数据', 'duplicate')
            self.duplicates = {}
