# coding: utf-8

import tkinter as tk


class MainWindow(tk.Tk):
    def __init__(self):
        super().__init__()

        window_width = 500
        window_height = 150

        screen_width = self.winfo_screenwidth()
        screen_height = self.winfo_screenheight()

        pos_x = (screen_width // 2) - (window_width // 2)
        pos_y = (screen_height // 2) - (window_height // 2)

        self.geometry('{}x{}+{}+{}'.format(window_width,
                                           window_height, pos_x, pos_y))
        self.minsize(window_width, window_height)
        self.maxsize(window_width, window_height)
