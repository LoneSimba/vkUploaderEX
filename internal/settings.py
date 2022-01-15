import json

from os import path, getcwd

from utils.singleton import Singleton


class Settings(metaclass=Singleton):
    _data: dict = {}
    _settings_file_path: str = path.join(getcwd(), '.config', 'settings.json')

    def __init__(self):
        if not path.exists(self._settings_file_path):
            with open(self._settings_file_path, 'a') as f:
                self._data = {
                    'login': '',
                    'group': ''
                }

                f.write(json.dumps(self._data))
        else:
            with open(self._settings_file_path, 'r') as f:
                _raw = f.readline()
                self._data = json.loads(_raw)

    def update(self, login: str, group: int):
        self._data['login'] = login
        self._data['group'] = group


    def save(self):
        with open(self._settings_file_path, 'w+') as f:
            f.write(json.dumps(self._data))

    def get_value(self, key: str):
        if key in self._data.keys():
            return self._data.get(key)
        else:
            return None

    def get_all(self):
        return self._data
