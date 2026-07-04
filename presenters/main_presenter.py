import os
from typing import List, Dict, Tuple, Optional

from core.scan_thread import ScanThread
from core.classification_manager import ClassificationManager
from services.duplicate_service import DuplicateService
from services.classification_service import ClassificationService
from services.hash_analysis_service import HashAnalysisService
from core.debug_manager import debug_manager


class MainPresenter:
    def __init__(self, view):
        self.view = view
        self._init_services()
        self._init_state()

    def _init_services(self):
        self.classifier = ClassificationManager()
        self.duplicate_service = DuplicateService(self.classifier)
        self.classification_service = ClassificationService(self.classifier)

    def _init_state(self):
        self.hash_scanning = False
        self.hash_completed = False
        self.hash_list = []
        self.group_rotations = {}

    def load_initial_data(self):
        self.classifier.load_config()
        shortcuts = self.classifier.get_all_shortcuts()
        recent_folders = self.classifier.get_recent_folders()
        
        self.view.update_shortcuts(shortcuts)
        self.view.update_recent_folders(recent_folders)
        
        if self.classifier.last_folder:
            self.view.set_status(f"上次分类: {os.path.basename(self.classifier.last_folder)}")
        else:
            self.view.set_status("请选择图片文件夹开始分类")

        self.check_unfinished_session()

    def check_unfinished_session(self):
        session = self.classifier.get_unfinished_session()
        if not session:
            return

        folder_path = session.get('folder_path', "")
        total_count = session.get('total_count', 0)
        processed_count = session.get('processed_count', 0)

        if total_count == 0:
            return

        remaining = total_count - processed_count
        self.view.show_unfinished_session_dialog(
            folder_path, total_count, processed_count, remaining,
            self.on_unfinished_session_continue,
            self.on_unfinished_session_cancel
        )

    def on_unfinished_session_continue(self, folder_path):
        self.start_scanning(folder_path)

    def on_unfinished_session_cancel(self):
        self.classifier.clear_unfinished_session()

    def select_folder(self):
        self.view.show_folder_dialog(self.on_folder_selected)

    def on_folder_selected(self, folder_path):
        if not folder_path:
            debug_manager.log_info('用户取消选择文件夹', 'folder')
            return
        debug_manager.log_info('用户选择文件夹', 'folder', folder_path=folder_path)
        self.start_scanning(folder_path)

    def start_scanning(self, folder_path: str):
        """启动文件夹扫描流程。

        公开方法，供 View 层（如最近文件夹选择）和内部回调统一调用。
        设置状态、重置哈希列表、启动后台扫描线程。
        """
        self.view.set_status("正在扫描图片...")
        self.view.hide_threshold_group()
        self.hash_list = []

        self.scan_thread = ScanThread(folder_path)
        # 使用 Qt 信号连接，自动跨线程调度到主线程执行
        self.scan_thread.progress.connect(self.on_scan_progress)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_scan_error)
        self.scan_thread.start()

    def on_scan_progress(self, current: int, total: int):
        self.view.set_status(f"正在扫描: {current}/{total}")

    def on_scan_finished(self, image_paths: list):
        debug_manager.log_info('扫描完成', 'scan', image_count=len(image_paths))

        folder_path = self.scan_thread.folder_path
        self._post_scan_setup(folder_path, image_paths)

        if not image_paths:
            self.view.set_status("未找到图片")
            return

        self.view.show_current_image()
        self.view.set_status(f"扫描完成，共 {len(image_paths)} 张图片")

        files_changed, changed_files = self.classifier.check_files_changed(image_paths)
        if files_changed:
            debug_manager.log_info('文件有变化，开始哈希分析', 'hash', changed_count=len(changed_files))
            self._start_hash_analysis(image_paths)
        else:
            debug_manager.log_info('文件无变化，跳过哈希分析', 'hash')
            self.hash_completed = True
            self._load_cached_hash_results(image_paths)

    def on_scan_error(self, error_message: str):
        debug_manager.log_error('扫描错误', 'scan', error=error_message)
        self.view.set_status("扫描失败")
        self.view.show_error_message(error_message)

    def _post_scan_setup(self, folder_path: str, image_paths: list):
        self.classifier.load_config(folder_path)
        self.classifier.load_duplicate_memory()
        
        shortcuts = self.classifier.get_all_shortcuts()
        recent_folders = self.classifier.get_recent_folders()
        
        self.view.update_shortcuts(shortcuts)
        self.view.update_recent_folders(recent_folders)
        
        self.classification_service.set_groups([[path] for path in image_paths])
        self.group_rotations = {}

    def _start_hash_analysis(self, image_paths: list):
        self.hash_scanning = True
        self.hash_completed = False

        threshold = self.classifier.get_hash_threshold()
        debug_manager.log_info('启动哈希分析', 'hash', image_count=len(image_paths), threshold=threshold)
        
        cache = self.classifier.load_hash_cache()
        cached_file_hashes = cache.get('file_hashes', {})
        debug_manager.log_info('加载缓存文件哈希', 'hash', cached_count=len(cached_file_hashes))
        
        hash_service = HashAnalysisService(threshold)
        hash_service.image_paths = image_paths
        hash_service.set_cached_hashes(cached_file_hashes)

        self.view.show_hash_analysis_dialog(
            hash_service,
            self.on_hash_progress_update,
            self.on_hash_finished,
            self.on_hash_canceled,
            self.on_hash_error,
            self.on_hash_threshold_changed
        )

    def on_hash_progress_update(self, current: int, total: int, stage: str, filename: str, processed_count: int, stage_progress: int = 0):
        self.view.set_status(f"后台分析相似度: {stage} ({current}/{total})")

    def on_hash_threshold_changed(self, threshold: int):
        debug_manager.log_info('用户调整哈希阈值', 'hash', threshold=threshold)
        self.classifier.set_hash_threshold(threshold)
        self.view.update_threshold(threshold)

    def on_threshold_changed(self, threshold: int):
        """主窗口阈值变化（防抖后触发）：执行重分组等重量级操作。

        View 层已即时更新数字显示并防抖，此处无需再调用 update_threshold_display。
        """
        debug_manager.log_info('主窗口阈值变化', 'hash', threshold=threshold)
        self.classifier.set_hash_threshold(threshold)

        if self.hash_completed and self.hash_list:
            debug_manager.log_info('重新分组', 'hash', threshold=threshold, hash_count=len(self.hash_list))
            # 调用 HashAnalysisService 的无状态静态方法重新分组，耦合度低可接受
            groups = HashAnalysisService.group_by_similarity(self.hash_list, threshold)
            self._apply_groups(groups)

            all_image_paths = []
            for group in groups:
                all_image_paths.extend(group)
            cache = self.classifier.build_hash_cache(
                all_image_paths, groups, self.duplicate_service.get_duplicates(), self.hash_list
            )
            self.classifier.save_hash_cache(cache)

            self.view.show_current_image()
            self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
            self._update_hash_status(groups, self.duplicate_service.get_duplicates())

    def on_hash_canceled(self):
        self.hash_scanning = False
        self.view.set_status("哈希分析已取消")
        debug_manager.log_info('哈希分析已取消', 'hash')

    def on_hash_error(self, error_message: str):
        debug_manager.log_error('哈希分析错误', 'hash', error=error_message)
        self.view.set_status("哈希分析失败")
        self.view.show_error_message(error_message)

    def on_hash_finished(self, groups: list, duplicates: dict, hash_list: list = None):
        debug_manager.log_info('哈希分析完成', 'hash', group_count=len(groups), duplicate_groups=len(duplicates))
        self.hash_scanning = False
        self.hash_completed = True

        if hash_list:
            self.hash_list = hash_list
            debug_manager.log_info('保存哈希列表', 'hash', hash_count=len(hash_list))

        self._apply_groups(groups)
        self.duplicate_service.set_duplicates(duplicates)

        all_image_paths = []
        for group in self.classification_service.get_groups():
            all_image_paths.extend(group)
        cache = self.classifier.build_hash_cache(all_image_paths, groups, duplicates, hash_list)
        debug_manager.log_info('保存哈希缓存', 'hash', file_hashes_count=len(cache.get('file_hashes', {})))
        self.classifier.save_hash_cache(cache)

        self.view.show_threshold_group()
        self.view.show_current_image()
        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        self._update_hash_status(groups, duplicates)

    def _apply_groups(self, groups: list):
        """应用相似度分组到分类服务。

        委托给 ClassificationService.apply_similar_groups，封装"过滤已处理图片 +
        未分组图片单独成组"的逻辑，避免表现层直接操作 service 内部状态。
        """
        self.classification_service.apply_similar_groups(groups)
        debug_manager.log_info('最终分组', 'hash', final_group_count=len(self.classification_service.get_groups()))

    def _update_hash_status(self, groups: list, duplicates: dict):
        if duplicates:
            total_duplicates = sum(len(p) - 1 for p in duplicates.values())
            self.view.set_status(f"分析完成: {len(groups)}组相似图片, {len(duplicates)}组重复({total_duplicates}张)")
        elif groups:
            self.view.set_status(f"分析完成: {len(groups)}组相似图片")
        else:
            self.view.set_status("分析完成: 未发现相似或重复图片")

    def _load_cached_hash_results(self, image_paths: list):
        debug_manager.log_info('加载缓存的哈希结果', 'hash')
        self.view.set_status("文件无变化，使用缓存结果")
        
        cache = self.classifier.load_hash_cache()
        similar_groups = cache.get('similar_groups', [])
        duplicates = cache.get('duplicates', {})
        hash_list = cache.get('hash_list', [])
        
        if hash_list:
            self.hash_list = hash_list
            self.hash_completed = True
            debug_manager.log_info('加载缓存的哈希列表', 'hash', hash_count=len(hash_list))
        
        if similar_groups:
            self._apply_groups(similar_groups)
            debug_manager.log_info('缓存相似分组加载完成', 'hash', group_count=len(self.classification_service.get_groups()))
        
        self.duplicate_service.set_duplicates(duplicates)
        
        if self.hash_completed and self.hash_list:
            self.view.show_threshold_group()
        
        self.view.show_current_image()
        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        
        remaining_duplicates = self.duplicate_service.get_duplicates()
        if remaining_duplicates:
            total_duplicates = sum(len(p) - 1 for p in remaining_duplicates.values())
            self.view.set_status(f"使用缓存: {len(self.classification_service.get_groups())}组, {len(remaining_duplicates)}组重复({total_duplicates}张)")
        else:
            self.view.set_status(f"使用缓存，共 {len(self.classification_service.get_groups())} 组")

    def next_image(self):
        current_index = self.classification_service.current_image_index
        current_group = self.classification_service.get_current_group()
        
        if current_index < len(current_group) - 1:
            self.classification_service.next_image()
            self.view.show_current_image()
        else:
            self.next_group()

    def prev_image(self):
        current_index = self.classification_service.current_image_index
        
        if current_index > 0:
            self.classification_service.prev_image()
            self.view.show_current_image()
        else:
            self.prev_group()

    def next_group(self):
        current_group_index = self.classification_service.current_group_index
        all_groups = self.classification_service.get_groups()
        
        if current_group_index < len(all_groups) - 1:
            self.classification_service.next_group()
            self.view.show_current_image()

    def prev_group(self):
        current_group_index = self.classification_service.current_group_index
        
        if current_group_index > 0:
            self.classification_service.prev_group()
            self.view.show_current_image()

    def rotate_image(self, clockwise: bool, angle: int = 90):
        current_group_index = self.classification_service.current_group_index
        
        if current_group_index not in self.group_rotations:
            self.group_rotations[current_group_index] = 0
        
        if clockwise:
            self.group_rotations[current_group_index] += angle
        else:
            self.group_rotations[current_group_index] -= angle
        
        self.group_rotations[current_group_index] %= 360
        
        self.view.show_current_image()

    def get_current_rotation(self) -> int:
        current_group_index = self.classification_service.current_group_index
        return self.group_rotations.get(current_group_index, 0)

    def classify_image(self, category: str):
        current_path = self.classification_service.get_current_image()
        if not current_path:
            return
        
        target_path = self.classifier.classify_image(current_path, category)
        if target_path:
            self.view.on_image_classified(current_path, target_path)
            self.classification_service.mark_processed(current_path)
            
            if self.hash_completed and self.hash_list:
                groups = HashAnalysisService.group_by_similarity(self.hash_list, self.classifier.get_hash_threshold())
                self._apply_groups(groups)
                
                cache = self.classifier.load_hash_cache()
                if cache:
                    cache['similar_groups'] = groups
                    self.classifier.save_hash_cache(cache)
            
            self.view.show_current_image()
            self.view.update_duplicate_list(self.duplicate_service.get_duplicates())

    def add_shortcut(self, key_string: str, folder_path: str):
        if self.classifier.add_shortcut(key_string, folder_path):
            shortcuts = self.classifier.get_all_shortcuts()
            self.view.update_shortcuts(shortcuts)
            self.view.show_info_message("快捷键已添加")
        else:
            self.view.show_error_message("添加快捷键失败")

    def remove_shortcut(self, key_string: str):
        if self.classifier.remove_shortcut(key_string):
            shortcuts = self.classifier.get_all_shortcuts()
            self.view.update_shortcuts(shortcuts)
            self.view.show_info_message("快捷键已删除")
        else:
            self.view.show_error_message("删除快捷键失败")

    def select_all_duplicates(self):
        self.view.select_all_duplicates()

    def deselect_all_duplicates(self):
        self.view.deselect_all_duplicates()

    def delete_selected_duplicates(self):
        selected_items = self.view.get_selected_duplicates()
        
        if not selected_items:
            self.view.show_warning_message("请选择要处理的重复图片组")
            return

        total_paths = sum(len(paths) for _, paths in selected_items)
        total_deletions = sum(len(paths) - 1 for _, paths in selected_items)

        self.view.show_delete_confirm_dialog(
            len(selected_items), total_paths, total_deletions,
            self.on_delete_confirmed
        )

    def on_delete_confirmed(self, selected_items):
        debug_manager.log_info('用户确认删除', 'duplicate', group_count=len(selected_items))
        
        for md5_hash, paths in selected_items:
            deleted_paths, failed_paths = self.duplicate_service.delete_duplicate_group(md5_hash, paths)
            for path in failed_paths:
                self.view.show_warning_message(f"删除失败: {path}")

        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        self.view.refresh_groups()

        if self.duplicate_service.is_all_processed():
            self.view.set_status("所有重复图片已处理完成")
            self.duplicate_service.clear_all_duplicate_memory()

    def show_duplicate_detail(self):
        duplicates = self.duplicate_service.get_duplicates()
        
        if not duplicates:
            self.view.show_info_message("暂无重复图片")
            return

        valid_groups = self.duplicate_service.get_valid_groups()
        if not valid_groups:
            self.view.show_info_message("暂无重复图片")
            return

        selected_items = self.view.get_selected_duplicates()
        
        if not selected_items:
            selected_items = [(valid_groups[0][0], valid_groups[0][1])]

        selected_groups = [paths for _, paths in selected_items]
        selected_md5s = [md5 for md5, _ in selected_items]

        self.view.show_duplicate_detail_dialog(selected_groups, selected_md5s, self.on_duplicate_detail_closed)

    def on_duplicate_detail_closed(self, deletions: list):
        """详情对话框关闭后，通过 service 执行删除。

        替代旧实现中直接修改 duplicate_service.duplicates 字典的做法，
        改用 DuplicateService.delete_selected_duplicates 统一处理文件删除、
        记忆保存和状态更新，保证数据一致性。

        Args:
            deletions: [(md5_hash, [selected_paths]), ...] 列表，由对话框返回
        """
        if not deletions:
            return

        debug_manager.log_info('执行详情对话框删除', 'duplicate', group_count=len(deletions))

        for md5_hash, selected_paths in deletions:
            deleted_paths, failed_paths = self.duplicate_service.delete_selected_duplicates(
                md5_hash, selected_paths
            )
            for path in failed_paths:
                self.view.show_warning_message(f"删除失败: {path}")

        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        self.view.refresh_groups()

        if self.duplicate_service.is_all_processed():
            self.view.set_status("所有重复图片已处理完成")
            self.duplicate_service.clear_all_duplicate_memory()

    def clear_storage(self):
        """清理存储：先从 classifier 获取数据 → 传给 view → 收到选中类别后执行清理。"""
        storage_size = self.classifier.get_storage_size()
        storage_details = self.classifier.get_storage_details()
        selected_categories = self.view.show_storage_clean_dialog(storage_size, storage_details)
        if selected_categories:
            self.classifier.clear_categories(selected_categories)
            self.view.show_info_message("存储已清理")
            self.view.update_shortcuts(self.classifier.get_all_shortcuts())

    def get_groups(self) -> list:
        return self.classification_service.get_groups()

    def get_current_image_path(self) -> Optional[str]:
        return self.classification_service.get_current_image()

    def get_current_group_index(self) -> int:
        return self.classification_service.current_group_index

    def get_current_image_index(self) -> int:
        return self.classification_service.current_image_index

    def get_total_groups(self) -> int:
        return len(self.classification_service.get_groups())

    def get_current_group_size(self) -> int:
        return len(self.classification_service.get_current_group())

    def get_duplicates(self) -> dict:
        return self.duplicate_service.get_duplicates()

    def get_hash_threshold(self) -> int:
        return self.classifier.get_hash_threshold()

    def get_recent_folders(self) -> list:
        return self.classifier.get_recent_folders()