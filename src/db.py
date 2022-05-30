# coding: utf-8

import os
import sys
import sqlite3

import cfg
from src import logging


def db_init():
    try:
        if not os.path.isfile(cfg.get_path_to_db()):
            logging.Logger('info').info('Database has just been created and is empty')
        db_con = sqlite3.connect(cfg.get_path_to_db())
        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


class File:
    hashsum = ''
    path = ''

    def __init__(self, hashsum, path):
        self.hashsum = hashsum
        self.path = path


def create_table(table_name, col_names):
    try:
        db_con = __connect()
        cur = db_con.cursor()

        cur.execute('CREATE TABLE "{}" ({})'.format(
            table_name, ', '.join(col_names)))
        db_con.commit()
        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def insert_into_table(table_name, file):
    try:
        db_con = __connect()
        cur = db_con.cursor()

        query = 'INSERT INTO "{}" VALUES (?, ?)'.format(table_name)
        cur.execute(query, [file.hashsum, file.path])

        db_con.commit()
        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def drop_table(table_name):
    try:
        db_con = __connect()
        cur = db_con.cursor()

        query = 'DROP TABLE "{}"'.format(table_name)
        cur.execute(query)

        db_con.commit()
        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def select_files(table_name):
    files = []

    try:
        db_con = __connect()
        cur = db_con.cursor()

        query = 'SELECT * FROM "{}"'.format(table_name)
        for row in cur.execute(query):
            file = __parse_row(row)
            files.append(file)

        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return files


def select_file_by_hashsum(table_name, hashsum):
    files = []

    try:
        db_con = __connect()
        cur = db_con.cursor()

        query = 'SELECT * FROM "{}" WHERE hashsum = ?'.format(table_name)
        for row in cur.execute(query, [hashsum]):
            file = __parse_row(row)
            files.append(file)

        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return files


def select_tables():
    tables = []

    try:
        db_con = __connect()
        cur = db_con.cursor()

        query = 'SELECT name FROM sqlite_master WHERE type="table"'

        for row in cur.execute(query):
            tables.append(row[0])

        db_con.close()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return tables


def __parse_row(row):
    file = File(row[0], row[1])
    return file


def __connect():
    con = sqlite3.connect(cfg.get_path_to_db())
    return con
