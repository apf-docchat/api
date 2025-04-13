import os
from urllib.parse import urlparse

import pymysql


def get_connection():
    try:
        # Parse the URI
        parsed_uri = urlparse(os.getenv('DATABASE_URI'))
        return pymysql.connect(host=parsed_uri.hostname,
                               user=parsed_uri.username,
                               password=parsed_uri.password,
                               database=parsed_uri.path.lstrip('/'),
                               port=parsed_uri.port)
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
