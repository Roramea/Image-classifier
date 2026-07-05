import os
import hashlib
from PIL import Image
from typing import List, Optional

from .simple_hash import dhash
from .debug_manager import debug_manager


class ImageScanner:
    SUPPORTED_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff', '.webp'}
    
    def __init__(self):
        self.image_paths: List[str] = []
    
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
    
    