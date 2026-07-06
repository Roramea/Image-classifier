import time
from typing import List, Dict
from threading import Thread

from core.image_scanner import ImageScanner
from core.simple_hash import hamming_distance
from core.debug_manager import debug_manager
from core.observer import Observer


class HashAnalysisService(Observer):
    STAGE_NAMES = ["计算 MD5 哈希", "计算图像哈希", "分组相似度图片"]

    def __init__(self, threshold: int = 10):
        super().__init__()
        self.image_paths = []
        self.is_canceled = False
        self.current_stage = 0
        self.threshold = threshold
        self.cached_hashes = {}
    
    def set_threshold(self, threshold: int):
        self.threshold = threshold
        debug_manager.log_info('设置相似度阈值', 'hash', threshold=threshold)
    
    def set_cached_hashes(self, cached_hashes: dict):
        self.cached_hashes = cached_hashes
        debug_manager.log_info('设置缓存哈希', 'hash', cached_count=len(cached_hashes))

    def start_analysis(self, image_paths: List[str]):
        self.image_paths = image_paths
        self.is_canceled = False
        self.current_stage = 0

        thread = Thread(target=self._run_analysis_safe, daemon=True)
        thread.start()

    def cancel(self):
        self.is_canceled = True

    def _run_analysis_safe(self):
        try:
            self.run_analysis()
        except Exception as e:
            debug_manager.log_exception(e, 'hash', context='线程异常')
            self.emit('analysis_error', f"线程异常: {str(e)}")
            if not self.is_canceled:
                self.emit('analysis_finished', [], {}, [])

    def run_analysis(self):
        scanner = ImageScanner()
        
        need_md5_recalc = []
        need_img_hash_recalc = []
        cached_md5_map = {}
        cached_hash_list = []
        
        for path in self.image_paths:
            if path in self.cached_hashes:
                cached_data = self.cached_hashes[path]
                if 'md5' in cached_data:
                    md5 = cached_data['md5']
                    if md5 in cached_md5_map:
                        cached_md5_map[md5].append(path)
                    else:
                        cached_md5_map[md5] = [path]
                else:
                    need_md5_recalc.append(path)
                
                if 'img_hash' in cached_data:
                    cached_hash_list.append((path, cached_data['img_hash']))
                else:
                    need_img_hash_recalc.append(path)
            else:
                need_md5_recalc.append(path)
                need_img_hash_recalc.append(path)
        
        debug_manager.log_info('增量哈希计算', 'hash', 
                              total_images=len(self.image_paths),
                              cached_md5=len(self.image_paths) - len(need_md5_recalc),
                              cached_img_hash=len(self.image_paths) - len(need_img_hash_recalc),
                              need_recalc_md5=len(need_md5_recalc),
                              need_recalc_img_hash=len(need_img_hash_recalc))

        total_steps = len(self.image_paths) * 3

        self.current_stage = 1
        stage_name = self.STAGE_NAMES[0]
        debug_manager.log_info(f'开始{stage_name}', 'hash', total_images=len(self.image_paths), need_recalc=len(need_md5_recalc))
        self.emit('analysis_stage_changed', stage_name, 0, len(self.image_paths))

        md5_hash_map = cached_md5_map.copy()
        processed_count = len(self.image_paths) - len(need_md5_recalc)
        
        for i, path in enumerate(need_md5_recalc):
            if self.is_canceled:
                debug_manager.log_info('哈希分析已取消', 'hash')
                self.emit('analysis_canceled')
                return

            filename = self._extract_filename(path)
            progress = processed_count + i + 1
            stage_progress = int(progress / len(self.image_paths) * 100)
            self._emit_progress(progress, total_steps, stage_name, filename, progress, stage_progress)
            self.emit('analysis_file_processed', filename, progress, len(self.image_paths))

            try:
                md5 = scanner.compute_md5(path)
                if md5:
                    if md5 in md5_hash_map:
                        md5_hash_map[md5].append(path)
                    else:
                        md5_hash_map[md5] = [path]
            except Exception as md5_ex:
                debug_manager.log_warning('MD5计算失败', 'hash', filename=filename, error=str(md5_ex))
                continue

        duplicates = {md5: paths for md5, paths in md5_hash_map.items() if len(paths) > 1}
        debug_manager.log_info(f'{stage_name}完成', 'hash', duplicate_groups=len(duplicates))

        self.current_stage = 2
        stage_name = self.STAGE_NAMES[1]
        debug_manager.log_info(f'开始{stage_name}', 'hash', total_images=len(self.image_paths), need_recalc=len(need_img_hash_recalc))
        self.emit('analysis_stage_changed', stage_name, 0, len(self.image_paths))
        self._emit_progress(len(self.image_paths), total_steps, stage_name, "", len(self.image_paths), 0)

        hash_list = cached_hash_list.copy()
        processed_count = len(self.image_paths) - len(need_img_hash_recalc)
        
        for i, path in enumerate(need_img_hash_recalc):
            if self.is_canceled:
                debug_manager.log_info('哈希分析已取消', 'hash')
                self.emit('analysis_canceled')
                return

            filename = self._extract_filename(path)
            progress = len(self.image_paths) + processed_count + i + 1
            stage_progress = int((processed_count + i + 1) / len(self.image_paths) * 100)
            self._emit_progress(progress, total_steps, stage_name, filename, processed_count + i + 1, stage_progress)
            self.emit('analysis_file_processed', filename, processed_count + i + 1, len(self.image_paths))

            try:
                img_hash = scanner.compute_image_hash(path)
                if img_hash:
                    hash_list.append((path, img_hash))
            except Exception as hash_ex:
                debug_manager.log_warning('图像哈希计算失败', 'hash', filename=filename, error=str(hash_ex))
                continue

        debug_manager.log_info(f'{stage_name}完成', 'hash', hash_count=len(hash_list))

        self.current_stage = 3
        stage_name = self.STAGE_NAMES[2]
        hash_count = len(hash_list)
        debug_manager.log_info(f'开始{stage_name}', 'hash', hash_count=hash_count)
        self.emit('analysis_stage_changed', stage_name, 0, hash_count)
        self._emit_progress(len(self.image_paths) * 2, total_steps, stage_name, "", len(self.image_paths), 0)

        visited = set()
        groups = []

        for i, (path1, hash1) in enumerate(hash_list):
            if self.is_canceled:
                debug_manager.log_info('哈希分析已取消', 'hash')
                self.emit('analysis_canceled')
                return

            if path1 in visited:
                continue

            group = [path1]
            visited.add(path1)

            filename = self._extract_filename(path1)
            progress = len(self.image_paths) * 2 + i + 1
            stage_progress = int((i + 1) / hash_count * 100) if hash_count > 0 else 100
            self._emit_progress(progress, total_steps, stage_name, filename, len(self.image_paths), stage_progress)
            self.emit('analysis_file_processed', filename, i + 1, hash_count)

            try:
                for j in range(i + 1, len(hash_list)):
                    path2, hash2 = hash_list[j]
                    if path2 not in visited:
                        diff = hamming_distance(hash1, hash2)
                        if diff <= self.threshold:
                            group.append(path2)
                            visited.add(path2)
            except Exception as group_ex:
                debug_manager.log_warning('相似度分组失败', 'hash', filename=filename, error=str(group_ex))
                continue
            
            if len(group) > 1:
                groups.append(group)

        groups.sort(key=lambda x: len(x), reverse=True)
        debug_manager.log_info(f'{stage_name}完成', 'hash', group_count=len(groups))

        if not self.is_canceled:
            self.emit('analysis_finished', groups, duplicates, hash_list)

    def _emit_progress(self, current: int, total: int, stage_name: str, filename: str, processed_count: int, stage_progress: int):
        self.emit('progress_updated', current, total, stage_name, filename, processed_count, stage_progress)

    @staticmethod
    def _extract_filename(path: str) -> str:
        return path.split('/')[-1] if '/' in path else path.split('\\')[-1]

    @staticmethod
    def group_by_similarity(hash_list: list, threshold: int) -> list:
        visited = set()
        groups = []
        
        for i, (path1, hash1) in enumerate(hash_list):
            if path1 in visited:
                continue
            
            group = [path1]
            visited.add(path1)
            
            try:
                for j in range(i + 1, len(hash_list)):
                    path2, hash2 = hash_list[j]
                    if path2 not in visited:
                        diff = hamming_distance(hash1, hash2)
                        if diff <= threshold:
                            group.append(path2)
                            visited.add(path2)
            except Exception as group_ex:
                debug_manager.log_warning('相似度分组失败', 'hash', filename=path1, error=str(group_ex))
                continue
            
            if len(group) > 1:
                groups.append(group)
        
        groups.sort(key=lambda x: len(x), reverse=True)
        return groups