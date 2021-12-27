# coding: utf-8

import os
import sys
import configparser


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
            'backup_interval': 1,
            'timezone': ''
        }
        config['DataBase'] = {
            'path_to_db': 'dbase.db',
            'file_retention_period': 30
        }
        config['GUI'] = {
            'show_gui': 1
        }

        with open('config.ini', 'w') as f:
            config.write(f)
        loggers['info'].info(
            'File "config.ini" was created with default values')
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return config
