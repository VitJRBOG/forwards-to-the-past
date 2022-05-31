import os
import sys
import datetime
import shutil
import queue
import threading

import gui
import cfg
import db
import backuper
from src import logging, painter


def start_backuping(q_start):
    q_start.put('go', block=False, timeout=None)


def start_backup_restoring(main_frame):
    q = queue.Queue()
    threading.Thread(target=painter.update_restoring_frame,
                     args=(main_frame, q,), daemon=True).start()
    backuper.restoring_backup(main_frame, q)


def select_path_to_backup(settings_frame):
    path = gui.open_dir_dialog('Выберите папку для хранения резервных копий')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_backup.set(path)


def select_path_to_files(settings_frame):
    path = gui.open_dir_dialog('Выберите папку для создания резервной копии')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_files.set(path)


def select_path_to_db(settings_frame):
    path = gui.open_filedialog()
    path = os.path.abspath(path)

    if path != '':
        settings_frame.path_to_db.set(path)


def update_configs(settings_frame):
    try:
        config = cfg.get_config()
        config['General']['path_to_backup'] = settings_frame.path_to_backup.get()
        config['General']['path_to_files'] = settings_frame.path_to_files.get()
        config['General']['backup_interval'] = settings_frame.backup_interval.get()
        config['General']['timezone'] = settings_frame.timezone.get()
        config['DataBase']['path_to_db'] = settings_frame.path_to_db.get()
        config['DataBase']['file_retention_period'] = settings_frame.file_retention_period.get()

        cfg.write_config(config)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def copying_backuped_file(restoring_frame):
    backup_date = restoring_frame.option.get()
    table_name = datetime.datetime.strptime(
        backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

    backup_files = db.select_files(int(table_name))

    selected_item = restoring_frame.files_table.focus()
    filepath = restoring_frame.files_table.item(selected_item)['values'][0]

    backuped_file_path = ''

    for item in backup_files:
        if item.path == filepath:
            backuped_file_path = '{}{}'.format(
                cfg.get_path_to_backup(), item.hashsum)

    filename = os.path.basename(filepath)

    dest_dir = gui.open_dir_dialog('Выберите папку для сохранения файла')

    shutil.copyfile(backuped_file_path, os.path.join(dest_dir, filename))


def switch_hide_startup(hide_startup_flag):
    config = cfg.get_config()
    if config['GUI']['hide_startup'] == '0':
        config['GUI']['hide_startup'] = '1'
        hide_startup_flag = '1'
    elif config['GUI']['hide_startup'] == '1':
        config['GUI']['hide_startup'] = '0'
        hide_startup_flag = '0'

    cfg.write_config(config)


def hide_gui(app):
    config = cfg.get_config()
    config['GUI']['show_gui'] = '0'
    cfg.write_config(config)

    app.withdraw()