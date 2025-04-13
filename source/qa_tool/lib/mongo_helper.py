import os

from pymongo import MongoClient


def get_mongodb():
    mongo_client = MongoClient(os.getenv('MONGO_URI'))

    try:
        return mongo_client.get_database(os.getenv('MONGO_DATABASE'))
    except Exception as e:
        print(e)
        raise e
