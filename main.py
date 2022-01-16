import re
import os.path
import mimetypes

from dearpygui.dearpygui import *

from internal.settings import Settings
from internal.vkHandler import VKHandler
from internal.cloudHandler import CloudHandler, GDriveHandler, GDriveItemStates, MailRuHandler, YaDiskHandler

current_source_type: str = 'none'
source_types: dict = {
    'gsheet': 'Google Sheets',
    'none': 'Нет'
}

current_source_handler: CloudHandler
source_handlers: dict = {
    'gsheet': GDriveHandler,
    'none': None
}

download_handlers: dict = {
    'gdrive': GDriveHandler,
    'mailru': MailRuHandler,
    'yadisk': YaDiskHandler
}

is_processing: bool = False

_root_dir = os.path.realpath('./')

_settings: Settings = Settings()
_vk_handler: VKHandler = VKHandler()

mimetypes.add_type('image/heif', 'heic')
mimetypes.add_type('image/heif', 'HEIC')

res_total = res_uploaded = res_failed = res_skipped = 0

# Callbacks


def set_current_handler():
    global current_source_type, current_source_handler

    if current_source_type in source_handlers:
        handler = source_handlers.get(current_source_type)
        if handler is not None:
            current_source_handler = handler()
        else:
            current_source_handler = handler
    else:
        current_source_handler = None
        print('Неизвестный тип обработчика')


def set_source_type(sender, app_data):
    global current_source_type

    if app_data in source_types.values():
        new_source_type = {s for s in source_types if source_types[s] == app_data}.pop()
        if new_source_type != current_source_type:
            current_source_type = new_source_type
            set_current_handler()

            if current_source_type == 'none':
                delete_source_file_dialog()
            else:
                delete_source_file_dialog()
                create_source_file_dialog()
    else:
        set_source_type(None, 'Нет')


def set_source_file(sender, app_data):
    if current_source_handler is not None:
        current_source_handler.set_source(app_data)
        delete_source_file_subdialog()
        create_source_file_subdialog()


def set_gsheet_worksheet(sender, app_data):
    if isinstance(current_source_handler, GDriveHandler):
        current_source_handler.set_worksheet(app_data)
        delete_gdrive_file_range_dialog()
        create_gdrive_file_range_dialog()


def update_gsheet_range_end(sender, app_data):
    if get_value('grange_end') <= app_data:
        set_value('grange_end', app_data)


def process(sender, app_data):
    global is_processing, res_uploaded, res_total, res_failed, res_skipped

    if not is_processing:
        res_total = res_uploaded = res_failed = res_skipped = 0
        clear_progress_table()
        delete_upload_results()

        is_processing = True
        disable_proc_inputs()

        for item in current_source_handler.get_rows(start=get_value('grange_start'), end=get_value('grange_end')):
            add_progress_table_row(item.get('id'), item.get('title'))

            download_handler: CloudHandler = None
            if 'drive.google.com' in item.get('link'):
                download_handler = download_handlers.get('gdrive')()
            elif 'cloud.mail.ru' in item.get('link'):
                download_handler = download_handlers.get('mailru')()
            elif 'disk.yandex' in item.get('link') or 'yadi.sk' in item.get('link'):
                download_handler = download_handlers.get('yadisk')()
            elif 'youtube.com' in item.get('link') or 'youtu.be' in item.get('link'):
                total, uploaded, failed, skipped = _vk_handler\
                    .upload_from_link(item, '"$title$". $materials$\nАвтор(ы) - $student$, $age$ лет.\nПедагог(и) - $tutor$.\n$school$, $group$')

                res_total += total
                res_uploaded += uploaded
                res_failed += failed
                res_skipped += skipped

                if uploaded == 0:
                    if failed == 0 and skipped > 0:
                        current_source_handler.mark_as(GDriveItemStates.SKIPPED)
                        update_progress(item.get('id'), 2, 'Работа пропущена: неподдериваемый формат')
                    else:
                        current_source_handler.mark_as(GDriveItemStates.FAILED)
                        update_progress(item.get('id'), 2, 'Ошибка при загрузке в ВК')
                else:
                    if uploaded < total:
                        current_source_handler.mark_as(GDriveItemStates.PARTIAL)
                        update_progress(item.get('id'), 2,
                                        'Частично загружено (возможно, неподдерживаемые файлы или ошибка при загрузке)')
                    else:
                        current_source_handler.mark_as(GDriveItemStates.FINISHED)
                        update_progress(item.get('id'), 2, 'Работа загружена')

                continue
            else:
                update_progress(item.get('id'), 2, 'Ошибка: неподдерживаемый источник')
                continue

            # try:
            if not download_handler.download(item.get('link'), str(item.get('id'))):
                current_source_handler.mark_as(GDriveItemStates.FAILED)
                update_progress(item.get('id'), 2, 'Ошибка при скачивании')
                continue
            # except:
            #     current_source_handler.mark_as(GDriveItemStates.FAILED)
            #     update_progress(item.get('id'), 2, 'Ошибка при скачивании')
            #     continue

            update_progress(item.get('id'), 1)
            # try:
            total, uploaded, failed, skipped = _vk_handler.upload(item, '"$title$". $materials$\nАвтор(ы) - $student$, $age$ лет.\nПедагог(и) - $tutor$.\n$school$, $group$\n\nfile: $file$')
            # except:
            #     current_source_handler.mark_as(GDriveItemStates.FAILED)
            #     update_progress(item.get('id'), 2, 'Ошибка при загрузке в ВК')
            #     continue

            res_total += total
            res_uploaded += uploaded
            res_failed += failed
            res_skipped += skipped

            if uploaded == 0:
                if failed == 0 and skipped > 0:
                    current_source_handler.mark_as(GDriveItemStates.SKIPPED)
                    update_progress(item.get('id'), 2, 'Работа пропущена: неподдериваемый формат')
                else:
                    current_source_handler.mark_as(GDriveItemStates.FAILED)
                    update_progress(item.get('id'), 2, 'Ошибка при загрузке в ВК')
            else:
                if uploaded < total:
                    current_source_handler.mark_as(GDriveItemStates.PARTIAL)
                    update_progress(item.get('id'), 2,
                                    'Частично загружено (возможно, неподдерживаемые файлы или ошибка при загрузке)')
                else:
                    current_source_handler.mark_as(GDriveItemStates.FINISHED)
                    update_progress(item.get('id'), 2, 'Работа загружена')

        create_upload_results()
        is_processing = False
        enable_proc_inputs()


