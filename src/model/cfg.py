# coding: utf-8

import os
import sys
import configparser


def get_path_to_backup(loggers):
    config = __get_config(loggers)
    return config['General']['path_to_backup']


def get_path_to_files(loggers):
    config = __get_config(loggers)
    return config['General']['path_to_files']


def get_backup_interval(loggers):
    config = __get_config(loggers)
    return config['General']['backup_interval']


def get_timezone(loggers):
    config = __get_config(loggers)
    return config['General']['timezone']


def get_path_to_db(loggers):
    config = __get_config(loggers)
    return config['DataBase']['path_to_db']


def get_file_retention_period(loggers):
    config = __get_config(loggers)
    return config['DataBase']['file_retention_period']


def get_show_gui_flag(loggers):
    config = __get_config(loggers)
    return config['GUI']['show_gui']


def __get_config(loggers):
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
