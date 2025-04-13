import os

from source.common import config


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

    SESSION_COOKIE_SAMESITE = None
    SESSION_COOKIE_SECURE = True

    SQLALCHEMY_DATABASE_URI = config.DATABASE_URI
