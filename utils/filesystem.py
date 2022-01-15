import os
import shutil
import warnings
import mimetypes

from fitz import Document
from wand.image import Image

import win32com.client as client


class FileSystem:
    _path: str = ''

    def __init__(self, path: str):
        self._path = path

    def get_path(self) -> str:
        return self._path

    def list_files(self) -> list:
        return os.listdir(self._path)

    def convert_pdf_to_jpg(self, filename: str):
        file = os.path.join(self._path, filename)

        with Document(file) as doc:
            if not doc.is_pdf:
                return None

            new_dir = os.path.join(self._path, filename.replace('.pdf', ''))
            os.makedirs(new_dir)

            i: int = 1
            for page in doc.pages():
                pix = page.get_pixmap()
                pix.save(os.path.join(new_dir, '%i.jpg' % i))
                i += 1

            return FileSystem(new_dir)

    def convert_pptx_to_jpg(self, filename: str):
        file = os.path.join(self._path, filename)

        try:
            (mime, _) = mimetypes.guess_extension(file)
            new_dir = os.path.join(self._path, filename.replace(mime, ''))
            os.makedirs(new_dir)

            powerpoint = client.Dispatch('PowerPoint.Application')
            doc = powerpoint.Presentations.Open(file)

            i: int = 1
            for slide in doc.Slides:
                slide.Export(os.path.join(new_dir, '%i.jpg' % i), 'JPG')
                i += 1

            powerpoint.Quit()
            return FileSystem(new_dir)
        except:
            return None

    def convert_heic_to_jpg(self, filename: str) -> str:
        file = os.path.join(self._path, filename)

        new_filename = filename.lower().replace('.heic', '.jpg')
        new_path = os.path.join(self._path, new_filename)

        open(new_path, 'wb').close()

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with Image(filename=file) as img:
                img.format = 'jpg'

                if img.width > 7000 or img.height > 7000:
                    if img.width > img.height:
                        img.transform(resize='7000x')
                    else:
                        img.transform(resize='x7000')

                img.save(filename=new_path)

        os.remove(file)

        return new_filename

    def resize_img(self, filename: str):
        file = os.path.join(self._path, filename)

        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            with Image(filename=file) as img:
                if img.width > 7000 or img.height > 7000:
                    if img.width > img.height:
                        img.transform(resize='7000x')
                    else:
                        img.transform(resize='x7000')
                    img.save(filename=file)

    def get_mime(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return mime

    def fix_ext(self, filename: str):
        file = os.path.join(self._path, filename)
        try:
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                with Image(filename=file) as img:
                    new_name = '%s.%s' % (filename, mimetypes.guess_extension(img.mimetype))
                    new_path = os.path.join(self._path, new_name)

                    img.save(filename=new_path)

                    os.remove(file)

                    return new_name
        except:
            return None

    def is_image(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return 'image' in mime

    def is_heic(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return 'heif' in mime

    def is_pdf(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return 'pdf' in mime

    def is_pptx(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return 'presentationml' in mime or 'ms-powerpoint' in mime

    def is_video(self, filename: str):
        file = os.path.join(self._path, filename)
        (mime, _) = mimetypes.guess_type(file)
        return 'video' in mime

    def remove(self):
        try:
            shutil.rmtree(self._path)
            return True
        except:
            return False
