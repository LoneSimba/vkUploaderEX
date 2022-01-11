from os import path

import pygsheets

from utils.singleton import Singleton

from google.oauth2.credentials import Credentials

from pygsheets.client import Client
from pygsheets.worksheet import Worksheet
from pygsheets.spreadsheet import Spreadsheet

from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile
from pydrive2.auth import GoogleAuth, AuthenticationError


class Handler(type, metaclass=Singleton):

    def __instancecheck__(self, instance):
        return self.__subclasscheck__(type(instance))

    def __subclasscheck__(self, subclass):
        return (hasattr(subclass, 'download') and
                callable(subclass.download) and
                hasattr(subclass, 'set_source') and
                callable(subclass.set_source) and
                hasattr(subclass, 'get_sources_list') and
                callable(subclass.get_sources_list))

    def download(cls):
        pass

    def set_source(cls, source):
        pass

    def get_sources_list(cls):
        pass


class GDriveHandler(metaclass=Handler):
    client: GoogleDrive = None
    pygsheets_client: Client = None

    available_sheets: dict = {}
    target_sheet: Spreadsheet = None

    available_worksheets: dict = {}
    target_worksheet: Worksheet = None

    def __init__(self):
        if not path.exists('.config/gdrive_creds.json'):
            open('.config/gdrive_creds.json', 'a').close()

        try:
            auth = GoogleAuth(settings_file='.config/gdrive.yaml')
            auth.LocalWebserverAuth()

            self.client = GoogleDrive(auth)

            creds = Credentials.from_authorized_user_file('.config/gdrive_creds.json')

            self.pygsheets_client = pygsheets.authorize(custom_credentials=creds)
        except AuthenticationError:
            print('Ошибка при авторизации в Google')

    def download(self, url: str):
        """Выполняет скачивание файлов с указанного URL
        :param url: Публичный URL для файла или папки
        """

        pass

    def get_sources_list(self) -> list:
        sheets = self.client.ListFile({
            'q': "'root' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'",
            'includeItemsFromAllDrives': True
        }).GetList()

        files: list = list()
        item: GoogleDriveFile
        for item in sheets:
            title = '%s (%s)' % (item.metadata.get('title'), ','.join(item.metadata.get('ownerNames')))
            self.available_sheets[item.metadata.get('id')] = title
            files.append(title)

        return files

    def set_source(self, title: str):
        if title in self.available_sheets.values():
            sheet_id = {s for s in self.available_sheets if self.available_sheets[s] == title}.pop()
            self.target_sheet = self.pygsheets_client.open_by_key(sheet_id)

    def get_sheets(self) -> list:
        sheets: list = list()
        s: Worksheet
        for s in self.target_sheet.worksheets():
            sheets.append(s.title)

        return sheets

    def set_worksheet(self, title: str):
        self.target_worksheet = self.target_sheet.worksheet_by_title(title)
