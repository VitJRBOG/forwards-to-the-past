# coding: utf-8

import os
import logging
import time

import cfg
import core


def __main():
    logging.basicConfig()
    loggers = {
        'info': __create_logger('info'),
        'warning': __create_logger('warning'),
        'critical': __create_logger('critical')
    }
    loggers['info'].info('Program was started')

    __run(loggers)


def __run(loggers):
    while True:
        config = cfg.get_config(loggers)
        core.files_processing(loggers, config)

        time.sleep(float(config['General']['checking_interval']))


def __create_logger(logger_name):
    logger = logging.getLogger(logger_name)

    msg_format = ''

    file_handler = logging.FileHandler('log.log')
    if logger_name == 'critical':
        logger.setLevel(logging.CRITICAL)
        msg_format = '%(asctime)s - [%(levelname)s] - ' + \
            '(%(filename)s).%(funcName)s(%(lineno)d) - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    if logger_name == 'warning':
        logger.setLevel(logging.WARNING)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    else:
        logger.setLevel(logging.INFO)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
    file_handler.setFormatter(logging.Formatter(msg_format))

    logger.addHandler(file_handler)

    return logger


if __name__ == '__main__':
    __main()
