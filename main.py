# coding: utf-8

import os
import sys
import logging
import configparser
import hashlib


def __get_list_filepaths(path, filepaths):
    if os.path.isfile(path):
        filepaths.append(path)
    else:
        for name in os.listdir(path):
            filepath = os.path.join(path, name)
            if os.path.isfile(filepath):
                filepaths.append(filepath)
            else:
                filepaths = __get_list_filepaths(filepath, filepaths)

    return filepaths


def __get_file_hashsum(path):
    hash = hashlib.md5()
    with open(path, 'rb') as f:
        for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
            hash.update(chunk)
    return hash.hexdigest()


def get_config(loggers):
    config = configparser.ConfigParser()

    if os.path.isfile('config.ini'):
        config.read('config.ini')
    else:
        config = __make_default_config(loggers)

    return config


def __make_default_config(loggers):
    config = configparser.ConfigParser()

    try:
        config['General'] = {
            'path_to_files': '',
            'path_to_backup': ''
        }
        config['DataBase'] = {
            'path_to_db': 'dbase.db'
        }

        with open('config.ini', 'w') as f:
            config.write(f)
        loggers['info'].info(
            'File "config.ini" was created with default values')
    except Exception:
        loggers['critical'].exception()
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
