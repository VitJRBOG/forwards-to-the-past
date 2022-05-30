import backuper


def update_backup_frame(main_frame, q):
    main_frame.backup_frame.update_progress_bar(0)
    main_frame.backup_frame.hide_buttons_show_progressbar()

    while True:
        progress = q.get(block=True, timeout=None)
        main_frame.backup_frame.update_progress_bar(progress)
        if progress == 100:
            break

    update_backup_date_labels(main_frame.backup_frame)

    backups = backuper.get_backups_list()

    main_frame.restoring_frame.update_backup_dates(backups)
    main_frame.backup_frame.hide_progress_bar_show_buttons()


def update_backup_date_labels(backup_frame):
    backup_dates = backuper.compose_backups_dates()
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