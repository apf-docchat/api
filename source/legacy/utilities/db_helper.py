from urllib.parse import urlparse
from source.common import config
import pymysql
from pymongo import MongoClient
import os

mongo_client = MongoClient(config.MONGO_URI)


def get_connection():
    try:
        # Parse the URI
        parsed_uri = urlparse(config.DATABASE_URI)
        return pymysql.connect(host=parsed_uri.hostname,
                               user=parsed_uri.username,
                               password=parsed_uri.password,
                               database=parsed_uri.path.lstrip('/'),
                               port=parsed_uri.port)
    except Exception as e:
        print(e)
        raise e


def get_mongodb():
    try:
        return mongo_client.get_database(os.getenv('MONGO_DATABASE'))
    except Exception as e:
        print(e)
        raise e


def find_one(query, *args):
    try:
        connection = get_connection()
        cursor = connection.cursor(pymysql.cursors.DictCursor)
        cursor.execute(query, args)
        result = cursor.fetchone()
        cursor.close()
        connection.close()

        if result:
            return result
        return None
    except Exception as e:
        print(e)
        raise e


def find_many(query, *args):
    try:
        connection = get_connection()
        cursor = connection.cursor(pymysql.cursors.DictCursor)

        cursor.execute(query, args)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            return result
        return []
    except Exception as e:
        print(e)
        raise e


def execute_many(query, entries):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.executemany(query, entries)
        connection.commit()
        cursor.close()
    except Exception as e:
        print(e)
        raise e
    finally:
        connection.close()


def execute_many_and_get_ids(query, entries):
    connection = get_connection()
    inserted_ids = []
    try:
        cursor = connection.cursor()

        for entry in entries:
            cursor.execute(query, entry)
            inserted_id = cursor.lastrowid
            inserted_ids.append(inserted_id)

        connection.commit()
        cursor.close()
    except Exception as e:
        print(e)
        raise e
    finally:
        connection.close()

    return inserted_ids


def execute(query, *args):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(query, args)
        connection.commit()
        cursor.close()

    except Exception as e:
        print(e)
        raise e
    finally:
        connection.close()


def execute_and_get_id(query, *args):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(query, args)
        connection.commit()
        cursor.close()
        return cursor.lastrowid
    except Exception as e:
        print(e)
        raise e
    finally:
        connection.close()


def execute_and_get_row_count(query, *args):
    connection = get_connection()
    try:
        cursor = connection.cursor()

        cursor.execute(query, args)
        connection.commit()
        cursor.close()
        return cursor.rowcount
    except Exception as e:
        print(e)
        raise e
    finally:
        connection.close()


def execute_many_with_transaction(query, entries):
    connection = get_connection()
    try:
        connection.begin()
        cursor = connection.cursor()
        cursor.executemany(query, entries)
        connection.commit()
        cursor.close()
    except Exception as e:
        print(e)
        connection.rollback()
        raise e
    finally:
        connection.close()


def execute_many_with_transaction_callback(callback):
    connection = get_connection()
    try:
        connection.begin()
        cursor = connection.cursor()
        callback(cursor)
        connection.commit()
        cursor.close()
    except Exception as e:
        print(e)
        connection.rollback()
        raise e
    finally:
        connection.close()