def save_settings(sender, app_data):
    login = get_value('vk_login')
    group_lnk = get_value('vk_group')

    group_id = int(re.findall(r'[club|event](\d+)', group_lnk)[0])

    _settings.update(login, group_id)
    _settings.save()
    update_vk_album_combos()
    delete_settings_window()


def vk_login(sender, app_data):
    login = get_value('vk_login')
    passw = get_value('vk_pass')

    _vk_handler.auth_with_creds(login, passw)


def vk_login_and_close(sender, app_data):
    login = _settings.get_value('login')
    passw = get_value('vk_pass')

    if _vk_handler.auth_with_creds(login, passw):
        delete_vk_login_prompt()


def vk_set_photo_album(sender, app_data):
    _vk_handler.set_photo_album(app_data)


def vk_set_video_album(sender, app_data):
    _vk_handler.set_video_album(app_data)


# GUI mutators


def create_source_file_dialog():
    files: list = list()

    if current_source_handler is not None:
        files = current_source_handler.get_sources_list()

    with group(tag='source_file_dialog', parent='source_dialog'):
        add_combo(tag='source_file_selector', label='Файл', items=files, callback=set_source_file)


def delete_source_file_dialog():
    try:
        delete_item('source_file_dialog')
    except:
        pass


def create_source_file_subdialog():
    if current_source_type == 'gsheet' and isinstance(current_source_handler, GDriveHandler):
        with group(tag='source_file_sub', parent='source_file_dialog'):
            add_combo(tag='source_file_sub_selector', label='Листы таблицы', items=current_source_handler.get_sheets(),
                      callback=set_gsheet_worksheet)
    else:
        pass


def delete_source_file_subdialog():
    try:
        delete_item('source_file_sub')
    except:
        pass


def create_proc_init_button():
    add_button(tag='proc_init_button', label='Начать обработку', callback=process, parent='proc_init_inputs')


def delete_proc_init_button():
    try:
        delete_item('proc_init_button')
    except:
        pass


def create_gdrive_file_range_dialog():
    if current_source_type == 'gsheet' and isinstance(current_source_handler, GDriveHandler):
        max_row = current_source_handler.get_last_row_id()

        with group(tag='source_file_range', parent='source_file_sub'):
            add_input_int(tag='grange_start', label='Начальный ряд', min_value=1, min_clamped=True, default_value=1,
                          step=1, max_value=max_row - 4, max_clamped=True, callback=update_gsheet_range_end)
            add_input_int(tag='grange_end', label='Конечный ряд', min_value=get_value('grange_start'),
                          min_clamped=True,
                          default_value=get_value('grange_start'), step=1, max_value=max_row - 4, max_clamped=True)

        create_proc_init_button()


def delete_gdrive_file_range_dialog():
    try:
        delete_proc_init_button()
        delete_item('source_file_range')
    except:
        pass


def enable_proc_inputs():
    enable_item('source_file_selector')
    enable_item('source_file_sub_selector')
    enable_item('grange_start')
    enable_item('grange_end')
    enable_item('proc_init_button')


