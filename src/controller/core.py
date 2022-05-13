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
import src.model.logging as logging
import src.view.gui as gui
import src.controller.event_handler as event_handler


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
    app = make_main_window(q_start)

    config = cfg.get_config()
    config['GUI']['show_gui'] = '1'
    cfg.write_config(config)

    config_modifications_observing(app, [config])

    initialization()

    if config['GUI']['hide_startup'] == '1':
        hide_gui(app)

    threading.Thread(target=checking_the_backup_frame_update_flag,
                     args=(app.main_frame, q_process,), daemon=True).start()
    threading.Thread(target=checking_the_backup_start_flag, args=(
        q_start, q_process,), daemon=True).start()
    threading.Thread(target=checking_for_backup_date, args=(
        q_start,), daemon=True).start()

    app.mainloop()


def config_modifications_observing(app, for_config):
    e = event_handler.EventHandler(
        checking_config_modifications, [app, for_config])
    observer = watchdog.observers.Observer()
    observer.schedule(e, path='./', recursive=False)
    observer.start()


def checking_config_modifications(app, for_config):
    if cfg.get_show_gui_flag() == '1':
        show_gui(app)

    if cfg.get_backup_interval() != for_config[0]['General']['backup_interval']:
        update_backup_date_labels(app.main_frame.backup_frame)

    for_config[0] = cfg.get_config()


def show_gui(app):
    time.sleep(1)
    app.deiconify()


def checking_for_backup_date(q_start):
    while True:
        delete_old_backup()

        today = get_today_date()
        next_backup_date = compute_next_backup_date()

        if today.timestamp() >= next_backup_date.timestamp():
            q_start.put('go', block=False, timeout=None)

        time.sleep(5)


def checking_the_backup_start_flag(q_start, q_progress):
    while True:
        command = q_start.get(block=True, timeout=None)
        if command == 'go':
            q_progress.put(0, block=False, timeout=None)
            making_new_backup(q_progress)


def checking_the_backup_frame_update_flag(main_frame, q_progress):
    while True:
        progress = q_progress.get(block=True, timeout=None)
        if progress == 0:
            update_backup_frame(main_frame, q_progress)


def making_new_backup(q):
    try:
        filepaths = get_list_filepaths(
            cfg.get_path_to_files(), [])

        if len(filepaths) > 0:
            progress_share = 50 / len(filepaths)
            changes = []
            for path in filepaths:
                hashsum = compose_file_hashsum(path)

                if not os.path.isfile(cfg.get_path_to_backup() + str(hashsum)):
                    changes.append(path)
                q.put(progress_share, block=False, timeout=None)

            table_name = compose_table_name()
            db.create_table(table_name, ['hashsum', 'path'])

            progress_share = 50 / len(filepaths)
            for path in filepaths:
                hashsum = compose_file_hashsum(path)
                saving_backup_files(table_name, path, hashsum)
                if path in changes:
                    logging.Logger('info').info(
                        'File {} was saved as {}'.format(path, hashsum))
                q.put(progress_share, block=False, timeout=None)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def delete_old_backup():
    try:
        today = get_today_date()
        backup_obsolescence_date = today - datetime.timedelta(
            float(cfg.get_file_retention_period()))

        tables = db.select_tables()

        for table_name in tables:
            if backup_obsolescence_date.timestamp() > float(table_name):
                db.drop_table(table_name)
                backup_date = datetime.datetime.fromtimestamp(
                    float(table_name))
                logger_msg = '{} backup is obsolete and was deleted.'.format(
                    backup_date.strftime('%d.%m.%Y %H:%M'))
                logging.Logger('info').info(logger_msg)

        filepaths = get_list_filepaths(cfg.get_path_to_backup(), [])

        tables = db.select_tables()

        for filepath in filepaths:
            file_name = os.path.basename(filepath)
            for i, table_name in enumerate(tables):
                match = db.select_file_by_hashsum(table_name, file_name)
                if len(match) != 0:
                    break

                if i == len(tables) - 1:
                    os.remove(filepath)
                    logging.Logger('info').info(
                        'File {} was deleted.'.format(filepath))

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def restoring_backup(main_frame):
    try:
        q = queue.Queue()

        threading.Thread(target=update_restoring_frame,
                         args=(main_frame, q,), daemon=True).start()

        backup_date = main_frame.restoring_frame.option.get()
        table_name = datetime.datetime.strptime(
            backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(int(table_name))

        filepaths = get_list_filepaths(cfg.get_path_to_files(), [])

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
                cfg.get_path_to_backup(), backup_file.hashsum)
            shutil.copyfile(src_path, backup_file.path)
            q.put(progress_share, block=False, timeout=False)

        progress_share = 100
        q.put(progress_share, block=False, timeout=None)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


