from typing import Callable, List, Dict, Any


class Observer:
    def __init__(self):
        self._callbacks: Dict[str, List[Callable]] = {}

    def on(self, event_name: str, callback: Callable):
        if event_name not in self._callbacks:
            self._callbacks[event_name] = []
        if callback not in self._callbacks[event_name]:
            self._callbacks[event_name].append(callback)

    def off(self, event_name: str, callback: Callable = None):
        if event_name not in self._callbacks:
            return
        if callback is None:
            self._callbacks[event_name] = []
        else:
            self._callbacks[event_name].remove(callback)

    def emit(self, event_name: str, *args, **kwargs):
        if event_name not in self._callbacks:
            return
        for callback in self._callbacks[event_name]:
            try:
                callback(*args, **kwargs)
            except Exception:
                pass