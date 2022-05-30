# coding: utf-8

import os

from src import logging
import core


def __main():
    logging.Logger('info').info('Program was started')

    core.run()


if __name__ == '__main__':
    __main()
