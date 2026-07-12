import abc
from PyQt5.QtCore import QObject
from typing import Optional, Dict, List, Tuple


class QtABCMeta(type(QObject), abc.ABCMeta):
    pass


class IMainView(metaclass=QtABCMeta):
    @abc.abstractmethod
    def update_shortcuts(self, shortcuts: Dict[str, str]) -> None:
        pass

    @abc.abstractmethod
    def update_recent_folders(self, recent_folders: List[str]) -> None:
        pass

    @abc.abstractmethod
    def update_duplicate_list(self, duplicates: Dict[str, List[str]]) -> None:
        pass

    @abc.abstractmethod
    def update_threshold(self, threshold: int) -> None:
        pass

    @abc.abstractmethod
    def set_status(self, text: str) -> None:
        pass

    @abc.abstractmethod
    def show_current_image(self) -> None:
        pass

    @abc.abstractmethod
    def show_folder_dialog(self, callback) -> None:
        pass

    @abc.abstractmethod
    def show_unfinished_session_dialog(self, folder_path, total_count, processed_count,
                                      remaining, continue_callback, cancel_callback) -> None:
        pass

    @abc.abstractmethod
    def show_hash_analysis_dialog(self, hash_service, progress_callback,
                                  finished_callback, canceled_callback,
                                  error_callback, threshold_callback) -> None:
        pass

    @abc.abstractmethod
    def show_delete_confirm_dialog(self, group_count, total_paths, total_deletions, callback) -> None:
        pass

    @abc.abstractmethod
    def show_duplicate_detail_dialog(self, selected_groups, selected_md5s, callback) -> None:
        pass

    @abc.abstractmethod
    def show_storage_clean_dialog(self, storage_size: int, storage_details: dict) -> Optional[list]:
        pass

    @abc.abstractmethod
    def show_info_message(self, message: str) -> None:
        pass

    @abc.abstractmethod
    def show_warning_message(self, message: str) -> None:
        pass

    @abc.abstractmethod
    def show_error_message(self, message: str) -> None:
        pass

    @abc.abstractmethod
    def invalidate_image_cache(self, path: str = None) -> None:
        pass

    @abc.abstractmethod
    def on_image_classified(self, current_path, target_path) -> None:
        pass

    @abc.abstractmethod
    def refresh_groups(self) -> None:
        pass

    @abc.abstractmethod
    def update_undo_btn_state(self) -> None:
        pass

    @abc.abstractmethod
    def select_all_duplicates(self) -> None:
        pass

    @abc.abstractmethod
    def deselect_all_duplicates(self) -> None:
        pass

    @abc.abstractmethod
    def get_selected_duplicates(self) -> List[Tuple[str, List[str]]]:
        pass

    @abc.abstractmethod
    def sync_hash_dialog_threshold(self, threshold: int) -> None:
        pass