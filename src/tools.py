import os
import sys
import hashlib
import shutil
import pytz
import datetime

import cfg
from src import logging


def get_list_filepaths(path, filepaths):

    try:
        if os.path.isfile(path):
            filepaths.append(path)
        else:
            for name in os.listdir(path):
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    filepaths.append(filepath)
                else:
                    filepaths = get_list_filepaths(filepath, filepaths)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return filepaths


def get_today_date():
    today_date = datetime.datetime(1970, 1, 1)

    try:
        tz = pytz.timezone(cfg.get_timezone())
        if tz == '':
            tz = pytz.timezone('UTC')
        today_date = datetime.datetime.now(tz=tz)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return today_date


def compose_file_hashsum(path):
    hash = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
                hash.update(chunk)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return hash.hexdigest()


def copy_file(path, hashsum):
    try:
        backup_path = cfg.get_path_to_backup() + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()