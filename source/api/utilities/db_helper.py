from urllib.parse import urlparse
from source.common import config
import pymysql
import psycopg
from psycopg.rows import dict_row
from pymongo import MongoClient
import os
import pandas as pd
from sqlalchemy import create_engine

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

#this function doesnt work
def get_db_connection(db_uri):
    parsed_uri = urlparse(db_uri)
    scheme = parsed_uri.scheme

    if scheme == 'mysql':
        connection =  pymysql.connect(
            host=parsed_uri.hostname,
            port=parsed_uri.port or 3306,
            user=parsed_uri.username,
            password=parsed_uri.password,
            database=parsed_uri.path.lstrip('/')
        )
        cursor = connection.cursor(pymysql.cursors.DictCursor)
    elif scheme in ['postgres', 'postgresql']:
        connection =  psycopg.connect(
            host=parsed_uri.hostname,
            port=parsed_uri.port or 5432,
            user=parsed_uri.username,
            password=parsed_uri.password,
            dbname=parsed_uri.path.split('/')[-2],  # Extract the database name
            row_factory=dict_row
        )
        cursor = connection.cursor(cursor_factory=psycopg.extras.DictCursor)        
    else:
        raise ValueError(f"Unsupported database scheme: {scheme}")
    
    return connection, cursor

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

""" def find_collection_db_many(query, db_uri, *args):
    try:
        connection = get_db_connection(db_uri)
        print("Connection succeeded")

        # Determine the cursor type based on the database type
        if 'postgres' in db_uri:
            cursor = connection.cursor(cursor_factory=psycopg.extras.DictCursor)
        else:
            cursor = connection.cursor(pymysql.cursors.DictCursor)

        cursor.execute(query, args)
        result = cursor.fetchall()
        cursor.close()
        connection.close()

        if result:
            return result
        return []
    except Exception as e:
        print("Connection failed")
        print(e)
        raise e """

def find_collection_db_many(query, db_uri, *args):
    try:
        #cursor = get_db_connection(db_uri)
        parsed_uri = urlparse(db_uri)
        scheme = parsed_uri.scheme
        print(f"Scheme: {scheme}")

        if scheme == 'mysql':
            engine = create_engine(db_uri)
        elif scheme in ['postgres', 'postgresql', 'postgresql+psycopg']:
            db_uri_parts = db_uri.split('/')
            db_uri = '/'.join(db_uri_parts[:-1])
            engine = create_engine(db_uri)

        # Use pandas to execute the query and fetch the results into a DataFrame
        df = pd.read_sql(query, engine, params=args)
        #connection.close()

        if not df.empty:
            return df
        return pd.DataFrame()
    except Exception as e:
        print("Connection failed")
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
