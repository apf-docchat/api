import logging

from source.qa_tool.lib.chats_helper import get_chat_history_by_user_id


def get_all_threads_for_user(user_id=None, start_date=None, end_date=None):
    try:
        threads = get_chat_history_by_user_id(user_id, start_date, end_date) or {}
        for thread in threads:
            thread.pop('_id')
            # thread.pop('user_id')
            thread.pop('organization_id')
            thread_created_datetime = thread.get('thread_created_datetime')
            if thread_created_datetime:
                thread_created_datetime = thread_created_datetime.replace(microsecond=0)
                thread['thread_created_datetime'] = thread_created_datetime.isoformat()
            for message in thread.get('messages'):
                chat_created_datetime = message.get('chat_created_datetime')
                if chat_created_datetime:
                    chat_created_datetime = chat_created_datetime.replace(microsecond=0)
                    message['chat_created_datetime'] = chat_created_datetime.isoformat()
        return threads
    except Exception as e:
        logging.error(e)
        raise e
