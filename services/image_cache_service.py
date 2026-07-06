from collections import OrderedDict
from PyQt5.QtGui import QPixmap


class ImageCacheService:
    def __init__(self, max_size: int = 10):
        self._cache = OrderedDict()
        self._max_size = max_size

    def get(self, path: str) -> QPixmap:
        if path in self._cache:
            self._cache.move_to_end(path)
            return self._cache[path]
        return None

    def set(self, path: str, pixmap: QPixmap):
        if path in self._cache:
            self._cache.move_to_end(path)
        else:
            if len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
        self._cache[path] = pixmap

    def remove(self, path: str):
        if path in self._cache:
            del self._cache[path]

    def clear(self):
        self._cache.clear()

    def contains(self, path: str) -> bool:
        return path in self._cache

    def get_size(self) -> int:
        return len(self._cache)