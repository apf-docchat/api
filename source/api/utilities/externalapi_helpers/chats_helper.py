from datetime import datetime
from uuid import uuid4
import bson
from source.api.utilities import db_helper
from datetime import datetime, timedelta


def create_thread(payload=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if payload is None:
            payload = {}
        thread_id = str(uuid4())
        document = dict(thread_id=thread_id, thread_created_datetime=datetime.now(), messages=[])
        document.update(payload)
        inserted_result = chat_history_collection.insert_one(document)
        if inserted_result.acknowledged:
            inserted_thread = chat_history_collection.find_one(dict(_id=bson.ObjectId(inserted_result.inserted_id)))
            return inserted_thread
        raise RuntimeError("Thread create failed!")
    except Exception as e:
        print(e)
        raise e


def update_thread(thread_id, payload=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if thread_id is None:
            raise RuntimeError("Thread id is empty!")
        if payload is None:
            payload = {}
        chat_history_collection.update_one(dict(thread_id=thread_id), {'$set': payload})
    except Exception as e:
        print(e)
        raise e


def add_chat_history(thread_id=None, payload=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if payload is None:
            payload = {}
        if thread_id is None:
            raise RuntimeError("Thread id is empty!")
        chat_id = str(uuid4())
        chat = dict(chat_id=chat_id, chat_created_datetime=datetime.now())
        chat.update(payload)
        chat_history_collection.update_one(dict(thread_id=thread_id), {'$push': dict(messages=chat)})
    except Exception as e:
        print(e)
        raise e


def get_chat_history_by_thread_id_and_user_id(thread_id=None, user_id=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if thread_id is None:
            raise RuntimeError("Thread id is empty!")
        if user_id is None:
            raise RuntimeError("User id is empty!")
        chat_history = chat_history_collection.find_one(dict(thread_id=thread_id, user_id=user_id))
        return chat_history
    except Exception as e:
        print(e)
        raise e

def get_chat_history_by_thread_id(thread_id=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if thread_id is None:
            raise RuntimeError("Thread id is empty!")
        chat_history = chat_history_collection.find_one(dict(thread_id=thread_id))
        return chat_history
    except Exception as e:
        print(e)
        raise e

def get_chat_history_by_user_id_and_module_and_type(user_id=None, module=None, chat_type=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if module is None:
            raise RuntimeError("Module id is empty!")
        if user_id is None:
            raise RuntimeError("User Id is empty!")
        if chat_type is None:
            raise RuntimeError("Type is empty!")
        chat_history = list(chat_history_collection.find(dict(user_id=user_id, module=module, type=chat_type)))
        return chat_history
    except Exception as e:
        print(e)
        raise e


def get_threads_by_filter(query_filter=None):
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        if query_filter is None:
            raise RuntimeError("Filter is empty!")
        search_filter = dict()
        search_filter.update(query_filter)
        chat_history = list(chat_history_collection.find(search_filter)
                            # .sort('thread_created_datetime', DESCENDING).limit(1)
                            )
        # chat_history = chat_history[0] if chat_history else None
        return chat_history
    except Exception as e:
        print(e)
        raise e

from datetime import datetime, timedelta
from source.api.utilities import db_helper

def get_chat_history_by_user_id(user_id=None, start_date=None, end_date=None):
    if end_date is None:
        end_date = datetime.now()  # Default to today
    if start_date is None:
        start_date = end_date - timedelta(weeks=1)  # Default to one week back
    try:
        db = db_helper.get_mongodb()
        chat_history_collection = db.get_collection('chat_history')
        query = {
            'thread_created_datetime': {'$gte': start_date, '$lte': end_date}
        }
        if user_id is not None:
            query['user_id'] = user_id
        
        # Filter chat history by user_id (if provided) and date range
        chat_history = list(chat_history_collection.find(query))
        return chat_history
    except Exception as e:
        print(e)
        raise e