# coding: utf-8

import os
import sys
import logging
import configparser
import hashlib
import datetime
import shutil
import time

import db


def main():
    logging.basicConfig()
    loggers = {
        'info': __create_logger('info'),
        'warning': __create_logger('warning'),
        'critical': __create_logger('critical')
    }
    loggers['info'].info('Program was started')

    __run(loggers)


def __run(loggers):
    while True:
        config = get_config(loggers)
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

        time.sleep(float(config['General']['checking_interval']))


def __copy_file(loggers, path, hashsum, config):
    backup_path = ''

    try:
        backup_path = config['General']['path_to_backup'] + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_path


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


def get_config(loggers):
    config = configparser.ConfigParser()

    try:
        if os.path.isfile('config.ini'):
            config.read('config.ini')
        else:
            config = __make_default_config(loggers)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return config


def __make_default_config(loggers):
    config = configparser.ConfigParser()

    try:
        config['General'] = {
            'path_to_files': '',
            'path_to_backup': '',
            'checking_interval': 300
        }
        config['DataBase'] = {
            'path_to_db': 'dbase.db',
            'file_retention_period': 30
        }

        with open('config.ini', 'w') as f:
            config.write(f)
        loggers['info'].info(
            'File "config.ini" was created with default values')
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return config


def __create_logger(logger_name):
    logger = logging.getLogger(logger_name)

    msg_format = ''

    file_handler = logging.FileHandler('log.log')
    if logger_name == 'critical':
        logger.setLevel(logging.CRITICAL)
        msg_format = '%(asctime)s - [%(levelname)s] - ' + \
            '(%(filename)s).%(funcName)s(%(lineno)d) - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    if logger_name == 'warning':
        logger.setLevel(logging.WARNING)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    else:
        logger.setLevel(logging.INFO)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    file_handler.setFormatter(logging.Formatter(msg_format))

    logger.addHandler(file_handler)

    return logger


if __name__ == '__main__':
    main()
