# coding: utf-8

import os
import sys
import threading
import queue
import time
import datetime
import hashlib
import shutil
import pytz
import watchdog.observers

import src.model.cfg as cfg
import src.model.db as db
import src.view.gui as gui
import src.controller.event_handler as event_handler


def run(loggers):
    db.db_init(loggers)

    start_with_gui(loggers, q_start=queue.Queue(), q_process=queue.Queue())


def initialization(loggers):
    config = cfg.get_config(loggers)

    if config['General']['path_to_backup'] == '':
        title = 'Выберите папку для хранения резервных копий'
        config['General']['path_to_backup'] = os.path.join(
            gui.open_dir_dialog(title), '')
        cfg.write_config(loggers, config)

    if config['General']['path_to_files'] == '':
        title = 'Выберите папку для создания резервной копии'
        config['General']['path_to_files'] = os.path.join(
            gui.open_dir_dialog(title), '')
        cfg.write_config(loggers, config)

    if config['General']['timezone'] == '':
        config['General']['timezone'] = 'Asia/Yekaterinburg'
        cfg.write_config(loggers, config)


def start_with_gui(loggers, q_start, q_process):
    app = make_main_window(loggers, q_start)

    config = cfg.get_config(loggers)
    config['GUI']['show_gui'] = '1'
    cfg.write_config(loggers, config)

    config_modifications_observing(loggers, app, [config])

    initialization(loggers)

    if config['GUI']['hide_startup'] == '1':
        hide_gui(loggers, app)

    threading.Thread(target=checking_the_backup_frame_update_flag,
                     args=(loggers, app.main_frame, q_process,), daemon=True).start()
    threading.Thread(target=checking_the_backup_start_flag, args=(
        loggers, q_start, q_process,), daemon=True).start()
    threading.Thread(target=checking_for_backup_date, args=(
        loggers, q_start,), daemon=True).start()

    app.mainloop()


def config_modifications_observing(loggers, app, for_config):
    e = event_handler.EventHandler(
        checking_config_modifications, [loggers, app, for_config])
    observer = watchdog.observers.Observer()
    observer.schedule(e, path='./', recursive=False)
    observer.start()


def checking_config_modifications(loggers, app, for_config):
    if cfg.get_show_gui_flag(loggers) == '1':
        show_gui(loggers, app)

    if cfg.get_backup_interval(loggers) != for_config[0]['General']['backup_interval']:
        update_backup_date_labels(loggers, app.main_frame.backup_frame)

    for_config[0] = cfg.get_config(loggers)


def show_gui(loggers, app):
    time.sleep(1)
    app.deiconify()


def checking_for_backup_date(loggers, q_start):
    while True:
        delete_old_backup(loggers)

        today = get_today_date(loggers)
        next_backup_date = compute_next_backup_date(loggers)

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
            update_backup_frame(loggers, main_frame, q_progress)


