import os
import re
import shutil
import requests
import mimetypes

import yadisk
import pygsheets

from os import path, makedirs
from enum import Enum, IntEnum

from google.oauth2.credentials import Credentials

from pygsheets.client import Client
from pygsheets import Cell, Spreadsheet, Worksheet

from pydrive2.drive import GoogleDrive
from pydrive2.files import GoogleDriveFile
from pydrive2.auth import GoogleAuth, AuthenticationError


class CloudHandler(type):

    def __instancecheck__(self, instance):
        return self.__subclasscheck__(type(instance))

    def __subclasscheck__(self, subclass):
        return (hasattr(subclass, 'download') and
                callable(subclass.download) and
                hasattr(subclass, 'set_source') and
                callable(subclass.set_source) and
                hasattr(subclass, 'get_sources_list') and
                callable(subclass.get_sources_list))

    def download(cls, url: str, dest: str):
        pass

    def set_source(cls, source):
        pass

    def get_sources_list(cls):
        pass


class GDriveCols(IntEnum):
    ID: int = 0
    SCHOOL: int = 3
    GROUP: int = 4
    STUDENT: int = 6
    AGE: int = 7
    TUTOR: int = 10
    TITLE: int = 13
    MATERIALS: int = 14
    LINK: int = 16
    COMM: int = 17


class GDriveColors(Enum):
    GREEN: tuple[float, float, float, float] = (0.8509804, 0.91764706, 0.827451, 0.0)
    GREY: tuple[float, float, float, float] = (0.8509804, 0.8509804, 0.8509804, 0.0)
    BLUE: tuple[float, float, float, float] = (0.23921569, 0.52156866, 0.7764706, 0.0)
    RED: tuple[float, float, float, float] = (0.91764706, 0.6, 0.6, 0.0)
    DARK_GREY: tuple[float, float, float, float] = (0.8, 0.8, 0.8, 0.0)


class GDriveItemStates(Enum):
    FINISHED: int = 0
    FAILED: int = 1
    SKIPPED: int = 2
    PARTIAL: int = 3


