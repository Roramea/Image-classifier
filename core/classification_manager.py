import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Optional

from core.debug_manager import debug_manager


class ClassificationManager:
    CONFIG_DIR = 'classifier_configs'
    MAX_RECENT_FOLDERS = 10
    PROTECTED_FILES = {'debug_logs.json'}
    
    def __init__(self):
        self.shortcut_map: Dict[str, str] = {}
        self.current_folder: str = ""
        self.last_folder: str = ""
        self.recent_folders: list = []
        self.unfinished_session = None
        self.processed_duplicates: Dict[str, list] = {}
        self.hash_threshold: int = 10
        if not os.path.exists(self.CONFIG_DIR):
            os.makedirs(self.CONFIG_DIR)
            debug_manager.log_info('创建配置目录', 'config', path=self.CONFIG_DIR)
        self.load_recent_folders()
        self.load_unfinished_session()
        self.load_duplicate_memory()
        self.load_settings()
        debug_manager.log_info('ClassificationManager 初始化完成', 'config')
    
    def get_config_file(self, folder_path: str) -> str:
        folder_hash = hashlib.md5(folder_path.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}.json')
    
    def load_recent_folders(self):
        recent_file = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
        debug_manager.log_info('加载最近文件夹', 'config', file=recent_file)
        if os.path.exists(recent_file):
            try:
                with open(recent_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.recent_folders = data.get('recent_folders', [])
                debug_manager.log_info('最近文件夹加载成功', 'config', count=len(self.recent_folders))
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=recent_file)
                self.recent_folders = []
        else:
            self.recent_folders = []
            debug_manager.log_info('最近文件夹文件不存在', 'config', file=recent_file)
        self.last_folder = self.recent_folders[0] if self.recent_folders else ""
        debug_manager.log_info('最近文件夹加载完成', 'config', last_folder=self.last_folder)
    
    def save_recent_folders(self, folder_path: str):
        debug_manager.log_info('保存最近文件夹', 'config', folder_path=folder_path)
        if folder_path in self.recent_folders:
            self.recent_folders.remove(folder_path)
        self.recent_folders.insert(0, folder_path)
        if len(self.recent_folders) > self.MAX_RECENT_FOLDERS:
            self.recent_folders = self.recent_folders[:self.MAX_RECENT_FOLDERS]
        
        recent_file = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
        try:
            with open(recent_file, 'w', encoding='utf-8') as f:
                json.dump({'recent_folders': self.recent_folders}, f, ensure_ascii=False, indent=2)
            self.last_folder = self.recent_folders[0]
            debug_manager.log_info('最近文件夹保存成功', 'config', count=len(self.recent_folders))
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=recent_file)
    
    def load_config(self, folder_path: str = ""):
        debug_manager.log_info('加载配置', 'config', folder_path=folder_path)
        if folder_path:
            self.current_folder = folder_path
            config_file = self.get_config_file(folder_path)
        elif self.last_folder:
            self.current_folder = self.last_folder
            config_file = self.get_config_file(self.last_folder)
        else:
            self.shortcut_map = {}
            self.current_folder = ""
            debug_manager.log_info('无配置文件，使用空映射', 'config')
            return
        
        debug_manager.log_info('配置文件路径', 'config', file=config_file)
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r', encoding='utf-8') as f:
                    self.shortcut_map = json.load(f)
                debug_manager.log_info('配置加载成功', 'config', shortcuts_count=len(self.shortcut_map))
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=config_file)
                self.shortcut_map = {}
        else:
            self.shortcut_map = {}
            debug_manager.log_info('配置文件不存在', 'config', file=config_file)
    
    def save_config(self):
        if not self.current_folder:
            debug_manager.log_error('无法保存配置', 'config', reason='current_folder为空')
            return False
        config_file = self.get_config_file(self.current_folder)
        try:
            with open(config_file, 'w', encoding='utf-8') as f:
                json.dump(self.shortcut_map, f, ensure_ascii=False, indent=2)
            self.save_recent_folders(self.current_folder)
            debug_manager.log_info('配置保存成功', 'config', file=config_file, shortcuts_count=len(self.shortcut_map))
            return True
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=config_file)
            return False
    
    def load_settings(self):
        settings_file = os.path.join(self.CONFIG_DIR, 'settings.json')
        debug_manager.log_info('加载全局设置', 'config', file=settings_file)
        if os.path.exists(settings_file):
            try:
                with open(settings_file, 'r', encoding='utf-8') as f:
                    settings = json.load(f)
                self.hash_threshold = settings.get('hash_threshold', 10)
                debug_manager.log_info('全局设置加载成功', 'config', hash_threshold=self.hash_threshold)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=settings_file)
                self.hash_threshold = 10
        else:
            self.hash_threshold = 10
            debug_manager.log_info('全局设置文件不存在，使用默认值', 'config', hash_threshold=self.hash_threshold)
    
    def save_settings(self):
        settings_file = os.path.join(self.CONFIG_DIR, 'settings.json')
        debug_manager.log_info('保存全局设置', 'config', file=settings_file, hash_threshold=self.hash_threshold)
        try:
            settings = {
                'hash_threshold': self.hash_threshold
            }
            with open(settings_file, 'w', encoding='utf-8') as f:
                json.dump(settings, f, ensure_ascii=False, indent=2)
            debug_manager.log_info('全局设置保存成功', 'config')
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=settings_file)
    
    def get_hash_threshold(self) -> int:
        return self.hash_threshold
    
    def set_hash_threshold(self, threshold: int):
        self.hash_threshold = threshold
        self.save_settings()
        debug_manager.log_info('设置哈希阈值', 'config', threshold=threshold)
    
    def get_recent_folders(self) -> list:
        return self.recent_folders.copy()
    
    def load_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('加载未完成会话', 'config', file=session_file)
        if os.path.exists(session_file):
            try:
                with open(session_file, 'r', encoding='utf-8') as f:
                    self.unfinished_session = json.load(f)
                debug_manager.log_info('未完成会话加载成功', 'config', session=self.unfinished_session)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=session_file)
                self.unfinished_session = None
        else:
            self.unfinished_session = None
            debug_manager.log_info('未完成会话文件不存在', 'config', file=session_file)
    
    def get_duplicate_memory_file(self) -> str:
        if not self.current_folder:
            return ""
        folder_hash = hashlib.md5(self.current_folder.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}_duplicates.json')
    
    def get_hash_cache_file(self) -> str:
        if not self.current_folder:
            return ""
        folder_hash = hashlib.md5(self.current_folder.encode('utf-8')).hexdigest()
        return os.path.join(self.CONFIG_DIR, f'{folder_hash}_hash_cache.json')
    
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
        """重命名哈希缓存中的所有路径引用。

        更新 fields: files, duplicates, similar_groups, hash_list, file_hashes。
        若缓存文件不存在或未找到旧路径则返回 False。
        """
        cache = self.load_hash_cache()
        if not cache:
            return False

        found = False

        # 1. files: 文件元信息 {path: {size, mtime}}
        if 'files' in cache and old_path in cache['files']:
            cache['files'][new_path] = cache['files'].pop(old_path)
            found = True

        # 2. duplicates: {md5: [paths]}
        if 'duplicates' in cache:
            for md5, paths in cache['duplicates'].items():
                if old_path in paths:
                    idx = paths.index(old_path)
                    paths[idx] = new_path
                    found = True

        # 3. similar_groups: [[path, ...], ...]
        if 'similar_groups' in cache:
            for group in cache['similar_groups']:
                if old_path in group:
                    idx = group.index(old_path)
                    group[idx] = new_path
                    found = True

        # 4. hash_list: [(path, img_hash), ...]（列表元组）
        if 'hash_list' in cache:
            for i, (p, h) in enumerate(cache['hash_list']):
                if p == old_path:
                    cache['hash_list'][i] = (new_path, h)
                    found = True

        # 5. file_hashes: {path: {img_hash, md5}}
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
            'files': files,
            'timestamp': datetime.now().isoformat()
        }
        return cache

    def build_hash_cache(self, image_paths: list, groups: list, duplicates: dict,
                         hash_list: list = None) -> dict:
        """构建完整的哈希缓存数据结构。

        封装缓存格式知识，避免表现层直接操作缓存内部结构。包含：
        - files: 文件元信息（size/mtime），用于变更检测
        - duplicates: 重复图片映射 {md5: [paths]}
        - similar_groups: 相似度分组 [[path, ...], ...]
        - hash_list: 图像哈希列表 [(path, img_hash), ...]（用于阈值调整时重新分组）
        - file_hashes: 文件哈希映射 {path: {'img_hash': str, 'md5': str}}（用于增量计算）

        Args:
            image_paths: 当前所有图片路径
            groups: 相似度分组结果
            duplicates: 重复图片字典
            hash_list: 图像哈希列表（可选，无则不写入 hash_list 和 file_hashes 的 img_hash 字段）

        Returns:
            完整的缓存字典，可直接传给 save_hash_cache 持久化
        """
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

            # 构建 path -> md5 反向映射，补充到 file_hashes
            # 这样下次扫描时可以直接从缓存读取 md5，避免重新计算
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
    
    def save_unfinished_session(self, session_data: dict):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('保存未完成会话', 'config', session_data=session_data)
        try:
            with open(session_file, 'w', encoding='utf-8') as f:
                json.dump(session_data, f, ensure_ascii=False, indent=2)
            self.unfinished_session = session_data
            debug_manager.log_info('未完成会话保存成功', 'config', file=session_file)
        except Exception as e:
            debug_manager.log_exception(e, 'config', file=session_file)
    
    def clear_unfinished_session(self):
        session_file = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
        debug_manager.log_info('清除未完成会话', 'config', file=session_file)
        if os.path.exists(session_file):
            try:
                os.remove(session_file)
                debug_manager.log_info('未完成会话文件已删除', 'config', file=session_file)
            except Exception as e:
                debug_manager.log_exception(e, 'config', file=session_file)
        self.unfinished_session = None
    
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
    
    def get_processed_duplicate_paths(self, md5_hash: str) -> list:
        return self.processed_duplicates.get(md5_hash, [])
    
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
    
    def check_all_duplicates_processed(self, all_duplicates: dict) -> bool:
        for md5_hash in all_duplicates.keys():
            if md5_hash not in self.processed_duplicates:
                return False
        return True
    
    def get_storage_size(self) -> int:
        total_size = 0
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                if filename in self.PROTECTED_FILES:
                    continue
                
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    total_size += os.path.getsize(filepath)
        return total_size
    
    def format_storage_size(self) -> str:
        size = self.get_storage_size()
        return self._format_size(size)
    
    def _format_size(self, size: int) -> str:
        if size < 1024:
            return f"{size} B"
        elif size < 1024 * 1024:
            return f"{size / 1024:.2f} KB"
        else:
            return f"{size / (1024 * 1024):.2f} MB"
    
    def get_storage_details(self) -> dict:
        details = {
            'shortcuts': {
                'name': '快捷键配置',
                'description': '各文件夹的快捷键绑定设置',
                'files': [],
                'size': 0
            },
            'duplicates': {
                'name': '重复图片处理记忆',
                'description': '已处理的重复图片组记录',
                'files': [],
                'size': 0
            },
            'recent': {
                'name': '最近文件夹记录',
                'description': '最近使用的文件夹列表',
                'files': [],
                'size': 0
            },
            'session': {
                'name': '未完成分类会话',
                'description': '上次未完成的分类进度',
                'files': [],
                'size': 0
            }
        }
        
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                if filename in self.PROTECTED_FILES:
                    continue
                
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    file_size = os.path.getsize(filepath)
                    
                    if filename.endswith('_duplicates.json'):
                        details['duplicates']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['duplicates']['size'] += file_size
                    elif filename == 'recent_folders.json':
                        details['recent']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['recent']['size'] += file_size
                    elif filename == 'unfinished_session.json':
                        details['session']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['session']['size'] += file_size
                    elif filename.endswith('.json'):
                        details['shortcuts']['files'].append({
                            'name': filename,
                            'path': filepath,
                            'size': file_size
                        })
                        details['shortcuts']['size'] += file_size
        
        return details
    
    def clear_categories(self, categories: list) -> bool:
        success = True
        
        if 'shortcuts' in categories:
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith('.json'):
                    if not filename.endswith('_duplicates.json') and \
                       filename != 'recent_folders.json' and \
                       filename != 'unfinished_session.json' and \
                       filename not in self.PROTECTED_FILES:
                        try:
                            os.remove(filepath)
                        except Exception:
                            success = False
            self.shortcut_map = {}
        
        if 'duplicates' in categories:
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith('_duplicates.json'):
                    try:
                        os.remove(filepath)
                    except Exception:
                        success = False
            self.processed_duplicates = {}
        
        if 'recent' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False
            self.recent_folders = []
            self.last_folder = ""
        
        if 'session' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False
            self.unfinished_session = None
        
        return success
    
    def clear_all_storage(self):
        if os.path.exists(self.CONFIG_DIR):
            for filename in os.listdir(self.CONFIG_DIR):
                if filename in self.PROTECTED_FILES:
                    continue
                
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath):
                    try:
                        os.remove(filepath)
                    except Exception:
                        pass
        
        self.shortcut_map = {}
        self.recent_folders = []
        self.unfinished_session = None
        self.processed_duplicates = {}
        self.last_folder = ""
    
    def get_unfinished_session(self) -> Optional[dict]:
        if self.unfinished_session:
            folder_path = self.unfinished_session.get('folder_path', "")
            if os.path.exists(folder_path):
                return self.unfinished_session
        return None
    
    def _is_valid_path(self, path: str) -> bool:
        if not path or not isinstance(path, str):
            debug_manager.log_warning('路径无效', 'config', path=path)
            return False
        
        invalid_chars = '<>"|?*'
        for char in invalid_chars:
            if char in path:
                debug_manager.log_warning('路径包含无效字符', 'config', path=path, invalid_char=char)
                return False
        
        colon_count = path.count(':')
        if colon_count > 1:
            debug_manager.log_warning('路径包含多个冒号', 'config', path=path)
            return False
        
        if colon_count == 1 and not (len(path) >= 2 and path[1] == ':' and path[0].isalpha()):
            debug_manager.log_warning('冒号位置无效', 'config', path=path)
            return False
        
        return True
    
    def add_shortcut(self, shortcut: str, folder_path: str) -> bool:
        if not self.current_folder:
            debug_manager.log_error('无法添加快捷键：未选择图片文件夹', 'config', shortcut=shortcut)
            return False

        if shortcut in self.shortcut_map:
            debug_manager.log_warning('快捷键已存在', 'config', shortcut=shortcut)
            return False

        if not self._is_valid_path(folder_path):
            debug_manager.log_error('路径验证失败', 'config', shortcut=shortcut, folder_path=folder_path)
            return False

        if not os.path.exists(folder_path):
            try:
                os.makedirs(folder_path)
                debug_manager.log_info('创建文件夹', 'config', folder_path=folder_path)
            except Exception as e:
                debug_manager.log_exception(e, 'config', folder_path=folder_path)
                return False

        self.shortcut_map[shortcut] = folder_path
        result = self.save_config()
        if result:
            debug_manager.log_info('快捷键添加成功', 'config', shortcut=shortcut, folder_path=folder_path,
                                   current_folder=self.current_folder)
        else:
            # 保存失败时回滚内存中的修改，避免 shortcut_map 被污染
            del self.shortcut_map[shortcut]
            debug_manager.log_error('快捷键保存失败', 'config', shortcut=shortcut)
        return result
    
    def remove_shortcut(self, shortcut: str) -> bool:
        if shortcut in self.shortcut_map:
            removed_path = self.shortcut_map.pop(shortcut)
            result = self.save_config()
            if not result:
                # 保存失败时回滚，避免内存与磁盘不一致
                self.shortcut_map[shortcut] = removed_path
            return result
        return False
    
    def get_folder(self, shortcut: str) -> Optional[str]:
        return self.shortcut_map.get(shortcut)
    
    def get_all_shortcuts(self) -> Dict[str, str]:
        return self.shortcut_map.copy()
    
    def classify_image(self, image_path: str, shortcut: str) -> Optional[str]:
        """将图片移动到快捷键对应的目标文件夹。

        Returns:
            成功时返回目标路径，失败时返回 None。
        """
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