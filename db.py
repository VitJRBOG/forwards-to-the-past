# coding: utf-8

import os
import sys
import sqlite3
import datetime


class File:
    hashsum = ''
    abs_path_to_original = ''
    abs_path_to_backup = ''
    upd_date = datetime.datetime(1970, 1, 1)

    def __init__(self, hashsum, abs_path_to_original,
                 abs_path_to_backup, upd_date):
        self.hashsum = hashsum
        self.abs_path_to_original = abs_path_to_original
        self.abs_path_to_backup = abs_path_to_backup
        self.upd_date = upd_date


def connect(loggers, config):
    con = sqlite3.Connection('')

    try:
        if os.path.isfile(config['DataBase']['path_to_db']):
            con = sqlite3.connect(config['DataBase']['path_to_db'])
        else:
            con = __init_database__(loggers, config['DataBase']['path_to_db'])
            loggers['info'].info('Database has just been created and is empty')
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return con


def insert_into_file(loggers, con, file):
    cur = con.cursor()

    try:
        query = 'INSERT INTO file VALUES (?, ?, ?, ?)'
        cur.execute(query, [file.hashsum,
                            file.abs_path_to_original,
                            file.abs_path_to_backup,
                            file.upd_date])
        con.commit()
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def select_file_by_hashsum(loggers, con, hashsum):
    files = []

    try:
        cur = con.cursor()
        query = 'SELECT * FROM file WHERE hashsum = ?'
        for row in cur.execute(query, [hashsum]):
            file = __parse_row(loggers, row)
            files.append(file)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return files


def __parse_row(loggers, row):
    file = File(row[0], row[1], row[2], row[3])
    return file


def __init_database__(loggers, path):
    con = sqlite3.connect(path)

    try:
        __create_table(loggers, con, 'file', [
            'hashsum', 'abs_path_to_original',
            'abs_path_to_backup', 'upd_date'])
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return con


def __create_table(loggers, con, table_name, col_names):
    try:
        cur = con.cursor()

        cur.execute('CREATE TABLE {} ({})'.format(
            table_name, ', '.join(col_names)))
        con.commit()
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()
