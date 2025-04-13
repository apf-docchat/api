from datetime import datetime, timedelta

from source.qa_tool.lib.mongo_helper import get_mongodb


def get_chat_history_by_user_id(user_id=None, start_date=None, end_date=None):
    if end_date is None:
        end_date = datetime.now()  # Default to today
    if start_date is None:
        start_date = end_date - timedelta(weeks=1)  # Default to one week back
    try:
        db = get_mongodb()
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
