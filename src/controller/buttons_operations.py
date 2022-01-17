# coding: utf-8


def start_backuping(loggers, q_start):
    q_start.put('go', block=False, timeout=None)