def making_new_backup(loggers, q):
    try:
        filepaths = get_list_filepaths(
            loggers, cfg.get_path_to_files(loggers), [])

        if len(filepaths) > 0:
            progress_share = 50 / len(filepaths)
            changes = []
            for path in filepaths:
                hashsum = compose_file_hashsum(loggers, path)

                if not os.path.isfile(cfg.get_path_to_backup(loggers) + str(hashsum)):
                    changes.append(path)
                q.put(progress_share, block=False, timeout=None)

            table_name = compose_table_name(loggers)
            db.create_table(loggers, table_name, ['hashsum', 'path'])

            progress_share = 50 / len(filepaths)
            for path in filepaths:
                hashsum = compose_file_hashsum(loggers, path)
                saving_backup_files(loggers, table_name, path, hashsum)
                if path in changes:
                    loggers['info'].info(
                        'File {} was saved as {}'.format(path, hashsum))
                q.put(progress_share, block=False, timeout=None)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def delete_old_backup(loggers):
    try:
        today = get_today_date(loggers)
        backup_obsolescence_date = today - datetime.timedelta(
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

        filepaths = get_list_filepaths(
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


def restoring_backup(loggers, main_frame):
    try:
        q = queue.Queue()

        threading.Thread(target=update_restoring_frame,
                         args=(loggers, main_frame, q,), daemon=True).start()

        backup_date = main_frame.restoring_frame.option.get()
        table_name = datetime.datetime.strptime(
            backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(loggers, int(table_name))

        filepaths = get_list_filepaths(
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


### ### ### ###
#  Tools part #
### ### ### ###


def get_backups_list(loggers):
    tables = db.select_tables(loggers)

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    return backups


def saving_backup_files(loggers, table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(loggers, table_name, file)
    copy_file(loggers, path, hashsum)


def compose_file_hashsum(loggers, path):
    hash = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
                hash.update(chunk)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return hash.hexdigest()


def copy_file(loggers, path, hashsum):
    try:
        backup_path = cfg.get_path_to_backup(loggers) + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def compose_table_name(loggers):
    backup_date = get_today_date(loggers)
    table_name = str(backup_date.timestamp()).split('.')[0]
    return table_name


def get_list_filepaths(loggers, path, filepaths):

    try:
        if os.path.isfile(path):
            filepaths.append(path)
        else:
            for name in os.listdir(path):
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    filepaths.append(filepath)
                else:
                    filepaths = get_list_filepaths(
                        loggers, filepath, filepaths)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return filepaths


def get_today_date(loggers):
    today_date = datetime.datetime(1970, 1, 1)

    try:
        tz = pytz.timezone(cfg.get_timezone(loggers))
        if tz == '':
            tz = pytz.timezone('UTC')
        today_date = datetime.datetime.now(tz=tz)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return today_date


def compose_backups_dates(loggers):
    backup_dates = {}

    try:
        backup_dates['oldest_backup_date'] = compute_oldest_backup_date(
            loggers)

        backup_dates['latest_backup_date'] = compute_latest_backup_date(
            loggers)

        backup_dates['next_backup_date'] = compute_next_backup_date(
            loggers, backup_dates['latest_backup_date'])

    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return backup_dates


def compute_oldest_backup_date(loggers):
    oldest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables(loggers)

        oldest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                oldest = float(table_name)
                continue

            if float(table_name) < oldest:
                oldest = float(table_name)

        oldest_backup_date = datetime.datetime.fromtimestamp(
            float(oldest))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return oldest_backup_date


def compute_latest_backup_date(loggers):
    latest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables(loggers)

        latest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                latest = float(table_name)

            if latest < float(table_name):
                latest = float(table_name)

        latest_backup_date = datetime.datetime.fromtimestamp(
            float(latest))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return latest_backup_date


def compute_next_backup_date(loggers, latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
        else:
            tables = db.select_tables(loggers)

            latest_backup_date = compute_latest_backup_date(
                loggers)

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval(loggers)))
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()

    return next_backup_date


### ### ### ### ###
#   Painter part  #
### ### ### ### ###


def make_main_window(loggers, q_start):
    buttons_params = {
        'backup': {
            'func': start_backuping,
            'args': [loggers, q_start]
        },
        'restoring': {
            'restore': {
                'func': restoring_backup,
                'args': [loggers]
            },
            'copy': {
                'func': copying_backuped_file,
                'args': [loggers]
            }
        },
        'settings': {
            'path_to_backup': {
                'func': select_path_to_backup,
                'args': [loggers]
            },
            'path_to_files': {
                'func': select_path_to_files,
                'args': [loggers]
            },
            'path_to_db': {
                'func': select_path_to_db,
                'args': [loggers]
            },
            'hide_startup': {
                'func': switch_hide_startup,
                'args': [loggers, cfg.get_hide_startup_flag(loggers)]
            },
            'hide_gui': {
                'func': hide_gui,
                'args': [loggers]
            },
            'save': {
                'func': update_configs,
                'args': [loggers]
            }
        }
    }

    backups = get_backups_list(loggers)
    configs = cfg.get_config(loggers)

    app = gui.Window(loggers, buttons_params, backups, configs)

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

    backups = get_backups_list(loggers)

    main_frame.restoring_frame.update_backup_dates(backups)
    main_frame.backup_frame.hide_progress_bar_show_buttons()


def update_backup_date_labels(loggers, backup_frame):
    backup_dates = compose_backups_dates(loggers)
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
    path = gui.open_dir_dialog('Выберите папку для хранения резервных копий')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_backup.set(path)


def select_path_to_files(loggers, settings_frame):
    path = gui.open_dir_dialog('Выберите папку для создания резервной копии')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_files.set(path)


def select_path_to_db(loggers, settings_frame):
    path = gui.open_filedialog()
    path = os.path.abspath(path)

    if path != '':
        settings_frame.path_to_db.set(path)


### ### ### ### ###
# Button handlers #
### ### ### ### ###


def start_backuping(loggers, q_start):
    q_start.put('go', block=False, timeout=None)


def update_configs(loggers, settings_frame):
    try:
        config = cfg.get_config(loggers)
        config['General']['path_to_backup'] = settings_frame.path_to_backup.get()
        config['General']['path_to_files'] = settings_frame.path_to_files.get()
        config['General']['backup_interval'] = settings_frame.backup_interval.get()
        config['General']['timezone'] = settings_frame.timezone.get()
        config['DataBase']['path_to_db'] = settings_frame.path_to_db.get()
        config['DataBase']['file_retention_period'] = settings_frame.file_retention_period.get()

        cfg.write_config(loggers, config)
    except Exception:
        loggers['critical'].exception('Program is terminated')
        sys.exit()


def copying_backuped_file(loggers, restoring_frame):
    backup_date = restoring_frame.option.get()
    table_name = datetime.datetime.strptime(
        backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

    backup_files = db.select_files(loggers, int(table_name))

    selected_item = restoring_frame.files_table.focus()
    filepath = restoring_frame.files_table.item(selected_item)['values'][0]

    backuped_file_path = ''

    for item in backup_files:
        if item.path == filepath:
            backuped_file_path = '{}{}'.format(
                cfg.get_path_to_backup(loggers), item.hashsum)

    filename = os.path.basename(filepath)

    dest_dir = gui.open_dir_dialog('Выберите папку для сохранения файла')

    shutil.copyfile(backuped_file_path, os.path.join(dest_dir, filename))


def switch_hide_startup(loggers, hide_startup_flag):
    config = cfg.get_config(loggers)
    if config['GUI']['hide_startup'] == '0':
        config['GUI']['hide_startup'] = '1'
        hide_startup_flag = '1'
    elif config['GUI']['hide_startup'] == '1':
        config['GUI']['hide_startup'] = '0'
        hide_startup_flag = '0'

    cfg.write_config(loggers, config)


def hide_gui(loggers, app):
    config = cfg.get_config(loggers)
    config['GUI']['show_gui'] = '0'
    cfg.write_config(loggers, config)

    app.withdraw()
