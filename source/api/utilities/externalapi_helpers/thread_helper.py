import logging

from flask import request

from source.api.utilities.externalapi_helpers import chats_helper

logger = logging.getLogger('app')


def get_threads_for_user_by_module_and_type():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        user_id = request.context.get("user_id")
        module = request.args.get('module')
        module_type = request.args.get('type')
        threads = chats_helper.get_chat_history_by_user_id_and_module_and_type(user_id, module, module_type) or {}
        for thread in threads:
            thread.pop('_id')
            thread.pop('user_id')
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
        logger.error(e)
        raise e


def get_thread_for_user_by_thread_id(thread_id=None):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        user_id = request.context.get("user_id")
        thread = chats_helper.get_chat_history_by_thread_id_and_user_id(thread_id, user_id) or {}
        thread.pop('_id')
        thread.pop('user_id')
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
        return thread
    except Exception as e:
        logger.error(e)
        raise e

def get_all_threads_for_user(user_id=None, start_date=None, end_date=None):
    try:
        threads = chats_helper.get_chat_history_by_user_id(user_id, start_date, end_date) or {}
        for thread in threads:
            thread.pop('_id')
            #thread.pop('user_id')
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
        logger.error(e)
        raise e