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
import src.view.main_window as main_window
import src.view.general_frame as general_frame
import src.view.backup_restoring_window as backup_restoring_window


def run(loggers):
    db.db_init(loggers)

    if cfg.get_show_gui_flag(loggers) == '1':
        __show_gui(loggers)
    else:
        checking_for_backup_date(loggers)


def __show_gui(loggers):
    app = main_window.MainWindow()

    params_for_btn = {
        'start': {
            'func': start_backing_up,
            'args': [loggers]
        },
        'restore': {
            'func': show_backup_restoring_window,
            'args': [loggers, app]
        }
    }

    g_frame = general_frame.GeneralFrame(
        app, params_for_btn)
    update_backup_date_labels(loggers, g_frame)

    thread = threading.Thread(
        target=checking_for_backup_date, args=(loggers, g_frame,), daemon=True)
    thread.start()

    app.mainloop()


def show_backup_restoring_window(loggers, app, master):
    tables = db.select_tables(loggers)

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    params_for_btn = {
        'func': restoring_backup,
        'args': [loggers, backups]
    }

    window = backup_restoring_window.Window(app, backups, params_for_btn)


def checking_for_backup_date(loggers, g_frame=None):
    while True:
        delete_old_backup(loggers)

        today = __get_backup_date(loggers)
        next_backup_date = __compute_next_backup_date(loggers)

        if today.timestamp() >= next_backup_date.timestamp():
            start_backing_up(loggers, g_frame)

        time.sleep(5)


def update_backup_date_labels(loggers, g_frame):
    backup_dates = compose_backups_dates(loggers)
    g_frame.set_oldest_backup_date(backup_dates['oldest_backup_date'])
    g_frame.set_latest_backup_date(backup_dates['latest_backup_date'])
    g_frame.set_next_backup_date(backup_dates['next_backup_date'])


def start_backing_up(loggers, g_frame=None):
    delete_old_backup(loggers)

    q = queue.Queue()

    files_processing(loggers, q)

    if g_frame != None:
        update_backup_date_labels(loggers, g_frame)


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
    else:
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


def restoring_backup(loggers, backup_date):
    try:
        table_name = datetime.datetime.strptime(
            backup_date.get(), '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(loggers, int(table_name))

        filepaths = __get_list_filepaths(
            loggers, cfg.get_path_to_files(loggers), [])

        for file_path in filepaths:
            os.remove(file_path)

        for backup_file in backup_files:
            src_path = '{}{}'.format(
                cfg.get_path_to_backup(loggers), backup_file.hashsum)
            shutil.copyfile(src_path, backup_file.path)
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
