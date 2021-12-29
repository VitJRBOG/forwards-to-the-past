# coding: utf-8

import tkinter as tk
import datetime
import threading


class Window(tk.Tk):
    def __init__(self):
        super().__init__()

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

        oldest_backup_date_label = Label(self, coordinates=(0, 30))
        latest_backup_date_label = Label(self, coordinates=(0, 50))
        next_backup_date_label = Label(self, coordinates=(0, 70))

        self.oldest_backup_date = oldest_backup_date_label.text_variable
        self.latest_backup_date = latest_backup_date_label.text_variable
        self.next_backup_date = next_backup_date_label.text_variable

        Button(self, 'Запустить сейчас',
               params_for_btn['start']['func'],
               params_for_btn['start']['args'], (150, 100))
        Button(self, 'Восстановить резервную копию',
               params_for_btn['restore']['func'],
               params_for_btn['restore']['args'], (100, 130))

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


class Label(tk.Label):
    def __init__(self, master, coordinates):
        self.text_variable = tk.StringVar()

        label = tk.Label(master, textvariable=self.text_variable)
        label.place(x=coordinates[0], y=coordinates[1])


class Button(tk.Button):
    def __init__(self, master, text, func, func_args, coordinates):
        func_args.append(master)
        button = tk.Button(master, text=text,
                           command=lambda: threading.Thread(target=func,
                                                            args=(func_args),
                                                            daemon=True).start())
        button.place(x=coordinates[0], y=coordinates[1])
