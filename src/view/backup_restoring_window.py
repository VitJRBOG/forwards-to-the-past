# coding: utf-8

import tkinter as tk
import threading


class Window(tk.Toplevel):
    def __init__(self, master, backups_dates, params_for_btn):
        super().__init__(master)
        window_width = 300
        window_height = 150

        # screen_width = self.winfo_screenwidth()
        # screen_height = self.winfo_screenheight()

        # pos_x = (screen_width // 2) - (window_width // 2)
        # pos_y = (screen_height // 2) - (window_height // 2)

        # self.geometry('{}x{}+{}+{}'.format(window_width,
        #                                    window_height, pos_x, pos_y))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)

        self.title('Восстановление резервной копии')

        Frame(self, backups_dates, params_for_btn)


class Frame(tk.Frame):
    def __init__(self, master, backups_dates, params_for_btn):
        super().__init__(master)

        selected_backup = make_dropdown_list(
            self, backups_dates, coordinates=(0, 0))

        params_for_btn['args'][1] = selected_backup
        make_button(self, params_for_btn['func'],
                    params_for_btn['args'], coordinates=(0, 1))

        self.pack()


def make_dropdown_list(master, options, coordinates):
    option = tk.StringVar(master)
    option.set(options[len(options)-1])

    dropdown_list = tk.OptionMenu(master, option, *options)
    dropdown_list.grid(column=coordinates[0], row=coordinates[1])

    return option


def make_button(master, func, func_args, coordinates):
    button = tk.Button(master, text='Восстановить',
                       command=lambda: threading.Thread(target=func,
                                                        args=(func_args),
                                                        daemon=True).start())
    button.grid(column=coordinates[0], row=coordinates[1])
