# coding: utf-8

import os
import sys
import threading
import queue
import time
import watchdog.observers

import cfg
import db
import tools
import backuper
import gui
import buttonhandler
import painter
import event_handler
from src import logging


def run():
    db.db_init()

    start_with_gui(q_start=queue.Queue(), q_process=queue.Queue())


def initialization():
    config = cfg.get_config()

    if config['General']['path_to_backup'] == '':
        title = 'Выберите папку для хранения резервных копий'
        config['General']['path_to_backup'] = os.path.join(
            gui.open_dir_dialog(title), '')
        cfg.write_config(config)

    if config['General']['path_to_files'] == '':
        title = 'Выберите папку для создания резервной копии'
        config['General']['path_to_files'] = os.path.join(
            gui.open_dir_dialog(title), '')
        cfg.write_config(config)

    if config['General']['timezone'] == '':
        config['General']['timezone'] = 'Asia/Yekaterinburg'
        cfg.write_config(config)


def start_with_gui(q_start, q_process):
    try:
        app = make_main_window(q_start)

        config = cfg.get_config()
        config['GUI']['show_gui'] = '1'
        cfg.write_config(config)

        config_modifications_observing(app, [config])

        initialization()

        if config['GUI']['hide_startup'] == '1':
            buttonhandler.hide_gui(app)

        threading.Thread(target=checking_the_backup_frame_update_flag,
                        args=(app.main_frame, q_process,), daemon=True).start()
        threading.Thread(target=checking_the_backup_start_flag, args=(
            q_start, q_process,), daemon=True).start()
        threading.Thread(target=checking_for_backup_date, args=(
            q_start,), daemon=True).start()

        app.mainloop()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def config_modifications_observing(app, for_config):
    try:
        e = event_handler.EventHandler(
            checking_config_modifications, [app, for_config])
        observer = watchdog.observers.Observer()
        observer.schedule(e, path='./', recursive=False)
        observer.start()
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def checking_config_modifications(app, for_config):
    if cfg.get_show_gui_flag() == '1':
        show_gui(app)

    if cfg.get_backup_interval() != for_config[0]['General']['backup_interval']:
        painter.update_backup_date_labels(app.main_frame.backup_frame)

    for_config[0] = cfg.get_config()


def show_gui(app):
    time.sleep(1)
    app.deiconify()


def checking_for_backup_date(q_start):
    while True:
        backuper.delete_old_backup()

        today = tools.get_today_date()
        next_backup_date = backuper.compute_next_backup_date()

        if today.timestamp() >= next_backup_date.timestamp():
            q_start.put('go', block=False, timeout=None)

        time.sleep(5)


def checking_the_backup_start_flag(q_start, q_progress):
    while True:
        command = q_start.get(block=True, timeout=None)
        if command == 'go':
            q_progress.put(0, block=False, timeout=None)
            backuper.making_new_backup(q_progress)


def checking_the_backup_frame_update_flag(main_frame, q_progress):
    while True:
        progress = q_progress.get(block=True, timeout=None)
        if progress == 0:
            painter.update_backup_frame(main_frame, q_progress)


def make_main_window(q_start):
    buttons_params = {
        'backup': {
            'func': buttonhandler.start_backuping,
            'args': [q_start]
        },
        'restoring': {
            'restore': {
                'func': buttonhandler.start_backup_restoring,
                'args': []
            },
            'copy': {
                'func': buttonhandler.copying_backuped_file,
                'args': []
            }
        },
        'settings': {
            'path_to_backup': {
                'func': buttonhandler.select_path_to_backup,
                'args': []
            },
            'path_to_files': {
                'func': buttonhandler.select_path_to_files,
                'args': []
            },
            'path_to_db': {
                'func': buttonhandler.select_path_to_db,
                'args': []
            },
            'hide_startup': {
                'func': buttonhandler.switch_hide_startup,
                'args': [cfg.get_hide_startup_flag()]
            },
            'hide_gui': {
                'func': buttonhandler.hide_gui,
                'args': []
            },
            'save': {
                'func': buttonhandler.update_configs,
                'args': []
            }
        }
    }

    backups = backuper.get_backups_list()
    configs = cfg.get_config()

    app = gui.Window(buttons_params, backups, configs)

    buttons_params['restoring']['restore']['args'].extend([app.main_frame])
    buttons_params['restoring']['copy']['args'].extend(
        [app.main_frame.restoring_frame])
    buttons_params['settings']['path_to_backup']['args'].append(
        app.main_frame.settings_frame)
    buttons_params['settings']['path_to_files']['args'].append(
        app.main_frame.settings_frame)
    buttons_params['settings']['path_to_db']['args'].append(
        app.main_frame.settings_frame)
    buttons_params['settings']['hide_gui']['args'].append(app)
    buttons_params['settings']['save']['args'].append(
        app.main_frame.settings_frame)

    painter.update_backup_date_labels(app.main_frame.backup_frame)

    return app
