# coding: utf-8

import tkinter as tk
import tkinter.ttk as ttk
from tkinter.constants import HORIZONTAL
import datetime
import threading


class Window(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Forwards to the Past')

        window_width = 500
        window_height = 190

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)

        self.geometry('{}x{}+{}+{}'.format(window_width,
                                           window_height, pos_x, pos_y))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)


class GeneralFrame(tk.Canvas):
    def __init__(self, master, params_for_btn):
        super().__init__(master)

        labels_frame = LabelsFrame(self, (0, 0))
        self.oldest_backup_date = labels_frame.oldest_backup_date
        self.latest_backup_date = labels_frame.latest_backup_date
        self.next_backup_date = labels_frame.next_backup_date

        self.progress_bar_frame = ProgressbarFrame(self, coordinates=(0, 100))
        self.progress_bar = self.progress_bar_frame.progress_bar
        self.progress_bar_frame.place_forget()

        self.buttons_frame = ButtonsFrame(self, params_for_btn, (0, 100))

        self.pack()

    def set_oldest_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'копий не найдено'
        self.oldest_backup_date.set('Старейшая копия: {}'.format(text))

    def set_latest_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'копий не найдено'
        self.latest_backup_date.set('Последняя копия: {}'.format(text))

    def set_next_backup_date(self, date=datetime.datetime(1970, 1, 1)):
        text = ''
        if date > datetime.datetime(1971, 1, 1):
            text = date.strftime('%d.%m.%Y %H:%M')
        else:
            text = 'автоматическое копирование отключено'
        self.next_backup_date.set('Следующее копирование: {}'.format(text))

    def hide_progress_bar_show_buttons(self):
        self.progress_bar_frame.place_forget()
        self.buttons_frame.place(x=0, y=100)

    def hide_buttons_show_progressbar(self):
        self.buttons_frame.place_forget()
        self.progress_bar_frame.place(x=0, y=100)

    def update_progress_bar(self, progress):
        if progress == 0 or progress == 100:
            self.progress_bar['value'] = progress
        else:
            self.progress_bar['value'] += progress


class LabelsFrame(tk.Canvas):
    def __init__(self, master, coordinates):
        super().__init__(master)

        oldest_backup_date_label = Label(self, coordinates=(0, 30))
        latest_backup_date_label = Label(self, coordinates=(0, 50))
        next_backup_date_label = Label(self, coordinates=(0, 70))

        self.oldest_backup_date = oldest_backup_date_label.text_variable
        self.latest_backup_date = latest_backup_date_label.text_variable
        self.next_backup_date = next_backup_date_label.text_variable

        self.place(x=coordinates[0], y=coordinates[1])


class Label(tk.Label):
    def __init__(self, master, coordinates):
        self.text_variable = tk.StringVar()
        super().__init__(master, textvariable=self.text_variable)

        self.place(x=coordinates[0], y=coordinates[1])


class ButtonsFrame(tk.Canvas):
    def __init__(self, master, params_for_btn, coordinates):
        super().__init__(master)

        Button(self, master, 'Запустить сейчас',
               params_for_btn['start']['func'],
               params_for_btn['start']['args'], (150, 0))
        Button(self, master, 'Восстановить резервную копию',
               params_for_btn['restore']['func'],
               params_for_btn['restore']['args'], (100, 30))

        self.place(x=coordinates[0], y=coordinates[1])


class Button(tk.Button):
    def __init__(self, master, g_frame, text, func, func_args, coordinates):
        func_args.append(g_frame)
        super().__init__(master, text=text,
                         command=lambda: threading.Thread(target=func,
                                                          args=(func_args),
                                                          daemon=True).start())
        self.place(x=coordinates[0], y=coordinates[1])


class ProgressbarFrame(tk.Canvas):
    def __init__(self, master, coordinates):
        super().__init__(master)

        self.progress_bar = ttk.Progressbar(
            self, orient=HORIZONTAL, length=350, mode='determinate')
        self.progress_bar.place(x=20, y=0)

        self.place(x=coordinates[0], y=coordinates[1])
