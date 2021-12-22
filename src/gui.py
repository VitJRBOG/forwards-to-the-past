# coding: utf-8

import tkinter
import tkinter.ttk
import queue
import threading

import core


def show_gui(loggers):
    global gui
    gui = GUI(loggers)

    gui.app.mainloop()


class GUI:
    app = tkinter.Tk()
    frame = tkinter.Frame()
    backup_start_btn = tkinter.Button()
    progress_bar = tkinter.ttk.Progressbar()

    def __init__(self, loggers):
        self.__make_main_window()
        self.__make_general_menu(loggers)
        self.frame.pack()

    def __make_main_window(self):
        self.app.title('Forwards to the Past')
        self.app.minsize(200, 100)
        self.frame = tkinter.Frame(self.app)

    def __make_general_menu(self, loggers):
        self.backup_start_btn = tkinter.Button(
            self.frame, text='Запустить резервное копирование',
            command=lambda: start_backup(loggers))

        self.progress_bar = tkinter.ttk.Progressbar(
            self.frame,
            orient='horizontal',
            mode='determinate',
            length=100
        )

        self.backup_start_btn.pack()
        self.progress_bar.pack()

    def update_progress_bar(self, q):
        self.progress_bar['value'] = 0
        while True:
            progress = q.get(block=True, timeout=None)
            if progress == 100:
                self.progress_bar['value'] = 100
                break
            else:
                self.progress_bar['value'] += progress


def start_backup(loggers):
    global gui
    q = queue.Queue()
    thread = threading.Thread(
        target=core.files_processing, args=(loggers, q,), daemon=True)
    thread.start()

    thread_two = threading.Thread(
        target=gui.update_progress_bar, args=(q,), daemon=True
    )
    thread_two.start()