def disable_proc_inputs():
    disable_item('source_file_selector')
    disable_item('source_file_sub_selector')
    disable_item('grange_start')
    disable_item('grange_end')
    disable_item('proc_init_button')


def create_settings_window():
    settings = _settings.get_all()
    with window(tag='settings', label='Настройки', pos=(40, 40), no_resize=True,
                width=640, height=460, on_close=delete_settings_window):
        with group(label='Вход в ВКонтакте'):
            add_input_text(tag='vk_login', label='Логин', default_value=settings.get('login'))
            add_input_text(tag='vk_pass', label='Пароль', password=True)
            add_button(label='Вход', callback=vk_login)

        with group(label='Настройки группы'):
            add_input_text(tag='vk_group', label='Ссылка на группу',
                           default_value='https://vk.com/club%s' % settings.get('group'))

        add_button(label='Сохранить', callback=save_settings)


def delete_settings_window():
    try:
        delete_item('settings')
    except:
        pass


def delete_vk_login_prompt():
    try:
        delete_item('vk_auth')
    except:
        pass


def update_vk_album_combos():
    try:
        delete_item('dest_dialog', children_only=True)
        add_combo(tag='vk_photo', label='Альбом для фото', items=_vk_handler.get_albums_photo(), parent='dest_dialog',
                  callback=vk_set_photo_album)
        add_combo(tag='vk_album', label='Альбом для видео', items=_vk_handler.get_albums_video(), parent='dest_dialog',
                  callback=vk_set_video_album)
    except:
        pass


def create_upload_results():
    with group(tag='results', parent='main'):
        with table(header_row=True, borders_innerH=True, borders_innerV=True, borders_outerH=True, borders_outerV=True):
            add_table_column(label='Всего обработано')
            add_table_column(label='Загружено')
            add_table_column(label='Пропущено')
            add_table_column(label='Ошибки')

            with table_row():
                add_text(str(res_total))
                add_text(str(res_uploaded))
                add_text(str(res_skipped))
                add_text(str(res_failed))


def delete_upload_results():
    try:
        delete_item('results')
    except:
        pass


def add_progress_table_row(id: int, title: str):
    with table_row(parent='progress_table'):
        add_text('%i %s' % (id, title[:20]))
        add_slider_int(tag='%i_progress' % id, max_value=2, clamped=True, default_value=0, no_input=False)
        add_text(tag='%i_state' % id, default_value='')


def update_progress(id: int, stage: int, result: str = ''):
    set_value('%i_progress' % id, stage)
    set_value('%i_state' % id, result)


def clear_progress_table():
    try:
        delete_item('progress_table', children_only=True)
        add_table_column(label='ID и название', parent='progress_table')
        add_table_column(label='Прогресс', parent='progress_table')
        add_table_column(label='Результат', parent='progress_table')
    except:
        pass

# GUI


create_context()

with font_registry():
    with font('resources/fonts/OpenSans-Regular.ttf', 18) as font:
        add_font_range_hint(mvFontRangeHint_Default)
        add_font_range_hint(mvFontRangeHint_Cyrillic)

    bind_font(font)

with window(tag='main'):
    with menu_bar():
        with menu(label='Файл'):
            add_menu_item(label='Настройки', callback=create_settings_window)

    if _vk_handler.is_auth_required() and not _vk_handler.auth_with_token():
        with window(tag='vk_auth', label='Повторите вход', pos=(20, 20), width=300, height=150, no_resize=True,
                    on_close=delete_vk_login_prompt):
            add_input_text(tag='vk_login', label='Логин', enabled=False, default_value=_settings.get_value('login'))
            add_input_text(tag='vk_passw', label='Пароль', password=True)
            add_button(label='Вход', callback=vk_login_and_close)

    with group(tag='proc_init_inputs'):
        with group(tag='source_dialog'):
            add_combo(label='Тип источника данных', items=list(source_types.values()), callback=set_source_type)

        add_separator()

        with group(tag='dest_dialog'):
            add_combo(tag='vk_photo', label='Альбом для фото', items=_vk_handler.get_albums_photo(),
                      callback=vk_set_photo_album)
            add_combo(tag='vk_album', label='Альбом для видео', items=_vk_handler.get_albums_video(),
                      callback=vk_set_video_album)

    add_separator()

    with child_window(height=256):
        with table(tag='progress_table', header_row=True, borders_innerH=True, borders_innerV=True, borders_outerH=True,
                   borders_outerV=True):

            add_table_column(label='ID и название')
            add_table_column(label='Прогресс')
            add_table_column(label='Результат')


create_viewport(title='vkUploaderEX', width=800, height=800)
setup_dearpygui()
show_viewport()
set_primary_window('main', True)
start_dearpygui()
destroy_context()
