import logging
import os

from flask import Flask
from flask.logging import default_handler


def setup_app_logger(app: Flask):
    app_log_level = getattr(logging, os.getenv('APP_LOG_LEVEL', 'INFO').upper())

    app_logger = logging.getLogger('app')
    app_logger.setLevel(app_log_level)
    app_logger.addHandler(default_handler)

    app.logger.setLevel(app_logger.getEffectiveLevel())