class GDriveHandler(metaclass=CloudHandler):

    # consts

    START_ROW: int = 4

    # vars

    client: GoogleDrive = None
    pygsheets_client: Client = None

    available_sheets: dict = {}
    target_sheet: Spreadsheet = None

    available_worksheets: dict = {}
    target_worksheet: Worksheet = None

    current_row: list[Cell] = []

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

    def download(self, url: str, dest: str):
        items = []
        if "file/d/" in url:
            fid = re.findall(r'd/([\w\W]+)/', url)[0]
            file_obj = self.client.CreateFile({'id': fid})
            file_obj.FetchMetadata(fetch_all=True)
            items = [file_obj]
        elif "folders/" in url:
            fid = re.findall(r'folders/(\w+)', url)[0]
            items = self.client.ListFile({'q': "'%s' in parents" % fid}).GetList()
        elif 'folderview' in url:
            fid = re.findall(r'id=(\w+)', url)[0]
            items = self.client.ListFile({'q': "'%s' in parents" % fid}).GetList()

        path = '%s/%s' % ('.temp', dest)
        makedirs(path, exist_ok=True)

        item: GoogleDriveFile
        for item in items:
            try:
                filename = re.sub(r'[\"?><:\\/|*]', '', item.metadata.get('originalFilename'))
                (mime, _) = mimetypes.guess_type(filename)

                if mime is None and item.metadata.get('fileExtension') == '':
                    filename = '%s.%s' % (filename, mimetypes.guess_extension(item.metadata.get('mimeType')))
                elif '.jfif' in filename:
                    filename = filename.replace('.jfif', '.jpg')

                item.GetContentFile("%s/%s" % (path, filename))
            except:
                return False

        return True

    def get_sources_list(self) -> list:
        sheets = self.client.ListFile({
            'q': "'root' in parents and trashed=false and mimeType='application/vnd.google-apps.spreadsheet'",
            'includeItemsFromAllDrives': 'true'
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

    def get_last_row_id(self) -> int:
        empty_cell_id: int = 0
        c: Cell
        for c in self.target_worksheet.get_col(col=GDriveCols.ID+1, returnas='cell'):
            if c.value_unformatted == '' and c.row > 5:
                empty_cell_id = c.row
                break

        return empty_cell_id

    def get_rows(self, start: int, end: int):
        cells: list[Cell]
        for cells in self.target_worksheet.get_values(start=(start + self.START_ROW, GDriveCols.ID+1),
                                                      end=(end + self.START_ROW, GDriveCols.COMM+1), returnas='cell'):
            if self.is_row_excluded(cells):
                continue

            self.current_row = cells
            yield {
                'id': int(cells[GDriveCols.ID].value_unformatted),
                'school': cells[GDriveCols.SCHOOL].value_unformatted,
                'group': cells[GDriveCols.GROUP].value_unformatted,
                'student': cells[GDriveCols.STUDENT].value_unformatted,
                'age': cells[GDriveCols.AGE].value,
                'tutor': cells[GDriveCols.TUTOR].value_unformatted,
                'title': cells[GDriveCols.TITLE].value_unformatted,
                'materials': cells[GDriveCols.MATERIALS].value_unformatted,
                'link': cells[GDriveCols.LINK].value_unformatted,
                'comm': cells[GDriveCols.COMM].value_unformatted
            }

    def is_row_excluded(self, row: list[Cell]) -> bool:
        return self.is_cells_colored(row) or self.is_cell_colored(row[GDriveCols.TITLE]) or\
               self.is_repeated(row[GDriveCols.COMM])

    def is_repeated(self, cell: Cell) -> bool:
        return 'повтор' in cell.value_unformatted.lower() or 'копия' in cell.value_unformatted.lower()

    def is_cells_colored(self, cells: list[Cell]) -> bool:
        for cell in cells:
            if cell.color != GDriveColors.DARK_GREY.value:
                return False

        return True

    def is_cell_colored(self, cell: Cell) -> bool:
        return cell.color == GDriveColors.GREY.value or cell.color == GDriveColors.BLUE.value or\
               cell.color == GDriveColors.GREEN.value or cell.color == GDriveColors.RED.value

    def mark_as(self, state: int):
        if state == GDriveItemStates.FAILED:
            self.current_row[GDriveCols.TITLE].color = GDriveColors.RED.value
        elif state == GDriveItemStates.SKIPPED:
            self.current_row[GDriveCols.TITLE].color = GDriveColors.BLUE.value
        elif state == GDriveItemStates.FINISHED:
            self.current_row[GDriveCols.TITLE].color = GDriveColors.GREY.value
        elif state == GDriveItemStates.PARTIAL:
            self.current_row[GDriveCols.TITLE].color = GDriveColors.GREEN.value


class MailRuHandler(metaclass=CloudHandler):

    def download(self, url: str, dest: str):
        weblink = re.findall(r'/public/(\w+/\w+)', url)[0]

        items_r = requests.get("https://cloud.mail.ru/api/v4/public/list?weblink=" + weblink)
        links_r = requests.get("https://cloud.mail.ru/api/v2/dispatcher", headers={"referer": url})

        if items_r.status_code != 200 | links_r.status_code != 200:

            return False

        items = items_r.json()
        links = links_r.json()

        weblink_get = links.get('body').get('weblink_get')[0].get('url')

        if items.get('type') == "folder":
            item_list = items.get('list')
        else:
            item_list = [items]

        dpath = os.path.join(os.getcwd(), '.temp', dest)
        makedirs(dpath, exist_ok=True)

        if len(item_list) == 0:
            return False

        for item in item_list:
            item_link = weblink_get + "/" + item.get('weblink')
            filename = re.sub(r'[\"?><:\\/|*]', '', item.get("name"))

            if '.jfif' in filename:
                filename = filename.replace('.jfif', '.jpg')

            img = requests.get(item_link, stream=True)

            if img.status_code == 200:
                img.raw.decode_content = True

                with open(os.path.join(dpath, filename), 'w+b') as f:
                    shutil.copyfileobj(img.raw, f)
                    f.flush()

            else:
                return False

        return True

    def set_source(cls, source):
        pass

    def get_sources_list(cls):
        pass


class YaDiskHandler(metaclass=CloudHandler):

    def download(self, url: str, dest: str):
        disk = yadisk.YaDisk()

        items = []
        if ' ' in url:
            urls = url.split(' ')

            for url_i in urls:
                data: yadisk.objects.PublicResourceObject
                try:
                    data = disk.get_public_meta(url_i)
                except:
                    return False

                if data.type == "dir":
                    items.append(data.embedded.items)
                else:
                    items.append(data)
            print(items)
        else:
            data: yadisk.objects.PublicResourceObject
            try:
                data = disk.get_public_meta(url)
                print(data)
            except:
                return False

            if data.type == "dir":
                items = data.embedded.items
            else:
                items = [data]

        dpath = os.path.join(os.getcwd(), '.temp', dest)
        makedirs(dpath, exist_ok=True)

        item: yadisk.objects.PublicResourceObject
        for item in items:
            if item.type == "dir":
                items.extend(item.embedded.items)
                continue

            filename = re.sub(r'[\"?><:\\/|*]', '', item.name)
            (mime, _) = mimetypes.guess_type(filename)

            if mime is None:
                filename = '%s.%s' % (filename, mimetypes.guess_extension(item.mime_type))
            elif '.jfif' in filename:
                filename = filename.replace('.jfif', '.jpg')

            file = requests.get(item.file, stream=True)
            if file.status_code == 200:
                file.raw.decode_content = True

                with open("%s/%s" % (dpath, filename), "wb") as f:
                    shutil.copyfileobj(file.raw, f)

            else:
                return False

        return True

    def set_source(self, source):
        pass

    def get_sources_list(self):
        pass