### ### ### ###
#  Tools part #
### ### ### ###


def get_backups_list():
    tables = db.select_tables()

    backups = []

    for table_name in tables:
        backup = datetime.datetime.fromtimestamp(float(table_name))
        backups.append(backup.strftime('%d.%m.%Y %H:%M:%S'))

    return backups


def saving_backup_files(table_name, path, hashsum):
    file = db.File(hashsum, path)
    db.insert_into_table(table_name, file)
    copy_file(path, hashsum)


def compose_file_hashsum(path):
    hash = hashlib.md5()
    try:
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(128 * hash.block_size), b''):
                hash.update(chunk)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return hash.hexdigest()


def copy_file(path, hashsum):
    try:
        backup_path = cfg.get_path_to_backup() + hashsum
        shutil.copyfile(path, backup_path)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def compose_table_name():
    backup_date = get_today_date()
    table_name = str(backup_date.timestamp()).split('.')[0]
    return table_name


def get_list_filepaths(path, filepaths):

    try:
        if os.path.isfile(path):
            filepaths.append(path)
        else:
            for name in os.listdir(path):
                filepath = os.path.join(path, name)
                if os.path.isfile(filepath):
                    filepaths.append(filepath)
                else:
                    filepaths = get_list_filepaths(filepath, filepaths)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return filepaths


def get_today_date():
    today_date = datetime.datetime(1970, 1, 1)

    try:
        tz = pytz.timezone(cfg.get_timezone())
        if tz == '':
            tz = pytz.timezone('UTC')
        today_date = datetime.datetime.now(tz=tz)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return today_date


def compose_backups_dates():
    backup_dates = {}

    try:
        backup_dates['oldest_backup_date'] = compute_oldest_backup_date()

        backup_dates['latest_backup_date'] = compute_latest_backup_date()

        backup_dates['next_backup_date'] = compute_next_backup_date(
            backup_dates['latest_backup_date'])

    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return backup_dates


def compute_oldest_backup_date():
    oldest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables()

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
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return oldest_backup_date


def compute_latest_backup_date():
    latest_backup_date = datetime.datetime(1970, 1, 1)

    try:
        tables = db.select_tables()

        latest = 0.0
        for i, table_name in enumerate(tables):
            if i == 0:
                latest = float(table_name)

            if latest < float(table_name):
                latest = float(table_name)

        latest_backup_date = datetime.datetime.fromtimestamp(
            float(latest))
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return latest_backup_date


def compute_next_backup_date(latest_backup_date=None):
    next_backup_date = datetime.datetime(1970, 1, 1)

    try:
        if latest_backup_date != None:
            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
        else:
            tables = db.select_tables()

            latest_backup_date = compute_latest_backup_date()

            next_backup_date = latest_backup_date + datetime.timedelta(
                days=float(cfg.get_backup_interval()))
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()

    return next_backup_date


### ### ### ### ###
#   Painter part  #
### ### ### ### ###


def make_main_window(q_start):
    buttons_params = {
        'backup': {
            'func': start_backuping,
            'args': [q_start]
        },
        'restoring': {
            'restore': {
                'func': restoring_backup,
                'args': []
            },
            'copy': {
                'func': copying_backuped_file,
                'args': []
            }
        },
        'settings': {
            'path_to_backup': {
                'func': select_path_to_backup,
                'args': []
            },
            'path_to_files': {
                'func': select_path_to_files,
                'args': []
            },
            'path_to_db': {
                'func': select_path_to_db,
                'args': []
            },
            'hide_startup': {
                'func': switch_hide_startup,
                'args': [cfg.get_hide_startup_flag()]
            },
            'hide_gui': {
                'func': hide_gui,
                'args': []
            },
            'save': {
                'func': update_configs,
                'args': []
            }
        }
    }

    backups = get_backups_list()
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

    update_backup_date_labels(app.main_frame.backup_frame)

    return app


