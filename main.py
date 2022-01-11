from dearpygui.dearpygui import *
from handlers.handler import Handler, GDriveHandler

current_source_type: str = 'none'
source_types: dict = {
    'gsheet': 'Google Sheets',
    'none': 'Нет'
}

current_source_handler: Handler
source_handlers: dict = {
    'gsheet': GDriveHandler(),
    'none': None
}

# Callbacks


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
                create_source_file_dialog()
    else:
        set_source_type(None, 'Нет')


def set_source_file(sender, app_data):
    if current_source_handler is not None:
        current_source_handler.set_source(app_data)
        create_source_file_subdialog()


def set_gsheet_worksheet(sender, app_data):
    if isinstance(current_source_handler, GDriveHandler):
        current_source_handler.set_worksheet(app_data)

# GUI mutators


def create_source_file_dialog():
    files: list = list()

    if current_source_handler is not None:
        files = current_source_handler.get_sources_list()

    with group(tag='source_file_dialog', parent='source_dialog'):
        add_combo(label='Файл', items=files, callback=set_source_file)


def delete_source_file_dialog():
    delete_item('source_file_dialog')


def create_source_file_subdialog():
    if current_source_type == 'gsheet' and isinstance(current_source_handler, GDriveHandler):
        with group(tag='source_file_sub', parent='source_file_dialog'):
            add_combo(label='Листы таблицы', items=current_source_handler.get_sheets(), callback=set_gsheet_worksheet)
    else:
        pass


def set_current_handler():
    global current_source_type, current_source_handler

    if current_source_type in source_handlers:
        current_source_handler = source_handlers.get(current_source_type)
    else:
        current_source_handler = None
        print('Неизвестный тип обработчика')

# GUI


create_context()

with font_registry():
    with font('resources/fonts/OpenSans-Regular.ttf', 18) as font:
        add_font_range_hint(mvFontRangeHint_Default)
        add_font_range_hint(mvFontRangeHint_Cyrillic)

    bind_font(font)

with window(tag='main'):
    with menu_bar():
        with menu(label='test'):
            add_menu_item(label='lol')

    with group(tag='source_dialog'):
        with group():
            add_combo(label='Тип источника данных', items=list(source_types.values()), callback=set_source_type)

    add_separator()

    with group():
        with table(header_row=True, borders_innerH=True, borders_innerV=True, borders_outerH=True, borders_outerV=True):

            add_table_column(label='ID', width_fixed=True, width=120)
            add_table_column(label='Progress')

            for i in range(0, 4):
                with table_row():
                    for j in range(0, 2):
                        add_text(f'Row{i} Column{j}')


create_viewport(title='vkUploaderEX', width=640, height=460)
setup_dearpygui()
show_viewport()
set_primary_window('main', True)
start_dearpygui()
destroy_context()
