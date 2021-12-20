# coding: utf-8

import os
import sys
import hashlib
import datetime
import shutil

import db


def files_processing(loggers, config):
    filepaths = __get_list_filepaths(
        loggers, config['General']['path_to_files'], [])
    for path in filepaths:
        hashsum = __get_file_hashsum(loggers, path)
        con = db.connect(loggers, config)
        noted_files = db.select_file_by_hashsum(loggers, con, hashsum)
        if len(noted_files) == 0:
            modification_date = __get_file_date_modification(loggers, path)
            backup_path = __copy_file(loggers, path, hashsum, config)
            file = db.File(hashsum, path, backup_path, modification_date)
            db.insert_into_file(loggers, con, file)


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


def __get_file_date_modification(loggers, path):
    modification_date = datetime.datetime(1970, 1, 1)

    try:
        modification_date = os.path.getatime(path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return modification_date


def __copy_file(loggers, path, hashsum, config):
    backup_path = ''

    try:
        backup_path = config['General']['path_to_backup'] + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_path
