# coding: utf-8

import tkinter as tk
import threading


class Window(tk.Toplevel):
    def __init__(self, master, backups_dates, params_for_btn):
        super().__init__(master)
        self.title('Восстановление резервной копии')

        window_width = 400
        window_height = 150

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)

        self.geometry('{}x{}+{}+{}'.format(window_width,
                                           window_height, pos_x, pos_y))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)

        Frame(self, backups_dates, params_for_btn)


class Frame(tk.Canvas):
    def __init__(self, master, backups_dates, params_for_btn):
        super().__init__(master)

        option_menu = OptionMenu(self, backups_dates, coordinates=(130, 10))
        selected_backup = option_menu.option

        params_for_btn['args'][1] = selected_backup
        Button(self, 'Восстановить', params_for_btn['func'],
               params_for_btn['args'], coordinates=(157, 45))

        self.pack()


class OptionMenu(tk.OptionMenu):
    def __init__(self, master, options, coordinates):
        self.option = tk.StringVar(master)
        self.option.set(options[len(options)-1])

        super().__init__(master, self.option, *options)
        self.place(x=coordinates[0], y=coordinates[1])


class Button(tk.Button):
    def __init__(self, master, text, func, func_args, coordinates):
        super().__init__(master, text=text,
                         command=lambda: threading.Thread(target=func,
                                                          args=(func_args),
                                                          daemon=True).start())
        self.place(x=coordinates[0], y=coordinates[1])
