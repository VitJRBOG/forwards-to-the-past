# coding: utf-8

import os
import sys
import configparser

import src.model.logging as logging


def get_path_to_backup():
    config = get_config()
    return config['General']['path_to_backup']


def get_path_to_files():
    config = get_config()
    return config['General']['path_to_files']


def get_backup_interval():
    config = get_config()
    return config['General']['backup_interval']


def get_timezone():
    config = get_config()
    return config['General']['timezone']


def get_path_to_db():
    config = get_config()
    return config['DataBase']['path_to_db']


def get_file_retention_period():
    config = get_config()
    return config['DataBase']['file_retention_period']


def get_show_gui_flag():
    config = get_config()
    return config['GUI']['show_gui']


def get_hide_startup_flag():
    config = get_config()
    return config['GUI']['hide_startup']


def get_config():
    config = configparser.ConfigParser()

    try:
        if os.path.isfile('config.ini'):
            config.read('config.ini')
        else:
            config = __make_default_config()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return config


def write_config(config):
    try:
        with open('config.ini', 'w') as f:
            config.write(f)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def __make_default_config():
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
            'show_gui': 1,
            'hide_startup': 0
        }

        with open('config.ini', 'w') as f:
            config.write(f)
        logging.Logger('critical').info(
            'File "config.ini" was created with default values')
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return config
