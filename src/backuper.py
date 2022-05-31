import os
import sys
import datetime
import shutil

import tools
import db
import cfg
from src import logging


def making_new_backup(q):
    try:
        filepaths = tools.get_list_filepaths(cfg.get_path_to_files(), [])

        if len(filepaths) > 0:
            progress_share = 50 / len(filepaths)
            changes = []
            for path in filepaths:
                hashsum = tools.compose_file_hashsum(path)

                if not os.path.isfile(cfg.get_path_to_backup() + str(hashsum)):
                    changes.append(path)
                q.put(progress_share, block=False, timeout=None)

            table_name = compose_table_name()
            db.create_table(table_name, ['hashsum', 'path'])

            progress_share = 50 / len(filepaths)
            for path in filepaths:
                hashsum = tools.compose_file_hashsum(path)
                saving_backup_files(table_name, path, hashsum)
                if path in changes:
                    logging.Logger('info').info(
                        'File {} was saved as {}'.format(path, hashsum))
                q.put(progress_share, block=False, timeout=None)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def delete_old_backup():
    try:
        today = tools.get_today_date()
        backup_obsolescence_date = today - datetime.timedelta(
            float(cfg.get_file_retention_period()))

        tables = db.select_tables()

        for table_name in tables:
            if backup_obsolescence_date.timestamp() > float(table_name):
                db.drop_table(table_name)
                backup_date = datetime.datetime.fromtimestamp(
                    float(table_name))
                logger_msg = '{} backup is obsolete and was deleted.'.format(
                    backup_date.strftime('%d.%m.%Y %H:%M'))
                logging.Logger('info').info(logger_msg)

        filepaths = tools.get_list_filepaths(cfg.get_path_to_backup(), [])

        tables = db.select_tables()

        for filepath in filepaths:
            file_name = os.path.basename(filepath)
            for i, table_name in enumerate(tables):
                match = db.select_file_by_hashsum(table_name, file_name)
                if len(match) != 0:
                    break

                if i == len(tables) - 1:
                    os.remove(filepath)
                    logging.Logger('info').info(
                        'File {} was deleted.'.format(filepath))

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def restoring_backup(main_frame, q):
    try:
        backup_date = main_frame.restoring_frame.option.get()
        table_name = datetime.datetime.strptime(
            backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(int(table_name))  # type: ignore

        filepaths = tools.get_list_filepaths(cfg.get_path_to_files(), [])

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
                cfg.get_path_to_backup(), backup_file.hashsum)
            shutil.copyfile(src_path, backup_file.path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def get_backups_list():
    tables = db.select_tables()

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    return backups


def saving_backup_files(table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(table_name, file)
    tools.copy_file(path, hashsum)


def compose_table_name():
    backup_date = tools.get_today_date()
    table_name = str(backup_date.timestamp()).split('.')[0]  # type: ignore
    return table_name


def compose_backups_dates():
    backup_dates = {}

    try:
        backup_dates['oldest_backup_date'] = compute_oldest_backup_date()

        backup_dates['latest_backup_date'] = compute_latest_backup_date()

        backup_dates['next_backup_date'] = compute_next_backup_date(
            backup_dates['latest_backup_date'])

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return backup_dates


def compute_oldest_backup_date():
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


def compute_latest_backup_date():
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


def compute_next_backup_date(latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
        else:
            tables = db.select_tables()

            latest_backup_date = compute_latest_backup_date()

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return next_backup_date