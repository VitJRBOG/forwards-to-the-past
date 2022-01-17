# coding: utf-8

import os
import sys
import threading
import queue
import time
import datetime
import shutil

import src.model.cfg as cfg
import src.model.db as db
import src.controller.tools as tools
import src.controller.painter as painter
import src.controller.buttons_operations as but_ops


def run(loggers):
    db.db_init(loggers)

    q_start = queue.Queue()

    if cfg.get_show_gui_flag(loggers) == '1':
        q_process = queue.Queue()
        start_with_gui(loggers, q_start, q_process)
    else:
        start_without_gui(loggers, q_start)


def start_without_gui(loggers, q_start):
    threading.Thread(target=checking_for_backup_date, args=(
        loggers, q_start,), daemon=True).start()

    checking_the_backup_start_flag(loggers, q_start, queue.Queue())


def start_with_gui(loggers, q_start, q_process):
    buttons_params = {
        'backup': {
            'func': but_ops.start_backuping,
            'args': [loggers, q_start]
        },
        'restoring': {
            'func': restoring_backup,
            'args': [loggers]
        },
        'settings': {
            'path_to_backup': {
                'func': painter.select_path_to_backup,
                'args': [loggers]
            },
            'path_to_files': {
                'func': painter.select_path_to_files,
                'args': [loggers]
            },
            'path_to_db': {
                'func': painter.select_path_to_db,
                'args': [loggers]
            },
            'save': {
                'func': update_configs,
                'args': [loggers]
            }
        }
    }

    app = painter.make_main_window(loggers, buttons_params)

    threading.Thread(target=checking_the_backup_frame_update_flag,
                     args=(loggers, app.main_frame, q_process,), daemon=True).start()
    threading.Thread(target=checking_the_backup_start_flag, args=(
        loggers, q_start, q_process,), daemon=True).start()
    threading.Thread(target=checking_for_backup_date, args=(
        loggers, q_start,), daemon=True).start()

    app.mainloop()


def checking_for_backup_date(loggers, q_start):
    while True:
        delete_old_backup(loggers)

        today = tools.get_today_date(loggers)
        next_backup_date = tools.compute_next_backup_date(loggers)

        if today.timestamp() >= next_backup_date.timestamp():
            q_start.put('go', block=False, timeout=None)

        time.sleep(5)


def checking_the_backup_start_flag(loggers, q_start, q_progress):
    while True:
        command = q_start.get(block=True, timeout=None)
        if command == 'go':
            q_progress.put(0, block=False, timeout=None)
            making_new_backup(loggers, q_progress)


def checking_the_backup_frame_update_flag(loggers, main_frame,
                                          q_progress):
    while True:
        progress = q_progress.get(block=True, timeout=None)
        if progress == 0:
            painter.update_backup_frame(loggers, main_frame, q_progress)


def making_new_backup(loggers, q):
    filepaths = tools.get_list_filepaths(
        loggers, cfg.get_path_to_files(loggers), [])

    if len(filepaths) > 0:
        progress_share = 50 / len(filepaths)
        changes = []
        for path in filepaths:
            hashsum = tools.compose_file_hashsum(loggers, path)

            if not os.path.isfile(cfg.get_path_to_backup(loggers) + str(hashsum)):
                changes.append(path)
            q.put(progress_share, block=False, timeout=None)

        table_name = tools.compose_table_name(loggers)
        db.create_table(loggers, table_name, ['hashsum', 'path'])

        progress_share = 50 / len(filepaths)
        for path in filepaths:
            hashsum = tools.compose_file_hashsum(loggers, path)
            tools.saving_backup_files(loggers, table_name, path, hashsum)
            if path in changes:
                loggers['info'].info(
                    'File {} was saved as {}'.format(path, hashsum))
            q.put(progress_share, block=False, timeout=None)

    progress_share = 100
    q.put(progress_share, block=False, timeout=None)


def delete_old_backup(loggers):
    try:
        today = tools.get_today_date(loggers)
        backup_obsolescence_date = today - \
            datetime.timedelta(
                float(cfg.get_file_retention_period(loggers)))

        tables = db.select_tables(loggers)

        for table_name in tables:
            if backup_obsolescence_date.timestamp() > float(table_name):
                db.drop_table(loggers, table_name)
                backup_date = datetime.datetime.fromtimestamp(
                    float(table_name))
                logger_msg = '{} backup is obsolete and was deleted.'.format(
                    backup_date.strftime('%d.%m.%Y %H:%M'))
                loggers['info'].info(logger_msg)

        filepaths = tools.get_list_filepaths(
            loggers, cfg.get_path_to_backup(loggers), [])

        tables = db.select_tables(loggers)

        for filepath in filepaths:
            file_name = os.path.basename(filepath)
            for i, table_name in enumerate(tables):
                match = db.select_file_by_hashsum(
                    loggers, table_name, file_name)
                if len(match) != 0:
                    break

                if i == len(tables) - 1:
                    os.remove(filepath)
                    loggers['info'].info(
                        'File {} was deleted.'.format(filepath))

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def restoring_backup(loggers, main_frame, backup_date):
    try:
        q = queue.Queue()

        threading.Thread(target=painter.update_restoring_frame,
                         args=(loggers, main_frame, q,), daemon=True).start()

        table_name = datetime.datetime.strptime(
            backup_date.get(), '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(loggers, int(table_name))

        filepaths = tools.get_list_filepaths(
            loggers, cfg.get_path_to_files(loggers), [])

        progress_share = 50
        if len(filepaths) > 0:
            progress_share = 50 / len(filepaths)
        else:
            q.put(progress_share, block=False, timeout=False)

        for file_path in filepaths:
            os.remove(file_path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 50
        if len(backup_files) > 0:
            progress_share = 50 / len(backup_files)
        else:
            q.put(progress_share, block=False, timeout=False)

        for backup_file in backup_files:
            src_path = '{}{}'.format(
                cfg.get_path_to_backup(loggers), backup_file.hashsum)
            shutil.copyfile(src_path, backup_file.path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def update_configs(loggers, settings_frame):
    config = cfg.get_config(loggers)
    config['General']['path_to_backup'] = settings_frame.path_to_backup.get()
    config['General']['path_to_files'] = settings_frame.path_to_files.get()
    config['General']['backup_interval'] = settings_frame.backup_interval.get()
    config['General']['timezone'] = settings_frame.timezone.get()
    config['DataBase']['path_to_db'] = settings_frame.path_to_db.get()
    config['DataBase']['file_retention_period'] = settings_frame.file_retention_period.get()

    cfg.write_config(loggers, config)
