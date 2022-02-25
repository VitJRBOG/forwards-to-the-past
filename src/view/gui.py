# coding: utf-8

import tkinter as tk
from tkinter.constants import HORIZONTAL
import tkinter.ttk as ttk
import tkinter.filedialog as filedialog
import threading
import datetime
import shutil
import os

import src.model.db as db


class Window(tk.Tk):
    def __init__(self, loggers, buttons_params, backup_dates, configs):
        super().__init__()
        self.title('Forwards to the Past')

        window_width = 500
        window_height = 270

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)

        self.geometry('{}x{}+{}+{}'.format(window_width,
                                           window_height, pos_x, pos_y))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)

        self.main_frame = MainFrame(
            self, loggers, buttons_params, backup_dates, configs, (0, 20))
        MenuFrame(self, self.main_frame, (0, 0))


class MenuFrame(tk.Canvas):
    def __init__(self, master, main_frame, position):
        super().__init__(master, width=500, height=40)

        Button(self, 'Резервное копирование',
               main_frame.show_backup_frame, [], (75, 10))
        Button(self, 'Восстановление копии',
               main_frame.show_restoring_frame, [], (220, 10))
        Button(self, 'Настройки',
               main_frame.show_settings_frame, [], (360, 10))

        self.place(x=position[0], y=position[1])


class MainFrame(tk.Canvas):
    def __init__(self, master, loggers, buttons_params, backup_dates, configs, position):
        super().__init__(master, width=500, height=270)

        self.backup_frame_pos = (150, 0)
        self.restoring_frame_pos = (45, 0)
        self.settings_frame_pos = (45, 0)

        self.backup_frame = BackupFrame(
            self, buttons_params['backup'], self.backup_frame_pos)
        self.restoring_frame = RestoringFrame(
            self, loggers, buttons_params['restoring'],
            backup_dates, self.backup_frame_pos)
        self.restoring_frame.place_forget()
        self.settings_frame = SettingsFrame(
            self, buttons_params['settings'], configs, self.backup_frame_pos)
        self.settings_frame.place_forget()

        self.place(x=position[0], y=position[1])

    def show_backup_frame(self):
        self.restoring_frame.place_forget()
        self.settings_frame.place_forget()
        self.backup_frame.place(
            x=self.backup_frame_pos[0], y=self.backup_frame_pos[1])

    def show_restoring_frame(self):
        self.settings_frame.place_forget()
        self.backup_frame.place_forget()
        self.restoring_frame.place(
            x=self.restoring_frame_pos[0], y=self.restoring_frame_pos[1])

    def show_settings_frame(self):
        self.backup_frame.place_forget()
        self.restoring_frame.place_forget()
        self.settings_frame.place(
            x=self.settings_frame_pos[0], y=self.settings_frame_pos[1])


class BackupFrame(tk.Canvas):
    def __init__(self, master, button_params, position):
        super().__init__(master)

        oldest_backup_label = Label(self, '', (0, 60))
        latest_backup_label = Label(self, '', (0, 90))
        next_backup_label = Label(self, '', (0, 120))

        self.oldest_backup = oldest_backup_label.text_var
        self.latest_backup = latest_backup_label.text_var
        self.next_backup = next_backup_label.text_var

        self.backup_button = Button(
            self, 'Запустить сейчас',
            button_params['func'],
            button_params['args'], (0, 155))

        self.progress_bar = ProgressBar(self, (0, 155))
        self.progress_bar.place_forget()

        self.place(x=position[0], y=position[1])

    def set_oldest_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'копий не найдено'
        self.oldest_backup.set('Старейшая копия: {}'.format(text))

    def set_latest_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'копий не найдено'
        self.latest_backup.set('Последняя копия: {}'.format(text))

    def set_next_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'автокопирование отключено'
        self.next_backup.set('Следующее копирование: {}'.format(text))

    def hide_progress_bar_show_buttons(self):
        self.progress_bar.place_forget()
        self.backup_button.place(x=0, y=155)

    def hide_buttons_show_progressbar(self):
        self.backup_button.place_forget()
        self.progress_bar.place(x=0, y=155)

    def update_progress_bar(self, progress):
        if progress == 0 or progress == 100:
            self.progress_bar['value'] = progress
        else:
            self.progress_bar['value'] += progress


