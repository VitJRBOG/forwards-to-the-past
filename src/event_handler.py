# coding: utf-8

import watchdog.events


class EventHandler(watchdog.events.FileSystemEventHandler):
    def __init__(self, command, command_args):
        self.command = command
        self.command_args = command_args

    def on_modified(self, event):
        self.command(*self.command_args)
