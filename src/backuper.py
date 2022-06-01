import os
import sys
import datetime
import shutil

import tools
import db
import cfg
from src import logging


def making_new_backup(q):
    filepaths = tools.get_list_filepaths(cfg.get_path_to_files(), [])

    if len(filepaths) > 0:
        progress_share = 50 / len(filepaths)
        new_backup_files = __compose_new_backup_files_list(q, filepaths)
        table_name = __create_new_backup_info_table()
        __create_new_backup_files(q, filepaths, table_name, new_backup_files)                

    progress_share = 100
    q.put(progress_share, block=False, timeout=None)


def __compose_new_backup_files_list(q, filepaths):
    try:
        new_backup_files = []
        progress_share = 50 / len(filepaths)
        for path in filepaths:
            hashsum = tools.compose_file_hashsum(path)
            if not os.path.isfile(cfg.get_path_to_backup() + str(hashsum)):
                new_backup_files.append(path)
            __put_progress_date_to_progressbar(q, progress_share)

        return new_backup_files
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __create_new_backup_info_table():
    table_name = __compose_table_name()
    db.create_table(table_name, ['hashsum', 'path'])

    return table_name


def __compose_table_name():
    try:
        backup_date = tools.get_today_date()
        table_name = str(backup_date.timestamp()).split('.')[0]
        return table_name
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __create_new_backup_files(q, filepaths, table_name, new_backup_files):
    try:
        progress_share = 50 / len(filepaths)
        for path in filepaths:
            hashsum = tools.compose_file_hashsum(path)
            __saving_backup_files(table_name, path, hashsum)
            if path in new_backup_files:
                logging.Logger('info').info(
                    'File {} was saved as {}'.format(path, hashsum))
            __put_progress_date_to_progressbar(q, progress_share)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __saving_backup_files(table_name, path, hashsum):
    try:
        file = db.File(hashsum, path)
        db.insert_into_table(table_name, file)
        tools.copy_file(path, hashsum)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def deleting_old_backups():
    try:
        tables = db.select_tables()
        for table_name in tables:
            if __backup_is_obsoleted(table_name):
                __delete_old_backup_table_info(table_name)
        filepaths = tools.get_list_filepaths(cfg.get_path_to_backup(), [])
        remaining_tables = db.select_tables()
        __delete_old_backup_files(filepaths, remaining_tables)

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __backup_is_obsoleted(table_name):
    today = tools.get_today_date()
    backup_obsolescence_date = today - datetime.timedelta(
        float(cfg.get_file_retention_period()))
    return backup_obsolescence_date.timestamp() > float(table_name)


def __delete_old_backup_table_info(table_name):
    db.drop_table(table_name)
    backup_date = datetime.datetime.fromtimestamp(float(table_name))
    logger_msg = '{} backup is obsolete and was deleted.'.format(
        backup_date.strftime('%d.%m.%Y %H:%M'))
    logging.Logger('info').info(logger_msg)


def __delete_old_backup_files(filepaths, remaining_tables):
    for filepath in filepaths:
        file_name = os.path.basename(filepath)
        for i, table_name in enumerate(remaining_tables):
            match = db.select_file_by_hashsum(table_name, file_name)
            if len(match) != 0:
                break

            if i == len(remaining_tables) - 1:
                os.remove(filepath)
                logging.Logger('info').info(
                    'File {} was deleted.'.format(filepath))


def restoring_backup(main_frame, q):
    try:
        backup_date = main_frame.restoring_frame.option.get()
        backup_files = __fetch_backup_files(backup_date)
        __removing_files_from_source_dir(q)
        __copying_backup_files_to_source_dir(q, backup_files)

        __put_progress_date_to_progressbar(q, progress_share=100)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __fetch_backup_files(backup_date):
    table_name = datetime.datetime.strptime(
        backup_date, '%d.%m.%Y %H:%M:%S').timestamp()
    backup_files = db.select_files(int(table_name))

    return backup_files


def __removing_files_from_source_dir(q):
    filepaths = tools.get_list_filepaths(cfg.get_path_to_files(), [])
    progress_share = 50
    if len(filepaths) > 0:
        progress_share = 50 / len(filepaths)
    else:
        __put_progress_date_to_progressbar(q, progress_share)

    for file_path in filepaths:
        os.remove(file_path)
        __put_progress_date_to_progressbar(q, progress_share)


def __copying_backup_files_to_source_dir(q, backup_files):
    progress_share = 50
    if len(backup_files) > 0:
        progress_share = 50 / len(backup_files)
    else:
        __put_progress_date_to_progressbar(q, progress_share)

    for backup_file in backup_files:
        src_path = '{}{}'.format(
            cfg.get_path_to_backup(), backup_file.hashsum)
        shutil.copyfile(src_path, backup_file.path)
        __put_progress_date_to_progressbar(q, progress_share)


def __put_progress_date_to_progressbar(q, progress_share):
    q.put(progress_share, block=False, timeout=None)


def get_backup_dates_list():
    try:
        tables = db.select_tables()

        backups = []

        for table_name in tables:
            backup = datetime.datetime.fromtimestamp(float(table_name))
            backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

        return backups
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def compose_backups_dates():
    try:
        backup_dates = {}
        backup_dates['oldest_backup_date'] = __compute_oldest_backup_date()
        backup_dates['latest_backup_date'] = __compute_latest_backup_date()
        backup_dates['next_backup_date'] = compute_next_backup_date(
            backup_dates['latest_backup_date'])
        return backup_dates

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def compute_next_backup_date(latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
        else:
            latest_backup_date = __compute_latest_backup_date()

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return next_backup_date


def __compute_oldest_backup_date():
    oldest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables()

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
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return oldest_backup_date


def __compute_latest_backup_date():
    latest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables()

        latest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                latest = float(table_name)

            if latest < float(table_name):
                latest = float(table_name)

        latest_backup_date = datetime.datetime.fromtimestamp(
            float(latest))
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return latest_backup_date