class RestoringFrame(tk.Canvas):
    def __init__(self, master, loggers, button_params, backup_dates, position):
        self.loggers = loggers

        super().__init__(master, width=420, height=235)

        self.option_menu = OptionMenu(
            self, self.update_files_table, backup_dates, (0, 30))
        self.option = self.option_menu.option

        self.restoring_button = Button(self, 'Восстановить',
                                       button_params['func'],
                                       button_params['args'],
                                       (150, 32))

        self.progress_bar = ProgressBar(self, (150, 30))
        self.progress_bar.place_forget()

        self.files_table = Table(self,
                                 [[375], ['Полный путь']],
                                 (5, 70))

        self.place(x=position[0], y=position[1])

    def update_backup_dates(self, backup_dates, *args):
        self.option_menu.destroy()
        self.option_menu = OptionMenu(
            self, self.update_files_table, backup_dates, (0, 30))
        self.option = self.option_menu.option

    def update_files_table(self, event):
        self.files_table.delete(*self.files_table.get_children())

        table_name = datetime.datetime.strptime(
            self.option.get(), '%d.%m.%Y %H:%M:%S').timestamp()

        backup_files = db.select_files(self.loggers, int(table_name))

        data = []

        for item in backup_files:
            data.append([item.path])

        self.files_table.insert_data(data)

    def hide_progress_bar_show_button(self):
        self.progress_bar.place_forget()
        self.restoring_button.place(x=150, y=32)

    def hide_button_show_progressbar(self):
        self.restoring_button.place_forget()
        self.progress_bar.place(x=150, y=35)

    def update_progress_bar(self, progress):
        if progress == 0 or progress == 100:
            self.progress_bar['value'] = progress
        else:
            self.progress_bar['value'] += progress


class SettingsFrame(tk.Canvas):
    def __init__(self, master, buttons_params, configs, position):
        super().__init__(master, width=410, height=250)

        first_y = 30
        interval = 25

        Label(self, 'Путь к резервным копиям', (0, first_y))
        path_to_backup_entry = Entry(
            self, configs['General']['path_to_backup'],
            (200, first_y), 25)
        self.path_to_backup = path_to_backup_entry.text_var
        Button(self, 'Указать', buttons_params['path_to_backup']['func'],
               buttons_params['path_to_backup']['args'], (360, first_y - 2))

        Label(self, 'Путь к файлам', (0, first_y + interval))
        path_to_files_entry = Entry(
            self, configs['General']['path_to_files'],
            (200, first_y + interval), 25)
        self.path_to_files = path_to_files_entry.text_var
        Button(self, 'Указать', buttons_params['path_to_files']['func'],
               buttons_params['path_to_files']['args'],
               (360, first_y - 2 + interval))

        Label(self, 'Интервал резервного копирования',
              (0, first_y + (interval * 2)))
        backup_interval_entry = Entry(
            self, configs['General']['backup_interval'],
            (200, first_y + (interval * 2)), 7)
        self.backup_interval = backup_interval_entry.text_var
        Label(self, 'дней', (230, first_y + (interval * 2)))

        Label(self, 'Часовой пояс', (0, first_y + (interval * 3)))
        timezone_entry = Entry(
            self, configs['General']['timezone'],
            (200, first_y + (interval * 3)), 25)
        self.timezone = timezone_entry.text_var

        Label(self, 'Путь к базе данных', (0, first_y + (interval * 4)))
        path_to_db_entry = Entry(
            self, configs['DataBase']['path_to_db'],
            (200, first_y + (interval * 4)), 25)
        self.path_to_db = path_to_db_entry.text_var
        Button(self, 'Указать', buttons_params['path_to_db']['func'],
               buttons_params['path_to_db']['args'],
               (360, first_y - 2 + (interval * 4)))

        Label(self, 'Срок хранения резервных копий',
              (0, first_y + (interval * 5)))
        file_retention_period_entry = Entry(
            self, configs['DataBase']['file_retention_period'],
            (200, first_y + (interval * 5)), 7)
        self.file_retention_period = file_retention_period_entry.text_var
        Label(self, 'дней', (230, first_y + (interval * 5)))

        Button(self, 'Скрыть графический интерфейс',
               buttons_params['hide_gui']['func'],
               buttons_params['hide_gui']['args'],
               (0, first_y + (interval * 6)))

        Button(self, 'Сохранить', buttons_params['save']['func'],
               buttons_params['save']['args'], (0, 215))

        self.place(x=position[0], y=position[1])


