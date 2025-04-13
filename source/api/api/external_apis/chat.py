from flask import request, Blueprint, Response, jsonify, make_response

from source.api.utilities.externalapi_helpers import chat_helper, auth_helper


chat = Blueprint('chat', __name__)

@chat.route('/chat', methods=['POST'])
@auth_helper.token_required
def chat_with_chat():
    try:
        query = request.json.get('user_query', 'Hello')
        collection_id = request.json.get('collection_id')
        thread_id = request.json.get('thread_id', None)
        selected_file_ids = request.json.get('selected_file_ids', None)
        chat_response = chat_helper.chat_query(query, collection_id, thread_id, selected_file_ids)
        return Response(chat_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@chat.route('/suggestions', methods=['GET'])
@auth_helper.token_required
def chat_get_suggestions():
    try:
        query = request.args.get('user_query', 'Hello')
        collection_id = request.args.get('collection_id')
        thread_id = request.args.get('thread_id', None)
        selected_file_ids = request.args.get('selected_file_ids', None)
        # Convert selected_file_ids to a list of integers
        if selected_file_ids:
            selected_file_ids = [int(file_id) for file_id in selected_file_ids.split(',')]

        suggestions = chat_helper.get_suggestions(query, collection_id, thread_id, selected_file_ids)
        return make_response(jsonify({'message': suggestions}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


""" @chat.route('/metadata', methods=['POST'])
@auth_helper.token_required
def chat_metadata_gen():
    try:
        chat_response = chat_helper.chat_metadata_generate()
        return make_response(jsonify({'message': 'Metadata generated as a CSV file and added to the Collection'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500) """
