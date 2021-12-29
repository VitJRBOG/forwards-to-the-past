# coding: utf-8

import tkinter as tk
import datetime
import threading


class GeneralFrame(tk.Canvas):
    def __init__(self, master, params_for_btn):
        super().__init__(master)

        self.oldest_backup_date = make_label(self, coordinates=(0, 30))
        self.latest_backup_date = make_label(self, coordinates=(0, 50))
        self.next_backup_date = make_label(self, coordinates=(0, 70))

        make_button(self, 'Запустить сейчас',
                    params_for_btn['start']['func'],
                    params_for_btn['start']['args'], (150, 100))
        make_button(self, 'Восстановить резервную копию',
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


def make_label(master, coordinates):
    text_variable = tk.StringVar()

    label = tk.Label(master, textvariable=text_variable)
    label.place(x=coordinates[0], y=coordinates[1])

    return text_variable


def make_button(master, text, func, func_args, coordinates):
    func_args.append(master)
    button = tk.Button(master, text=text,
                       command=lambda: threading.Thread(target=func,
                                                        args=(func_args),
                                                        daemon=True).start())
    button.place(x=coordinates[0], y=coordinates[1])
