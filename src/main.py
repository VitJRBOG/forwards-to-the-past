# coding: utf-8

import os

import src.model.logging as logging
import controller.core as core


def __main():
    logging.Logger('info').info('Program was started')

    core.run()


if __name__ == '__main__':
    __main()
