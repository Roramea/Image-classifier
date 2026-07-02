import os
import hashlib
from PIL import Image
from collections import defaultdict
from typing import List, Dict, Tuple, Optional

from simple_hash import compute_image_hash, hamming_distance


class ImageScanner:
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    def __init__(self):
        self.image_paths: List[str] = []
        self.md5_hash_map: Dict[str, List[str]] = {}
        self.image_hash_map: Dict[str, str] = {}
        self.similar_groups: List[List[str]] = []
    
    def scan_folder(self, folder_path: str) -> int:
        self.image_paths = []
        for root, dirs, files in os.walk(folder_path):
            for file in files:
                ext = os.path.splitext(file)[1].lower()
                if ext in self.SUPPORTED_EXTENSIONS:
                    self.image_paths.append(os.path.join(root, file))
        return len(self.image_paths)
    
    def compute_md5(self, file_path: str) -> Optional[str]:
        try:
            hash_md5 = hashlib.md5()
            with open(file_path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    hash_md5.update(chunk)
            return hash_md5.hexdigest()
        except Exception:
            return None
    
    def compute_image_hash(self, file_path: str) -> Optional[str]:
        try:
            img = Image.open(file_path)
            img = img.convert('RGB')
            return compute_image_hash(file_path)
        except Exception:
            return None
    
    def find_duplicates(self) -> Dict[str, List[str]]:
        self.md5_hash_map = defaultdict(list)
        for path in self.image_paths:
            md5 = self.compute_md5(path)
            if md5:
                self.md5_hash_map[md5].append(path)
        
        duplicates = {md5: paths for md5, paths in self.md5_hash_map.items() if len(paths) > 1}
        return duplicates
    
    def group_similar_images(self, threshold: int = 10) -> List[List[str]]:
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
        return self.similar_groups
    
    def get_all_images(self) -> List[str]:
        return self.image_paths
    
    def get_similar_groups(self) -> List[List[str]]:
        return self.similar_groups