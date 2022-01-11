# coding: utf-8

import os
import sys
import threading
import queue
import time
import hashlib
import datetime
import shutil
import pytz

import src.model.cfg as cfg
import src.model.db as db
import src.view.gui as gui


def run(loggers):
    db.db_init(loggers)

    if cfg.get_show_gui_flag(loggers) == '1':
        __show_gui(loggers)
    else:
        checking_for_backup_date(loggers)


def __show_gui(loggers):
    buttons_params = {
        'backup': {
            'func': start_backing_up,
            'args': [loggers]
        },
        'restoring': {
            'func': restoring_backup,
            'args': [loggers]
        },
        'settings': {
            'path_to_backup': {
                'func': select_path_to_backup,
                'args': [loggers]
            },
            'path_to_files': {
                'func': select_path_to_files,
                'args': [loggers]
            },
            'path_to_db': {
                'func': select_path_to_db,
                'args': [loggers]
            },
            'save': {
                'func': update_configs,
                'args': [loggers]
            }
        }
    }

    backups = get_backups_list(loggers)
    configs = cfg.get_config(loggers)

    app = gui.Window(buttons_params, backups, configs)

    update_backup_date_labels(loggers, app.main_frame.backup_frame)

    thread = threading.Thread(
        target=checking_for_backup_date, args=(loggers, app.main_frame,), daemon=True)
    thread.start()

    app.mainloop()


def get_backups_list(loggers):
    tables = db.select_tables(loggers)

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    return backups


def checking_for_backup_date(loggers, main_frame=None):
    while True:
        delete_old_backup(loggers)

        today = __get_backup_date(loggers)
        next_backup_date = __compute_next_backup_date(loggers)

        if today.timestamp() >= next_backup_date.timestamp():
            start_backing_up(loggers, main_frame)

        time.sleep(5)


def update_backup_date_labels(loggers, backup_frame):
    backup_dates = compose_backups_dates(loggers)
    backup_frame.set_oldest_backup_date(backup_dates['oldest_backup_date'])
    backup_frame.set_latest_backup_date(backup_dates['latest_backup_date'])
    backup_frame.set_next_backup_date(backup_dates['next_backup_date'])


def start_backing_up(loggers, main_frame=None):
    q = queue.Queue()

    if main_frame != None:
        thread = threading.Thread(target=update_backup_frame,
                                  args=(loggers, main_frame, q,), daemon=True)
        thread.start()

    delete_old_backup(loggers)

    files_processing(loggers, q)


def update_backup_frame(loggers, main_frame, q):
    main_frame.backup_frame.update_progress_bar(0)
    main_frame.backup_frame.hide_buttons_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.backup_frame.update_progress_bar(progress)
        if progress == 100:
            break

    update_backup_date_labels(loggers, main_frame.backup_frame)

    backups = get_backups_list(loggers)

    main_frame.restoring_frame.update_backup_dates(backups)
    main_frame.backup_frame.hide_progress_bar_show_buttons()


def update_restoring_frame(loggers, main_frame, q):
    main_frame.restoring_frame.update_progress_bar(0)
    main_frame.restoring_frame.hide_button_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.restoring_frame.update_progress_bar(progress)
        if progress == 100:
            break

    main_frame.restoring_frame.hide_progress_bar_show_button()


def files_processing(loggers, q):
    filepaths = __get_list_filepaths(
        loggers, cfg.get_path_to_files(loggers), [])

    if len(filepaths) > 0:
        progress_share = 50 / len(filepaths)
        changes = []
        for path in filepaths:
            hashsum = __get_file_hashsum(loggers, path)

            if not os.path.isfile(cfg.get_path_to_backup(loggers) + str(hashsum)):
                changes.append(path)
            q.put(progress_share, block=False, timeout=None)

        table_name = __get_table_name(loggers)
        db.create_table(loggers, table_name, ['hashsum', 'path'])

        progress_share = 50 / len(filepaths)
        for path in filepaths:
            hashsum = __get_file_hashsum(loggers, path)
            saving_backup_files(loggers, table_name, path, hashsum)
            if path in changes:
                loggers['info'].info(
                    'File {} was saved as {}'.format(path, hashsum))
            q.put(progress_share, block=False, timeout=None)

    progress_share = 100
    q.put(progress_share, block=False, timeout=None)


