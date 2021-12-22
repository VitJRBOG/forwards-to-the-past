# coding: utf-8

import os
import sys
import hashlib
import datetime
import shutil
import pytz

import cfg
import db


def files_processing(loggers, q):
    config = cfg.get_config(loggers)

    con = db.connect(loggers, config)
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
        db.create_table(loggers, con, table_name, ['hashsum', 'path'])

        progress_share = 50 / len(changes)
        for path in filepaths:
            hashsum = __get_file_hashsum(loggers, path)
            saving_backup_files(loggers, config, con,
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
        tz = None
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
