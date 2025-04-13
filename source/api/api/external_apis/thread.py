from flask import Blueprint, jsonify, make_response, Response, request
from source.api.utilities.externalapi_helpers import auth_helper, docguide_helper, chats_helper, thread_helper

chat_threads = Blueprint('chat_threads', __name__)


@chat_threads.route('/', methods=['GET'])
@auth_helper.token_required
def get_chat_threads():
    try:
        threads = thread_helper.get_threads_for_user_by_module_and_type()
        return make_response(jsonify({'data': threads, 'message': 'Threads fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@chat_threads.route('/<thread_id>', methods=['GET'])
@auth_helper.token_required
def get_chat_thread(thread_id):
    try:
        thread = thread_helper.get_thread_for_user_by_thread_id(thread_id)
        return make_response(jsonify({'data': thread, 'message': 'Thread fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
