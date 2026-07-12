import os
from typing import List, Dict, Tuple, Optional

from PyQt5.QtCore import QTimer

from core.scan_thread import ScanThread
from core.classification_manager import ClassificationManager
from services.duplicate_service import DuplicateService
from services.classification_service import ClassificationService
from services.hash_analysis_service import HashAnalysisService
from services.image_cache_service import ImageCacheService
from core.debug_manager import debug_manager
from views.i_main_view import IMainView


class MainPresenter:
    def __init__(self, view: IMainView):
        self.view = view
        self._init_services()
        self._init_state()

    def _init_services(self):
        self.classifier = ClassificationManager()
        self.duplicate_service = DuplicateService(self.classifier)
        self.classification_service = ClassificationService(self.classifier)
        self.image_cache_service = ImageCacheService()

    def _init_state(self):
        self.hash_scanning = False
        self.hash_completed = False
        self.hash_list = []
        self.group_rotations = {}
        self._resuming_session = False
        self._pending_session_data = None

        self._threshold_timer = QTimer()
        self._threshold_timer.setSingleShot(True)
        self._threshold_timer.setInterval(300)
        self._threshold_timer.timeout.connect(self._apply_threshold)
        self._pending_threshold = None

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
        """用户选择继续未完成会话：启动扫描，待扫描完成后恢复进度。"""
        session = self.classifier.get_unfinished_session()
        self._resuming_session = True
        self._pending_session_data = session
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
        切换文件夹前先保存当前哈希缓存，再重置状态、启动后台扫描线程。
        """
        # 切换文件夹前保存当前哈希缓存，避免内存中的哈希数据丢失
        self._save_current_hash_cache()

        self.view.set_status("正在扫描图片...")
        self.hash_list = []
        self.hash_completed = False

        self.scan_thread = ScanThread(folder_path)
        # 使用 Qt 信号连接，自动跨线程调度到主线程执行
        self.scan_thread.progress.connect(self.on_scan_progress)
        self.scan_thread.finished.connect(self.on_scan_finished)
        self.scan_thread.error.connect(self.on_scan_error)
        self.scan_thread.start()

    def _save_current_hash_cache(self):
        """保存当前内存中的哈希状态到磁盘缓存。

        在切换文件夹或关闭应用时调用，确保持久化最新的哈希数据。
        若无当前文件夹或无 hash_list 数据则跳过。
        """
        if not self.classifier.current_folder:
            return
        if not self.hash_list:
            return

        # 当前剩余的图片路径（用于文件元信息缓存）
        all_image_paths = []
        for group in self.classification_service.get_groups():
            all_image_paths.extend(group)

        # 重新分组以反映最新状态
        threshold = self.classifier.get_hash_threshold()
        groups = HashAnalysisService.group_by_similarity(self.hash_list, threshold)

        cache = self.classifier.build_hash_cache(
            all_image_paths, groups,
            self.duplicate_service.get_duplicates(), self.hash_list
        )
        self.classifier.save_hash_cache(cache)
        debug_manager.log_info('哈希缓存已保存', 'hash',
                               folder=self.classifier.current_folder,
                               hash_count=len(self.hash_list))

    def _incremental_update_hash(self, image_paths: list, changed_files: list, cache: dict):
        """对新增/变化的图片增量计算哈希，合并到现有缓存。

        相比完整哈希分析（弹出对话框），此方法直接在主线程快速完成：
        - 从缓存 hash_list 中移除已删除的图片
        - 只对 changed_files 计算 md5 和 img_hash
        - 合并后重新分组并保存缓存

        Args:
            image_paths: 当前扫描到的所有图片路径
            changed_files: 新增或修改的文件路径列表
            cache: 已加载的哈希缓存字典
        """
        from core.image_scanner import ImageScanner

        debug_manager.log_info('增量更新哈希', 'hash',
                               total=len(image_paths), changed=len(changed_files))

        cached_hash_list = cache.get('hash_list', [])
        cached_file_hashes = cache.get('file_hashes', {})

        # 从 hash_list 中移除已删除的图片（不在当前 image_paths 中的）
        current_path_set = set(image_paths)
        hash_list = [(p, h) for p, h in cached_hash_list if p in current_path_set]
        removed_count = len(cached_hash_list) - len(hash_list)
        if removed_count:
            debug_manager.log_info('移除已删除图片的哈希', 'hash', removed_count=removed_count)

        # 对 changed_files 计算哈希
        scanner = ImageScanner()
        existing_paths = {p for p, _ in hash_list}
        changed_path_set = set(changed_files)

        for path in changed_files:
            # 修改的文件先移除旧哈希
            if path in existing_paths:
                hash_list = [(p, h) for p, h in hash_list if p != path]

            img_hash = scanner.compute_image_hash(path)
            if img_hash:
                hash_list.append((path, img_hash))

        self.hash_list = hash_list
        self.hash_completed = True

        # 重新分组
        threshold = self.classifier.get_hash_threshold()
        groups = HashAnalysisService.group_by_similarity(hash_list, threshold)

        # 增量计算 MD5 用于重复检测
        md5_map = {}
        for path in image_paths:
            if path in changed_path_set:
                md5 = scanner.compute_md5(path)
            elif path in cached_file_hashes and 'md5' in cached_file_hashes[path]:
                md5 = cached_file_hashes[path]['md5']
            else:
                md5 = scanner.compute_md5(path)
            if md5:
                md5_map.setdefault(md5, []).append(path)

        duplicates = {md5: paths for md5, paths in md5_map.items() if len(paths) > 1}

        # 应用分组
        self._apply_groups(groups)
        self.duplicate_service.set_duplicates(duplicates)

        # 保存缓存
        all_image_paths = []
        for group in self.classification_service.get_groups():
            all_image_paths.extend(group)

        new_cache = self.classifier.build_hash_cache(
            all_image_paths, groups, duplicates, hash_list
        )
        self.classifier.save_hash_cache(new_cache)

        # 更新 UI
        self.view.show_current_image()
        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        self._update_hash_status(groups, duplicates)

        debug_manager.log_info('增量更新完成', 'hash',
                               hash_count=len(hash_list),
                               group_count=len(groups),
                               duplicate_count=len(duplicates))

    def on_scan_progress(self, current: int, total: int):
        self.view.set_status(f"正在扫描: {current}/{total}")

    def on_scan_finished(self, image_paths: list):
        debug_manager.log_info('扫描完成', 'scan', image_count=len(image_paths))

        folder_path = self.scan_thread.folder_path
        self._post_scan_setup(folder_path, image_paths)

        if not image_paths:
            self.view.set_status("未找到图片")
            return

        # 若为恢复未完成会话，则还原进度（已处理图片、当前索引）
        if self._resuming_session and self._pending_session_data:
            self._restore_session_progress(self._pending_session_data, image_paths)
            self._resuming_session = False
            self._pending_session_data = None

        self.view.show_current_image()
        self.view.set_status(f"扫描完成，共 {len(image_paths)} 张图片")

        files_changed, changed_files = self.classifier.check_files_changed(image_paths)
        if files_changed:
            cache = self.classifier.load_hash_cache()
            cached_hash_list = cache.get('hash_list', [])

            if cached_hash_list and changed_files and len(changed_files) < len(image_paths):
                # 有缓存且仅部分文件变化：增量更新，不弹出哈希分析对话框
                debug_manager.log_info('检测到新增/变化文件，增量更新哈希', 'hash',
                                       changed_count=len(changed_files), cached_count=len(cached_hash_list))
                self.view.set_status(f"正在增量分析 {len(changed_files)} 张新图片...")
                self._incremental_update_hash(image_paths, changed_files, cache)
            else:
                # 无缓存或大量变化：启动完整哈希分析（弹出对话框）
                debug_manager.log_info('文件有变化，开始完整哈希分析', 'hash', changed_count=len(changed_files))
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
        # 将当前文件夹保存到最近列表（扫描完成即记录，不依赖分类操作）
        self.classifier.save_recent_folders(folder_path)

        shortcuts = self.classifier.get_all_shortcuts()
        recent_folders = self.classifier.get_recent_folders()

        self.view.update_shortcuts(shortcuts)
        self.view.update_recent_folders(recent_folders)
        # 切换文件夹时清除图片缓存，避免旧图片占用内存
        self.view.invalidate_image_cache()

        self.classification_service.set_groups([[path] for path in image_paths])
        self.classification_service.clear_classify_history()
        self.group_rotations = {}

    def _restore_session_progress(self, session: dict, image_paths: list):
        """恢复未完成会话的进度：已处理图片、当前图片索引。

        从 session 中读取 processed_images（路径列表）和 current_image（当前图片路径），
        还原到 ClassificationService 中。若路径已不存在则跳过。
        """
        processed = session.get('processed_images', [])
        current_image = session.get('current_image', "")
        debug_manager.log_info(
            '恢复未完成会话进度', 'session',
            processed_count=len(processed), current_image=current_image
        )
        # 还原已处理图片（仅保留当前仍存在的图片路径）
        valid_processed = [p for p in processed if p in image_paths]
        for p in valid_processed:
            self.classification_service.mark_processed(p)
        # 还原当前图片索引：遍历分组找到图片所在的组和组内位置
        if current_image:
            groups = self.classification_service.get_groups()
            for group_idx, group in enumerate(groups):
                if current_image in group:
                    self.classification_service.current_group_index = group_idx
                    self.classification_service.current_image_index = group.index(current_image)
                    debug_manager.log_info(
                        '会话进度恢复完成', 'session',
                        group_index=group_idx, image_index=group.index(current_image)
                    )
                    break
        # 恢复后清除未完成会话标记（用户已继续，会话生效）
        self.classifier.clear_unfinished_session()

    def on_app_close(self):
        """应用关闭时的清理工作：保存哈希缓存和未完成会话。

        先保存当前哈希缓存（避免内存数据丢失），再保存未完成会话。
        """
        debug_manager.log_info('应用关闭，执行清理', 'session')
        # 保存当前哈希缓存
        self._save_current_hash_cache()

        if not self.classifier.current_folder:
            debug_manager.log_info('无当前文件夹，跳过会话保存', 'session')
            return
        groups = self.classification_service.get_groups()
        total = sum(len(g) for g in groups)
        if total == 0:
            debug_manager.log_info('无图片数据，跳过会话保存', 'session')
            self.classifier.clear_unfinished_session()
            return
        processed = self.classification_service.processed_images
        processed_count = len(processed)
        # 全部处理完成则清除未完成会话
        if processed_count >= total:
            debug_manager.log_info('分类已全部完成，清除未完成会话', 'session')
            self.classifier.clear_unfinished_session()
            return
        # 保存未完成会话
        current_image = self.classification_service.get_current_image()
        session_data = {
            'folder_path': self.classifier.current_folder,
            'total_count': total,
            'processed_count': processed_count,
            'remaining': total - processed_count,
            'current_image': current_image,
            'processed_images': list(processed),
        }
        self.classifier.save_unfinished_session(session_data)
        debug_manager.log_info(
            '未完成会话已保存', 'session',
            folder=self.classifier.current_folder,
            processed=processed_count, total=total
        )

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
        """主窗口阈值变化：更新数字显示并启动防抖定时器，延迟执行重分组。

        拖动时 valueChanged 高频触发，若每次都执行 group_by_similarity(O(n²)) +
        磁盘 IO + UI 刷新会导致明显卡顿。防抖 300ms 后才执行重量级操作。
        """
        self._pending_threshold = threshold
        self._threshold_timer.start()

    def _apply_threshold(self):
        """防抖超时后执行：调用分类器进行重分组等重量级操作。"""
        if self._pending_threshold is not None:
            threshold = self._pending_threshold
            self._pending_threshold = None
            debug_manager.log_info('主窗口阈值变化', 'hash', threshold=threshold)
            self.classifier.set_hash_threshold(threshold)
            self.view.sync_hash_dialog_threshold(threshold)

            if self.hash_completed and self.hash_list:
                debug_manager.log_info('重新分组', 'hash', threshold=threshold, hash_count=len(self.hash_list))
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
        else:
            self.classification_service.next_group()
        self.view.show_current_image()

    def prev_image(self):
        current_index = self.classification_service.current_image_index

        if current_index > 0:
            self.classification_service.prev_image()
        else:
            self.classification_service.prev_group()
            current_group = self.classification_service.get_current_group()
            if current_group:
                self.classification_service.current_image_index = len(current_group) - 1
        self.view.show_current_image()

    def next_group(self):
        self.classification_service.next_group()
        self.view.show_current_image()

    def prev_group(self):
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
            self.classification_service.add_classify_history(current_path, target_path, category)
            self.view.on_image_classified(current_path, target_path)
            self.classification_service.mark_processed(current_path)

            if self.hash_completed and self.hash_list:
                self._remove_from_hash_list(current_path)

            self.view.show_current_image()
            self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
            self.view.update_undo_btn_state()

            target_folder = os.path.basename(os.path.dirname(target_path))
            filename = os.path.basename(current_path)
            total_processed = len(self.classification_service.processed_images)
            total_groups = self.classification_service.get_groups()
            total_images = sum(len(g) for g in total_groups) + total_processed
            self.view.set_status(f"已分类: {filename} -> {target_folder} ({total_processed}/{total_images})")

    def _remove_from_hash_list(self, path: str):
        """从 hash_list 中增量移除指定路径，避免 O(n²) 重新分组。"""
        new_hash_list = [(p, h) for p, h in self.hash_list if p != path]
        if len(new_hash_list) != len(self.hash_list):
            self.hash_list = new_hash_list
            debug_manager.log_info('hash_list 增量移除', 'hash', removed=path, remaining=len(self.hash_list))

    def _sync_hash_list_with_groups(self):
        """同步 hash_list 与当前分组状态：只保留当前分组中存在的图片路径。
        
        在分类撤回等操作后调用，确保 hash_list 与分类服务的分组状态保持一致。
        """
        if not self.hash_completed or not self.hash_list:
            return

        current_paths = set()
        for group in self.classification_service.get_groups():
            current_paths.update(group)

        old_count = len(self.hash_list)
        self.hash_list = [(p, h) for p, h in self.hash_list if p in current_paths]
        
        if len(self.hash_list) != old_count:
            debug_manager.log_info('hash_list 同步完成', 'hash', 
                                  removed=old_count - len(self.hash_list), 
                                  remaining=len(self.hash_list))

    def undo_classify(self):
        """撤回最后一次分类操作。"""
        record = self.classification_service.pop_classify_history()
        if not record:
            self.view.set_status("没有可撤回的分类操作")
            return

        original_path = record['original_path']
        target_path = record['target_path']

        if not os.path.exists(target_path):
            self.view.show_warning_message(f"文件不存在: {target_path}")
            return

        try:
            import shutil
            shutil.move(target_path, original_path)
            debug_manager.log_info('分类撤回成功', 'classification', 
                                  original=original_path, target=target_path)

            self.classification_service.add_path_back(original_path)

            if self.hash_completed and self.hash_list:
                self._sync_hash_list_with_groups()

            self.view.invalidate_image_cache(target_path)
            self.view.show_current_image()
            self.view.update_duplicate_list(self.duplicate_service.get_duplicates())

            filename = os.path.basename(original_path)
            total_processed = len(self.classification_service.processed_images)
            total_groups = self.classification_service.get_groups()
            total_images = sum(len(g) for g in total_groups) + total_processed
            self.view.set_status(f"已撤回: {filename} ({total_processed}/{total_images})")
        except Exception as e:
            debug_manager.log_exception(e, 'classification', 
                                       original=original_path, target=target_path)
            self.view.show_error_message(f"撤回失败: {str(e)}")

    def has_undo_history(self) -> bool:
        """检查是否有可撤回的分类记录。"""
        return self.classification_service.classify_history != []

    def add_shortcut(self, key_string: str, folder_path: str):
        if not self.classifier.current_folder:
            self.view.show_error_message("请先选择要分类的图片文件夹")
            return
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

    def get_shortcuts(self) -> dict:
        """获取当前快捷键映射，供 View 层按键匹配使用。"""
        return self.classifier.get_all_shortcuts()

    def handle_key_press(self, key_str: str) -> bool:
        """处理按键事件，匹配快捷键映射触发分类。

        Args:
            key_str: 按键字符串（已转换为小写）

        Returns:
            True if a shortcut was matched and classification was triggered, False otherwise
        """
        shortcuts = self.classifier.get_all_shortcuts()
        if key_str in shortcuts:
            debug_manager.log_info('快捷键触发分类', 'shortcut', key=key_str)
            self.classify_image(key_str)
            return True
        return False

    def rename_current_image(self, new_filename: str) -> Tuple[bool, str]:
        """重命名当前图片文件。

        Args:
            new_filename: 新文件名（仅文件名部分，不含扩展名）

        Returns:
            (是否成功, 消息文本)
        """
        old_path = self.classification_service.get_current_image()
        if not old_path or not os.path.exists(old_path):
            return False, "当前图片不存在"

        folder = os.path.dirname(old_path)
        old_name = os.path.basename(old_path)
        _, old_ext = os.path.splitext(old_name)

        # 处理新文件名：始终使用原文件的扩展名，忽略用户输入的扩展名
        new_name_base = os.path.splitext(new_filename)[0]
        new_filename = new_name_base + old_ext

        # 校验文件名不含非法字符
        invalid_chars = '<>:"/\\|?*'
        for ch in invalid_chars:
            if ch in new_filename:
                return False, f"文件名包含非法字符: {ch}"

        # Windows 保留名检查
        reserved_names = ['CON', 'PRN', 'AUX', 'NUL'] + \
                         [f'COM{i}' for i in range(1, 10)] + \
                         [f'LPT{i}' for i in range(1, 10)]
        if new_name_base.upper() in reserved_names:
            return False, f"文件名 '{new_name_base}' 是系统保留名"

        # 新路径
        new_path = os.path.join(folder, new_filename)

        # 同名文件已存在
        if os.path.exists(new_path) and os.path.abspath(new_path) != os.path.abspath(old_path):
            return False, f"文件已存在: {new_filename}"

        # 执行重命名
        try:
            os.rename(old_path, new_path)
        except OSError as e:
            debug_manager.log_exception('重命名文件失败', 'rename', error=str(e), old=old_path, new=new_path)
            return False, str(e)

        # 同步更新各服务中的路径引用
        self.classification_service.rename_path(old_path, new_path)
        self.duplicate_service.rename_path(old_path, new_path)

        # 同步哈希缓存（内存 + 磁盘）
        if self.hash_list:
            for i, (p, h) in enumerate(self.hash_list):
                if p == old_path:
                    self.hash_list[i] = (new_path, h)
                    break
        self.classifier.rename_in_hash_cache(old_path, new_path)

        # 刷新 UI：重复图片列表
        self.view.update_duplicate_list(self.duplicate_service.get_duplicates())
        # 清除图片缓存（旧路径失效）
        self.view.invalidate_image_cache(old_path)

        debug_manager.log_info('图片重命名成功', 'rename', old=old_name, new=new_filename)
        return True, f"{old_name} → {new_filename}"

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

    def get_image_from_cache(self, path: str):
        return self.image_cache_service.get(path)

    def cache_image(self, path: str, pixmap):
        self.image_cache_service.set(path, pixmap)

    def invalidate_image_cache(self, path: str = None):
        if path:
            self.image_cache_service.remove(path)
        else:
            self.image_cache_service.clear()

    def __getattr__(self, name):
        """动态委托未定义的方法到底层服务，减少无逻辑包装方法。"""
        if hasattr(self.classification_service, name):
            return getattr(self.classification_service, name)
        if hasattr(self.duplicate_service, name):
            return getattr(self.duplicate_service, name)
        if hasattr(self.classifier, name):
            return getattr(self.classifier, name)
        if hasattr(self.image_cache_service, name):
            return getattr(self.image_cache_service, name)
        raise AttributeError(f"'MainPresenter' object has no attribute '{name}'")