def update_backup_frame(main_frame, q):
    main_frame.backup_frame.update_progress_bar(0)
    main_frame.backup_frame.hide_buttons_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.backup_frame.update_progress_bar(progress)
        if progress == 100:
            break

    update_backup_date_labels(main_frame.backup_frame)

    backups = get_backups_list()

    main_frame.restoring_frame.update_backup_dates(backups)
    main_frame.backup_frame.hide_progress_bar_show_buttons()


def update_backup_date_labels(backup_frame):
    backup_dates = compose_backups_dates()
    backup_frame.set_oldest_backup_date(backup_dates['oldest_backup_date'])
    backup_frame.set_latest_backup_date(backup_dates['latest_backup_date'])
    backup_frame.set_next_backup_date(backup_dates['next_backup_date'])


def update_restoring_frame(main_frame, q):
    main_frame.restoring_frame.update_progress_bar(0)
    main_frame.restoring_frame.hide_button_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.restoring_frame.update_progress_bar(progress)
        if progress == 100:
            break

    main_frame.restoring_frame.hide_progress_bar_show_button()


def select_path_to_backup(settings_frame):
    path = gui.open_dir_dialog('Выберите папку для хранения резервных копий')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_backup.set(path)


def select_path_to_files(settings_frame):
    path = gui.open_dir_dialog('Выберите папку для создания резервной копии')
    path = os.path.abspath(path)
    path = os.path.join(path, '')

    if path != '':
        settings_frame.path_to_files.set(path)


def select_path_to_db(settings_frame):
    path = gui.open_filedialog()
    path = os.path.abspath(path)

    if path != '':
        settings_frame.path_to_db.set(path)


### ### ### ### ###
# Button handlers #
### ### ### ### ###


def start_backuping(q_start):
    q_start.put('go', block=False, timeout=None)


def update_configs(settings_frame):
    try:
        config = cfg.get_config()
        config['General']['path_to_backup'] = settings_frame.path_to_backup.get()
        config['General']['path_to_files'] = settings_frame.path_to_files.get()
        config['General']['backup_interval'] = settings_frame.backup_interval.get()
        config['General']['timezone'] = settings_frame.timezone.get()
        config['DataBase']['path_to_db'] = settings_frame.path_to_db.get()
        config['DataBase']['file_retention_period'] = settings_frame.file_retention_period.get()

        cfg.write_config(config)
    except Exception:
        logging.Logger('critical').exception('Program is terminated')
        sys.exit()


def copying_backuped_file(restoring_frame):
    backup_date = restoring_frame.option.get()
    table_name = datetime.datetime.strptime(
        backup_date, '%d.%m.%Y %H:%M:%S').timestamp()

    backup_files = db.select_files(int(table_name))

    selected_item = restoring_frame.files_table.focus()
    filepath = restoring_frame.files_table.item(selected_item)['values'][0]

    backuped_file_path = ''

    for item in backup_files:
        if item.path == filepath:
            backuped_file_path = '{}{}'.format(
                cfg.get_path_to_backup(), item.hashsum)

    filename = os.path.basename(filepath)

    dest_dir = gui.open_dir_dialog('Выберите папку для сохранения файла')

    shutil.copyfile(backuped_file_path, os.path.join(dest_dir, filename))


def switch_hide_startup(hide_startup_flag):
    config = cfg.get_config()
    if config['GUI']['hide_startup'] == '0':
        config['GUI']['hide_startup'] = '1'
        hide_startup_flag = '1'
    elif config['GUI']['hide_startup'] == '1':
        config['GUI']['hide_startup'] = '0'
        hide_startup_flag = '0'

    cfg.write_config(config)


def hide_gui(app):
    config = cfg.get_config()
    config['GUI']['show_gui'] = '0'
    cfg.write_config(config)

    app.withdraw()