def saving_backup_files(loggers, table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(loggers, table_name, file)
    __copy_file(loggers, path, hashsum)


def __get_table_name(loggers):
    backup_date = __get_backup_date(loggers)
    table_name = str(backup_date.timestamp()).split('.')[0]
    return table_name


def __get_backup_date(loggers):
    tz = pytz.timezone(cfg.get_timezone(loggers))
    if tz == '':
        tz = pytz.timezone('UTC')
    backup_date = datetime.datetime.now(tz=tz)
    return backup_date


def __get_list_filepaths(loggers, path, filepaths):

    try:
        if os.path.isfile(path):
            filepaths.append(path)
        else:
            for name in os.listdir(path):
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    filepaths.append(filepath)
                else:
                    filepaths = __get_list_filepaths(
                        loggers, filepath, filepaths)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return filepaths


def __get_file_hashsum(loggers, path):
    hash = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
                hash.update(chunk)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return hash.hexdigest()


def __copy_file(loggers, path, hashsum):
    try:
        backup_path = cfg.get_path_to_backup(loggers) + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def delete_old_backup(loggers):
    try:
        today = get_today_date(loggers)
        backup_obsolescence_date = today - \
            datetime.timedelta(
                float(cfg.get_file_retention_period(loggers)))

        tables = db.select_tables(loggers)

        for table_name in tables:
            if backup_obsolescence_date.timestamp() > float(table_name):
                db.drop_table(loggers, table_name)
                backup_date = datetime.datetime.fromtimestamp(
                    float(table_name))
                logger_msg = '{} backup is obsolete and was deleted.'.format(
                    backup_date.strftime('%d.%m.%Y %H:%M'))
                loggers['info'].info(logger_msg)

        filepaths = __get_list_filepaths(
            loggers, cfg.get_path_to_backup(loggers), [])

        tables = db.select_tables(loggers)

        for filepath in filepaths:
            file_name = os.path.basename(filepath)
            for i, table_name in enumerate(tables):
                match = db.select_file_by_hashsum(
                    loggers, table_name, file_name)
                if len(match) != 0:
                    break

                if i == len(tables) - 1:
                    os.remove(filepath)
                    loggers['info'].info(
                        'File {} was deleted.'.format(filepath))

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def restoring_backup(loggers, main_frame, backup_date):
    try:
        q = queue.Queue()

        threading.Thread(target=update_restoring_frame,
                         args=(loggers, main_frame, q,), daemon=True).start()

        table_name = datetime.datetime.strptime(
            backup_date.get(), '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(loggers, int(table_name))

        filepaths = __get_list_filepaths(
            loggers, cfg.get_path_to_files(loggers), [])

        progress_share = 50
        if len(filepaths) > 0:
            progress_share = 50 / len(filepaths)
        else:
            q.put(progress_share, block=False, timeout=False)

        for file_path in filepaths:
            os.remove(file_path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 50
        if len(backup_files) > 0:
            progress_share = 50 / len(backup_files)
        else:
            q.put(progress_share, block=False, timeout=False)

        for backup_file in backup_files:
            src_path = '{}{}'.format(
                cfg.get_path_to_backup(loggers), backup_file.hashsum)
            shutil.copyfile(src_path, backup_file.path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def compose_backups_dates(loggers):
    backup_dates = {}

    try:
        backup_dates['oldest_backup_date'] = __compute_oldest_backup_date(
            loggers)

        backup_dates['latest_backup_date'] = __compute_latest_backup_date(
            loggers)

        backup_dates['next_backup_date'] = __compute_next_backup_date(
            loggers, backup_dates['latest_backup_date'])

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_dates


def __compute_oldest_backup_date(loggers):
    oldest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables(loggers)

        oldest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                oldest = float(table_name)
                continue

            if float(table_name) < oldest:
                oldest = float(table_name)

        oldest_backup_date = datetime.datetime.fromtimestamp(
            float(oldest))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return oldest_backup_date


def __compute_latest_backup_date(loggers):
    latest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables(loggers)

        latest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                latest = float(table_name)

            if latest < float(table_name):
                latest = float(table_name)

        latest_backup_date = datetime.datetime.fromtimestamp(
            float(latest))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return latest_backup_date


def __compute_next_backup_date(loggers, latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
        else:
            tables = db.select_tables(loggers)

            latest_backup_date = __compute_latest_backup_date(
                loggers)

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return next_backup_date


def get_today_date(loggers):
    tz = pytz.timezone(cfg.get_timezone(loggers))
    if tz == '':
        tz = pytz.timezone('UTC')
    today_date = datetime.datetime.now(tz=tz)
    return today_date


def select_path_to_backup(loggers, settings_frame):
    path = gui.open_dir_dialog()
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_backup.set(path)


def select_path_to_files(loggers, settings_frame):
    path = gui.open_dir_dialog()
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_files.set(path)


def select_path_to_db(loggers, settings_frame):
    path = gui.open_filedialog()
    path = os.path.abspath(path)

    if path != '':
        settings_frame.path_to_db.set(path)


def update_configs(loggers, settings_frame):
    config = cfg.get_config(loggers)
    config['General']['path_to_backup'] = settings_frame.path_to_backup.get()
    config['General']['path_to_files'] = settings_frame.path_to_files.get()
    config['General']['backup_interval'] = settings_frame.backup_interval.get()
    config['General']['timezone'] = settings_frame.timezone.get()
    config['DataBase']['path_to_db'] = settings_frame.path_to_db.get()
    config['DataBase']['file_retention_period'] = settings_frame.file_retention_period.get()

    cfg.write_config(loggers, config)
