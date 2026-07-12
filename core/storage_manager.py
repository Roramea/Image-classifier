import os
from typing import Dict, List

from core.debug_manager import debug_manager


class StorageManager:
    CONFIG_DIR = 'classifier_configs'
    PROTECTED_FILES = {'debug_logs.json'}

    def __init__(self):
        pass

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

        if 'duplicates' in categories:
            for filename in os.listdir(self.CONFIG_DIR):
                filepath = os.path.join(self.CONFIG_DIR, filename)
                if os.path.isfile(filepath) and filename.endswith('_duplicates.json'):
                    try:
                        os.remove(filepath)
                    except Exception:
                        success = False

        if 'recent' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'recent_folders.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False

        if 'session' in categories:
            filepath = os.path.join(self.CONFIG_DIR, 'unfinished_session.json')
            if os.path.exists(filepath):
                try:
                    os.remove(filepath)
                except Exception:
                    success = False

        return success