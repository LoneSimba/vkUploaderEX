import os
import json

from internal.settings import Settings
from utils.filesystem import FileSystem

from vk_api import *
from vk_api.vk_api import VkApiMethod


class VKHandler:
    _api: VkApiMethod = None
    _uploader: VkUpload = None
    _settings: Settings = None

    _config_path: str = os.path.join(os.getcwd(), '.config')
    _download_path: str = os.path.join(os.getcwd(), '.temp')
    _token_path: str = os.path.join(_config_path, 'vk_token.json')
    _vkconf_path: str = os.path.join(_config_path, 'vk_config.v2.json')

    photo_albums: dict = {}
    video_albums: dict = {}

    photo_album_id: int = 0
    video_album_id: int = 0

    def __init__(self):
        self._settings = Settings()

    def auth_with_token(self) -> bool:
        try:
            with open(self._token_path, 'r') as f:
                token = f.readline()

            if len(token) == 0:
                return False
            else:
                token = json.loads(token)

                try:
                    session = VkApi(login=token.get('login'), token=token.get('token'),
                                    config_filename=self._vkconf_path)
                    session.auth()

                    self._api = session.get_api()
                    self._uploader = VkUpload(self._api)

                    return True
                except PasswordRequired:
                    return False

        except IOError:
            return False

    def auth_with_password(self, password: str):
        pass

    def auth_with_creds(self, login: str, password: str):
        try:
            session = vk_api.VkApi(login=login, password=password, config_filename=self._vkconf_path)
            session.auth()

            with open(self._token_path, "w+", encoding='utf-8') as f:
                auth = {
                    'login': login,
                    'token': session.token.get('access_token')
                }

                f.write(json.dumps(auth))

            self._api = session.get_api()
            self._uploader = VkUpload(self._api)
        except:
            print('Ошибка входа')

    def is_auth_required(self) -> bool:
        return self._api is None

    def get_albums_photo(self) -> list:
        if self.is_auth_required() and not self.auth_with_token():
            print('Не удалось авторизоваться')
            return list()

        albums: dict = {}
        for al in VkTools(self._api).get_all_iter(method='photos.getAlbums',
                                                  values={'owner_id': -self._settings.get_value('group')}, max_count=20):
            albums[al.get('id')] = al.get('title')

        self.photo_albums = albums
        return list(albums.values())

    def get_albums_video(self) -> list:
        if self.is_auth_required() and not self.auth_with_token():
            print('Не удалось авторизоваться')
            return list()

        albums: dict = {}
        for al in VkTools(self._api).get_all_iter(method='video.getAlbums',
                                                  values={'owner_id': -self._settings.get_value('group')}, max_count=20):
            albums[al.get('id')] = al.get('title')

        self.video_albums = albums
        return list(albums.values())

    def set_photo_album(self, title: str):
        if title in self.photo_albums.values():
            self.photo_album_id = {s for s in self.photo_albums if self.photo_albums[s] == title}.pop()

    def set_video_album(self, title: str):
        if title in self.video_albums.values():
            self.video_album_id = {s for s in self.video_albums if self.video_albums[s] == title}.pop()

    def upload(self, data: dict, desc: str) -> tuple[int, int, int, int]:
        for key, val in data.items():
            desc = desc.replace('$%s$' % key, str(val))

        path = os.path.join(self._download_path, str(data.get('id')))
        group = self._settings.get_value('group')
        fs = FileSystem(path)
        files = fs.list_files()
        total = len(files)
        uploaded = failed = skipped = 0

        for file in files:
            filename = os.fsdecode(file)

            if fs.get_mime(filename) is None:
                filename = fs.fix_ext(filename)
                if filename is None:
                    skipped += 1
                    continue

            if fs.is_image(filename):
                if fs.is_heic(filename):
                    filename = fs.convert_heic_to_jpg(filename)
                else:
                    fs.resize_img(filename)

                try:
                    desc = desc.replace('$file$', filename)
                    if self._uploader.photo(photos=os.path.join(path, filename), album_id=self.photo_album_id,
                                            description=desc, group_id=group):
                        uploaded += 1
                    else:
                        failed += 1
                except:
                    failed += 1
                finally:
                    os.remove(os.path.join(path, filename))

            elif fs.is_pdf(filename):
                orig = filename
                tmp_fs = fs.convert_pdf_to_jpg(filename)
                if tmp_fs is not None:
                    tmp_files = tmp_fs.list_files()
                    total += len(tmp_files)-1

                    for file_i in tmp_files:
                        filename = os.fsdecode(file_i)
                        try:
                            desc = desc.replace('$file$', orig)
                            if self._uploader.photo(photos=os.path.join(tmp_fs.get_path(), filename),
                                                    album_id=self.photo_album_id, description=desc, group_id=group):
                                uploaded += 1
                            else:
                                failed += 1
                        except:
                            failed += 1
                        finally:
                            os.remove(os.path.join(tmp_fs.get_path(), filename))

                    tmp_fs.remove()
                    os.remove(os.path.join(path, orig))

                else:
                    failed += 1

            elif fs.is_pptx(filename):
                print('pres')
                orig = filename
                tmp_fs = fs.convert_pptx_to_jpg(filename)
                if tmp_fs is not None:
                    tmp_files = tmp_fs.list_files()
                    total += len(tmp_files)-1

                    for file_i in tmp_files:
                        filename = os.fsdecode(file_i)
                        try:
                            desc = desc.replace('$file$', orig)
                            if self._uploader.photo(photos=os.path.join(tmp_fs.get_path(), filename),
                                                    album_id=self.photo_album_id, description=desc, group_id=group):
                                uploaded += 1
                            else:
                                failed += 1
                        except:
                            failed += 1
                        finally:
                            os.remove(os.path.join(tmp_fs.get_path(), filename))

                    tmp_fs.remove()
                    os.remove(os.path.join(path, orig))

                else:
                    failed += 1

            elif fs.is_video(filename):
                print('video')
                try:
                    desc = desc.replace('$file$', filename)
                    if self._uploader.video(video_file=os.path.join(path, filename), album_id=self.video_album_id,
                                            description=desc, group_id=group, name=data.get('title')):
                        uploaded += 1
                    else:
                        failed += 1
                except:
                    failed += 1
                finally:
                    os.remove(os.path.join(path, filename))

            else:
                print('skip')
                skipped += 1
                os.remove(os.path.join(path, filename))

        fs.remove()

        return total, uploaded, failed, skipped
