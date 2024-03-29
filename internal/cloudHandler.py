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
from pydrive2.auth import GoogleAuth, AuthenticationError, RefreshError


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
    SCHOOL: int = 4
    GROUP: int = 5
    STUDENT: int = 9
    AGE: int = 10
    TUTOR: int = 6
    TITLE: int = 16
    MATERIALS: int = 17
    LINK: int = 18
    COMM: int = 19
    RES: int = 25


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
        except RefreshError:
            os.remove('.config/gdrive_creds.json')
            self.__init__()

    def download(self, url: str, dest: str):
        items = []
        if ' ' in url:
            links = url.split(' ')

            for _link in links:

                if "file/d/" in _link or 'presentation/d/' in _link:
                    fid = re.findall(r'd/([\w\W]+)/', _link)[0]
                    print(fid)
                    file_obj = self.client.CreateFile({'id': fid})
                    file_obj.FetchMetadata(fetch_all=True)
                    items.append(file_obj)
                elif "folders/" in _link:
                    fid = re.findall(r'folders/([\w\W][^?]+)', _link)[0]
                    items.extend(self.client.ListFile({'q': "'%s' in parents" % fid}).GetList())
                elif 'folderview' in _link:
                    fid = re.findall(r'id=([\w\W]+)', _link)[0]
                    items.extend(self.client.ListFile({'q': "'%s' in parents" % fid}).GetList())
        else:
            if "file/d/" in url or 'presentation/d/' in url:
                fid = re.findall(r'd/([\w\W]+)/', url)[0]
                print(fid)
                file_obj = self.client.CreateFile({'id': fid})
                file_obj.FetchMetadata(fetch_all=True)
                items = [file_obj]
            elif "folders/" in url:
                fid = re.findall(r'folders/([\w\W][^?]+)', url)[0]
                items = self.client.ListFile({'q': "'%s' in parents" % fid}).GetList()
            elif 'folderview' in url:
                fid = re.findall(r'id=([\w\W]+)', url)[0]
                items = self.client.ListFile({'q': "'%s' in parents" % fid}).GetList()

        dpath = '%s/%s' % ('.temp', dest)
        makedirs(dpath, exist_ok=True)

        item: GoogleDriveFile
        for item in items:
            try:
                if item.metadata.get('mimeType') == 'application/vnd.google-apps.presentation':
                    # _mime = 'application/vnd.openxmlformats-officedocument.presentationml.presentation'
                    _mime = 'application/pdf'
                    link = item.metadata.get('exportLinks')[_mime]
                    ext = mimetypes.guess_extension(_mime)
                    filename = '%s%s' % (item.metadata.get('title'), ext)

                    res = requests.get(link, stream=True)

                    if res.status_code == 200:
                        res.raw.decode_content = True

                        with open(os.path.join(dpath, filename), 'w+b') as f:
                            shutil.copyfileobj(res.raw, f)
                            f.flush()

                    else:
                        return False

                else:
                    filename = re.sub(r'[\"?><:\\/|*]', '', item.metadata.get('originalFilename'))
                    (mime, _) = mimetypes.guess_type(filename)

                    if mime is None and item.metadata.get('fileExtension') == '':
                        filename = '%s%s' % (filename, mimetypes.guess_extension(item.metadata.get('mimeType')))
                    elif '.jfif' in filename:
                        filename = filename.replace('.jfif', '.jpg')

                    item.GetContentFile("%s/%s" % (dpath, filename))
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

        return empty_cell_id-1

    def get_rows(self, start: int, end: int):
        cells: list[Cell]
        for cells in self.target_worksheet.get_values(start=(start + self.START_ROW, GDriveCols.ID+1),
                                                      end=(end + self.START_ROW, GDriveCols.RES+1), returnas='cell'):
            if self.is_row_excluded(cells):
                continue

            self.current_row = cells
            yield {
                'no': int(cells[GDriveCols.ID].row),
                'id': int(cells[GDriveCols.ID].value_unformatted),
                'school': cells[GDriveCols.SCHOOL].value_unformatted,
                'group': cells[GDriveCols.GROUP].value_unformatted,
                'student': cells[GDriveCols.STUDENT].value_unformatted,
                'age': cells[GDriveCols.AGE].value,
                'tutor': cells[GDriveCols.TUTOR].value_unformatted,
                'title': str(cells[GDriveCols.TITLE].value_unformatted),
                'materials': cells[GDriveCols.MATERIALS].value_unformatted,
                'link': cells[GDriveCols.LINK].value_unformatted,
                'comm': cells[GDriveCols.COMM].value_unformatted,
                'res': cells[GDriveCols.RES].value_unformatted
            }

    def is_row_excluded(self, row: list[Cell]) -> bool:
        return self.is_excluded(row[GDriveCols.RES])

    def is_excluded(self, cell: Cell) -> bool:
        return any(res in cell.value_unformatted for res in [ 'аннулирован'])
# 'Гран-при', 'Специальный', 'Лауреат I степени'
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
        url = ''.join(re.findall(r'(https://[^а-я\s]+)', url, re.IGNORECASE))

        if ' ' in url:
            urls = url.split(' ')

            for url_i in urls:
                data: yadisk.objects.PublicResourceObject
                try:
                    data = disk.get_public_meta(url_i)
                except:
                    return False

                if data.type == "dir":
                    items.extend(data.embedded.items)
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
                filename = '%s%s' % (filename, mimetypes.guess_extension(item.mime_type))
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
