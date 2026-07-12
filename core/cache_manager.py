import os
import json
import hashlib
from typing import Dict, Optional, List, Tuple

from core.debug_manager import debug_manager


class CacheManager:
    CONFIG_DIR = 'classifier_configs'

    def __init__(self):
        self.current_folder: str = ""

    def set_current_folder(self, folder_path: str):
        self.current_folder = folder_path

    def get_hash_cache_file(self) -> str:
        if not self.current_folder:
            return ""
        folder_hash = hashlib.md5(self.current_folder.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}_hash_cache.json')

    def load_hash_cache(self) -> dict:
        debug_manager.log_info('加载哈希缓存', 'config', current_folder=self.current_folder)
        if not self.current_folder:
            debug_manager.log_info('无当前文件夹，返回空缓存', 'config')
            return {}
        cache_file = self.get_hash_cache_file()
        debug_manager.log_info('哈希缓存文件路径', 'config', file=cache_file)
        if os.path.exists(cache_file):
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    cache = json.load(f)
                debug_manager.log_info('哈希缓存加载成功', 'config', cache_size=len(cache))
                return cache
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=cache_file)
                return {}
        else:
            debug_manager.log_info('哈希缓存文件不存在', 'config', file=cache_file)
            return {}

    def save_hash_cache(self, cache: dict):
        if not self.current_folder:
            debug_manager.log_warning('无法保存哈希缓存', 'config', reason='current_folder为空')
            return
        cache_file = self.get_hash_cache_file()
        debug_manager.log_info('保存哈希缓存', 'config', file=cache_file, cache_size=len(cache))
        try:
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache, f, ensure_ascii=False, indent=2)
            debug_manager.log_info('哈希缓存保存成功', 'config', file=cache_file)
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=cache_file)

    def rename_in_hash_cache(self, old_path: str, new_path: str) -> bool:
        cache = self.load_hash_cache()
        if not cache:
            return False

        found = False

        if 'files' in cache and old_path in cache['files']:
            cache['files'][new_path] = cache['files'].pop(old_path)
            found = True

        if 'duplicates' in cache:
            for md5, paths in cache['duplicates'].items():
                if old_path in paths:
                    idx = paths.index(old_path)
                    paths[idx] = new_path
                    found = True

        if 'similar_groups' in cache:
            for group in cache['similar_groups']:
                if old_path in group:
                    idx = group.index(old_path)
                    group[idx] = new_path
                    found = True

        if 'hash_list' in cache:
            for i, (p, h) in enumerate(cache['hash_list']):
                if p == old_path:
                    cache['hash_list'][i] = (new_path, h)
                    found = True

        if 'file_hashes' in cache and old_path in cache['file_hashes']:
            cache['file_hashes'][new_path] = cache['file_hashes'].pop(old_path)
            found = True

        if found:
            self.save_hash_cache(cache)
            debug_manager.log_info('哈希缓存路径已更新', 'hash', old=old_path, new=new_path)
        return found

    def check_files_changed(self, image_paths: list) -> tuple:
        debug_manager.log_info('检查文件变化', 'hash', file_count=len(image_paths))
        cache = self.load_hash_cache()
        if not cache:
            debug_manager.log_info('无缓存数据，需要重新分析', 'hash')
            return True, image_paths

        cached_files = cache.get('files', {})
        current_files = {}
        for path in image_paths:
            try:
                stat = os.stat(path)
                current_files[path] = {
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                }
            except Exception as e:
                debug_manager.log_warning('获取文件信息失败', 'hash', path=path, error=str(e))
                return True, image_paths

        changed_files = []

        for path, info in current_files.items():
            if path not in cached_files:
                debug_manager.log_info('发现新文件', 'hash', path=path)
                changed_files.append(path)
            else:
                cached_info = cached_files[path]
                if cached_info['size'] != info['size'] or cached_info['mtime'] != info['mtime']:
                    debug_manager.log_info('文件内容变化', 'hash', path=path)
                    changed_files.append(path)

        removed_files = set(cached_files.keys()) - set(current_files.keys())
        if removed_files:
            debug_manager.log_info('文件被删除', 'hash', removed_count=len(removed_files))

        if changed_files or removed_files:
            debug_manager.log_info('文件有变化', 'hash', changed_count=len(changed_files), removed_count=len(removed_files))
            return True, changed_files
        else:
            debug_manager.log_info('文件无变化，可使用缓存', 'hash')
            return False, []

    def create_file_cache(self, image_paths: list) -> dict:
        debug_manager.log_info('创建文件缓存', 'hash', file_count=len(image_paths))
        files = {}
        for path in image_paths:
            try:
                stat = os.stat(path)
                files[path] = {
                    'size': stat.st_size,
                    'mtime': stat.st_mtime
                }
            except Exception as e:
                debug_manager.log_warning('获取文件信息失败', 'hash', path=path, error=str(e))

        cache = {
            'files': files
        }
        return cache

    def build_hash_cache(self, image_paths: list, groups: list, duplicates: dict,
                         hash_list: list = None) -> dict:
        debug_manager.log_info('构建哈希缓存', 'hash',
                               file_count=len(image_paths),
                               group_count=len(groups),
                               duplicate_count=len(duplicates),
                               has_hash_list=hash_list is not None)
        cache = self.create_file_cache(image_paths)
        cache['duplicates'] = duplicates
        cache['similar_groups'] = groups

        if hash_list:
            cache['hash_list'] = hash_list
            file_hashes = {path: {'img_hash': img_hash} for path, img_hash in hash_list}
            cache['file_hashes'] = file_hashes

            md5_hash_map = {}
            for md5, paths in duplicates.items():
                for path in paths:
                    if path not in md5_hash_map:
                        md5_hash_map[path] = md5
            for path, md5 in md5_hash_map.items():
                if path not in cache['file_hashes']:
                    cache['file_hashes'][path] = {}
                cache['file_hashes'][path]['md5'] = md5

        return cache