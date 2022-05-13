import logging
import os


class Logger(logging.Logger):
    def __init__(self, logger_name: str):
        super().__init__(logger_name)

        if logger_name == 'critical':
            self.__add_critical_logger_params()
        elif logger_name == 'warning':
            self.__add_warning_logger_params()
        else:
            self.__add_info_logger_params()

    def __add_critical_logger_params(self):
        self.setLevel(logging.CRITICAL)
        msg_format = '%(asctime)s - [%(levelname)s] - ' + \
            '(%(filename)s).%(funcName)s(%(lineno)d) - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
        self.__add_filehandler(msg_format)

    def __add_warning_logger_params(self):
        self.setLevel(logging.WARNING)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
        self.__add_filehandler(msg_format)

    def __add_info_logger_params(self):
        self.setLevel(logging.INFO)
        msg_format = '%(asctime)s - [%(levelname)s] - PID: ' + \
            '{} - %(message)s'.format(os.getpid())
        self.__add_filehandler(msg_format)

    def __add_filehandler(self, msg_format: str):
        file_handler = logging.FileHandler('log.log')
        file_handler.setFormatter(logging.Formatter(msg_format))
        self.addHandler(file_handler)