import os
import hashlib
from PIL import Image
from collections import defaultdict
from typing import List, Dict, Optional

from .simple_hash import compute_image_hash, hamming_distance, dhash
from .debug_manager import debug_manager


class ImageScanner:
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    def __init__(self):
        self.image_paths: List[str] = []
        self.md5_hash_map: Dict[str, List[str]] = {}
        self.image_hash_map: Dict[str, str] = {}
        self.similar_groups: List[List[str]] = []
    
    def scan_folder(self, folder_path: str) -> int:
        debug_manager.log_info('开始扫描文件夹', 'scanner', folder_path=folder_path)
        self.image_paths = []
        try:
            for root, dirs, files in os.walk(folder_path):
                for file in files:
                    ext = os.path.splitext(file)[1].lower()
                    if ext in self.SUPPORTED_EXTENSIONS:
                        self.image_paths.append(os.path.join(root, file))
            count = len(self.image_paths)
            debug_manager.log_info('扫描完成', 'scanner', folder_path=folder_path, image_count=count)
            return count
        except Exception as e:
            debug_manager.log_exception(e, 'scanner', folder_path=folder_path)
            return 0
    
    def compute_md5(self, file_path: str) -> Optional[str]:
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception as e:
            debug_manager.log_warning('计算MD5失败', 'scanner', file_path=file_path)
            return None
    
    def compute_image_hash(self, file_path: str) -> Optional[str]:
        try:
            with Image.open(file_path) as img:
                img = img.convert('RGB')
                return dhash(img)
        except Exception as e:
            debug_manager.log_warning('计算图像哈希失败', 'scanner', file_path=file_path, error=str(e))
            return None
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        debug_manager.log_info('开始查找重复图片', 'scanner', image_count=len(self.image_paths))
        self.md5_hash_map = defaultdict(list)
        for path in self.image_paths:
            md5 = self.compute_md5(path)
            if md5:
                self.md5_hash_map[md5].append(path)
        
        duplicates = {md5: paths for md5, paths in self.md5_hash_map.items() if len(paths) > 1}
        debug_manager.log_info('重复图片查找完成', 'scanner', duplicate_groups=len(duplicates))
        return duplicates
    
    def group_similar_images(self, threshold: int = 10) -> List[List[str]]:
        debug_manager.log_info('开始相似图片分组', 'scanner', image_count=len(self.image_paths), threshold=threshold)
        hash_list = []
        for path in self.image_paths:
            img_hash = self.compute_image_hash(path)
            if img_hash:
                self.image_hash_map[path] = img_hash
                hash_list.append((path, img_hash))
        
        visited = set()
        groups = []
        
        for i, (path1, hash1) in enumerate(hash_list):
            if path1 in visited:
                continue
            
            group = [path1]
            visited.add(path1)
            
            for j in range(i + 1, len(hash_list)):
                path2, hash2 = hash_list[j]
                if path2 not in visited:
                    diff = hamming_distance(hash1, hash2)
                    if diff <= threshold:
                        group.append(path2)
                        visited.add(path2)
            
            groups.append(group)
        
        self.similar_groups = sorted(groups, key=lambda x: len(x), reverse=True)
        debug_manager.log_info('相似图片分组完成', 'scanner', group_count=len(self.similar_groups))
        return self.similar_groups
    
    def get_all_images(self) -> List[str]:
        return self.image_paths
    
    def get_similar_groups(self) -> List[List[str]]:
        return self.similar_groups