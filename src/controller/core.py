# coding: utf-8

import os
import sys
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


def run(loggers):
    config = cfg.get_config(loggers)
    db_con = db.connect(loggers)
    if config['GUI']['show_gui'] == '1':
        __show_gui(loggers, db_con)
    else:
        q = queue.Queue()
        files_processing(loggers, db_con, q)
        time.sleep(float(config['General']['backup_interval']) * 86400)

        return run(loggers)


def __show_gui(loggers, db_con):
    app = main_window.MainWindow()

    g_frame = general_frame.GeneralFrame(
        app, start_backing_up, (loggers,))
    update_backup_date_labels(loggers, g_frame, db_con)

    app.mainloop()


def update_backup_date_labels(loggers, g_frame, db_con):
    backup_dates = compose_backups_dates(loggers, db_con)
    g_frame.set_oldest_backup_date(backup_dates['oldest_backup_date'])
    g_frame.set_latest_backup_date(backup_dates['latest_backup_date'])
    g_frame.set_next_backup_date(backup_dates['next_backup_date'])


def start_backing_up(loggers, g_frame):
    db_con = db.connect(loggers)

    q = queue.Queue()

    files_processing(loggers, db_con, q)
        update_backup_date_labels(loggers, g_frame, db_con)

    db_con.close()


def files_processing(loggers, db_con, q):
    config = cfg.get_config(loggers)

    filepaths = __get_list_filepaths(
        loggers, config['General']['path_to_files'], [])

    progress_share = 50 / len(filepaths)
    changes = []
    for path in filepaths:
        hashsum = __get_file_hashsum(loggers, path)

        if not os.path.isfile(config['General']['path_to_backup'] + str(hashsum)):
            changes.append(path)
        q.put(progress_share, block=False, timeout=None)

    if len(changes) > 0:
        table_name = __get_table_name(loggers, config)
        db.create_table(loggers, db_con, table_name, ['hashsum', 'path'])

        progress_share = 50 / len(changes)
        for path in filepaths:
            hashsum = __get_file_hashsum(loggers, path)
            saving_backup_files(loggers, config, db_con,
                                table_name, path, hashsum)
            if path in changes:
                loggers['info'].info(
                    'File {} was saved as {}'.format(path, hashsum))
                q.put(progress_share, block=False, timeout=None)
    else:
        progress_share = 100
        q.put(progress_share, block=False, timeout=None)


def saving_backup_files(loggers, config, con, table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(loggers, con, table_name, file)
    __copy_file(loggers, path, hashsum, config)


def __get_table_name(loggers, config):
    backup_date = __get_backup_date(loggers, config)
    return backup_date.timestamp()


def __get_backup_date(loggers, config):
    tz = pytz.timezone(config['General']['timezone'])
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


def __copy_file(loggers, path, hashsum, config):
    try:
        backup_path = config['General']['path_to_backup'] + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def compose_backups_dates(loggers, db_con):
    backup_dates = {}

    try:
        tables = db.select_tables(loggers, db_con)

        backup_dates['oldest_backup_date'] = __compute_oldest_backup_date(
            loggers, tables)

        backup_dates['latest_backup_date'] = __compute_latest_backup_date(
            loggers, tables)

        backup_dates['next_backup_date'] = __compute_next_backup_date(
            loggers, backup_dates['latest_backup_date'])

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_dates


def __compute_oldest_backup_date(loggers, tables=None, db_con=None):
    oldest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if tables == None:
            if db_con == None:
                db_con = db.connect(loggers)
            tables = db.select_tables(loggers, db_con)

        oldest_backup_date = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                oldest_backup_date = float(table_name)
                continue

            if float(table_name) < oldest_backup_date:
                oldest_backup_date = float(table_name)

        oldest_backup_date = datetime.datetime.fromtimestamp(
            float(oldest_backup_date))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return oldest_backup_date


def __compute_latest_backup_date(loggers, tables=None, db_con=None):
    latest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if tables == None:
            if db_con == None:
                db_con = db.connect(loggers)
            tables = db.select_tables(loggers, db_con)

        latest_backup_date = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                latest_backup_date = float(table_name)

            if latest_backup_date < float(table_name):
                latest_backup_date = float(table_name)

        latest_backup_date = datetime.datetime.fromtimestamp(
            float(latest_backup_date))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return latest_backup_date


def __compute_next_backup_date(loggers, latest_backup_date=None,
                               db_con=None, tables=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        config = cfg.get_config(loggers)

        if latest_backup_date != None:
            config = cfg.get_config(loggers)
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(config['General']['backup_interval']))
        else:
            if tables == None:
                if db_con == None:
                    db_con = db.connect(loggers)
                tables = db.select_tables(loggers, db_con)

            latest_backup_date = __compute_latest_backup_date(
                loggers, tables)

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(config['General']['backup_interval']))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return next_backup_date
