import os


class Config:
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')

    SQLALCHEMY_DATABASE_URI = os.getenv('DATABASE_URI')