class ProgressBar(ttk.Progressbar):
    def __init__(self, master, position):
        super().__init__(master, orient=HORIZONTAL, length=215, mode='determinate')
        self.place(x=position[0], y=position[1])


class Table(ttk.Treeview):
    def __init__(self, master, column_params, position):
        frame = tk.Frame(master)

        super().__init__(frame, height=7)

        self['columns'] = column_params[1]
        self['show'] = 'headings'
        for i, _ in enumerate(column_params[0]):
            self.heading(column_params[1][i], text=column_params[1][i])
            self.column(column_params[1][i], width=column_params[0][i])

        self.pack(side='left')

        treescroll = tk.Scrollbar(frame, orient='vertical', command=self.yview)
        self.configure(yscrollcommand=treescroll.set)

        treescroll.pack(side='right', fill='y')

        frame.place(x=position[0], y=position[1])

        self.bind('<Button-3>', self.show_menu)

    def insert_data(self, data):
        for row in data:
            self.insert('', 'end', values=row)

    def show_menu(self, event):
        menu = Menu(
            self, [{'name': 'Копировать в...', 'func': self.copy_file}])
        try:
            menu.tk_popup(event.x_root, event.y_root)
        finally:
            menu.grab_release()

    def copy_file(self):
        selected_item = self.focus()
        filepath = self.item(selected_item)['values'][0]

        filename = os.path.basename(filepath)

        dest_dir = open_dir_dialog()

        shutil.copyfile(filepath, os.path.join(dest_dir, filename))


class Button(tk.Button):
    def __init__(self, master, text, command, command_params, position):
        super().__init__(master, text=text, command=lambda: threading.Thread(
            target=command, args=(command_params), daemon=True).start())
        self.place(x=position[0], y=position[1])


class OptionMenu(tk.OptionMenu):
    def __init__(self, master, command, options, coordinates):
        self.option = tk.StringVar(master)
        if len(options) > 0:
            self.option.set(options[len(options)-1])
        else:
            self.option.set('')
            options.append('')

        super().__init__(master, self.option, *options, command=command)
        self.place(x=coordinates[0], y=coordinates[1])


class Menu(tk.Menu):
    def __init__(self, master, options):
        super().__init__(master, tearoff=0)
        for item in options:
            self.add_command(label=item['name'], command=item['func'])


class Label(tk.Label):
    def __init__(self, master, text, position):
        self.text_var = tk.StringVar()
        self.text_var.set(text)
        super().__init__(master, textvariable=self.text_var)

        self.place(x=position[0], y=position[1])


class Entry(tk.Entry):
    def __init__(self, master, text, position, width):
        self.text_var = tk.StringVar()
        self.text_var.set(text)
        super().__init__(master, textvariable=self.text_var, width=width)

        self.place(x=position[0], y=position[1])


def open_filedialog():
    path = filedialog.askopenfilename()

    return path


def open_dir_dialog():
    path = filedialog.askdirectory()

    return path
