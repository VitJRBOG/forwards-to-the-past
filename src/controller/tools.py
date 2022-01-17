# coding: utf-8

import os
import sys
import datetime
import hashlib
import shutil
import pytz

import src.model.cfg as cfg
import src.model.db as db


def get_backups_list(loggers):
    tables = db.select_tables(loggers)

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    return backups


def saving_backup_files(loggers, table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(loggers, table_name, file)
    copy_file(loggers, path, hashsum)


def get_file_hashsum(loggers, path):
    hash = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
                hash.update(chunk)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return hash.hexdigest()


def copy_file(loggers, path, hashsum):
    try:
        backup_path = cfg.get_path_to_backup(loggers) + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def get_table_name(loggers):
    backup_date = get_backup_date(loggers)
    table_name = str(backup_date.timestamp()).split('.')[0]
    return table_name


def get_backup_date(loggers):
    tz = pytz.timezone(cfg.get_timezone(loggers))
    if tz == '':
        tz = pytz.timezone('UTC')
    backup_date = datetime.datetime.now(tz=tz)
    return backup_date


def get_list_filepaths(loggers, path, filepaths):

    try:
        if os.path.isfile(path):
            filepaths.append(path)
        else:
            for name in os.listdir(path):
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    filepaths.append(filepath)
                else:
                    filepaths = get_list_filepaths(
                        loggers, filepath, filepaths)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return filepaths


def get_today_date(loggers):
    tz = pytz.timezone(cfg.get_timezone(loggers))
    if tz == '':
        tz = pytz.timezone('UTC')
    today_date = datetime.datetime.now(tz=tz)
    return today_date


def compose_backups_dates(loggers):
    backup_dates = {}

    try:
        backup_dates['oldest_backup_date'] = compute_oldest_backup_date(
            loggers)

        backup_dates['latest_backup_date'] = compute_latest_backup_date(
            loggers)

        backup_dates['next_backup_date'] = compute_next_backup_date(
            loggers, backup_dates['latest_backup_date'])

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_dates


def compute_oldest_backup_date(loggers):
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


def compute_latest_backup_date(loggers):
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


def compute_next_backup_date(loggers, latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
        else:
            tables = db.select_tables(loggers)

            latest_backup_date = compute_latest_backup_date(
                loggers)

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return next_backup_date
