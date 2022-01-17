# coding: utf-8

import os

import src.view.gui as gui
import src.controller.tools as tools
import src.model.cfg as cfg


def make_main_window(loggers, buttons_params):
    backups = tools.get_backups_list(loggers)
    configs = cfg.get_config(loggers)

    app = gui.Window(buttons_params, backups, configs)

    update_backup_date_labels(loggers, app.main_frame.backup_frame)

    return app


def update_backup_frame(loggers, main_frame, q):
    main_frame.backup_frame.update_progress_bar(0)
    main_frame.backup_frame.hide_buttons_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.backup_frame.update_progress_bar(progress)
        if progress == 100:
            break

    update_backup_date_labels(loggers, main_frame.backup_frame)

    backups = tools.get_backups_list(loggers)

    main_frame.restoring_frame.update_backup_dates(backups)
    main_frame.backup_frame.hide_progress_bar_show_buttons()


def update_backup_date_labels(loggers, backup_frame):
    backup_dates = tools.compose_backups_dates(loggers)
    backup_frame.set_oldest_backup_date(backup_dates['oldest_backup_date'])
    backup_frame.set_latest_backup_date(backup_dates['latest_backup_date'])
    backup_frame.set_next_backup_date(backup_dates['next_backup_date'])


def update_restoring_frame(loggers, main_frame, q):
    main_frame.restoring_frame.update_progress_bar(0)
    main_frame.restoring_frame.hide_button_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.restoring_frame.update_progress_bar(progress)
        if progress == 100:
            break

    main_frame.restoring_frame.hide_progress_bar_show_button()


def select_path_to_backup(loggers, settings_frame):
    path = gui.open_dir_dialog()
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_backup.set(path)


def select_path_to_files(loggers, settings_frame):
    path = gui.open_dir_dialog()
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_files.set(path)


def select_path_to_db(loggers, settings_frame):
    path = gui.open_filedialog()
    path = os.path.abspath(path)

    if path != '':
        settings_frame.path_to_db.set(path)
