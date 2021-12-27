# coding: utf-8

import os
import sys
import sqlite3

import src.model.cfg as cfg


class File:
    hashsum = ''
    path = ''

    def __init__(self, hashsum, path):
        self.hashsum = hashsum
        self.path = path


def connect(loggers):
    con = sqlite3.connect('')

    config = cfg.get_config(loggers)

    try:
        if not os.path.isfile(config['DataBase']['path_to_db']):
            loggers['info'].info('Database has just been created and is empty')
        con = sqlite3.connect(config['DataBase']['path_to_db'])
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return con


def create_table(loggers, con, table_name, col_names):
    try:
        cur = con.cursor()

        cur.execute('CREATE TABLE "{}" ({})'.format(
            table_name, ', '.join(col_names)))
        con.commit()
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def insert_into_table(loggers, con, table_name, file):
    cur = con.cursor()

    try:
        query = 'INSERT INTO "{}" VALUES (?, ?)'.format(table_name)
        cur.execute(query, [file.hashsum, file.path])
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


def select_tables(loggers, con):
    tables = []

    try:
        cur = con.cursor()

        query = 'SELECT name FROM sqlite_master WHERE type="table"'

        for row in cur.execute(query):
            tables.append(row[0])
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return tables


def __parse_row(loggers, row):
    file = File(row[0], row[1])
    return file
