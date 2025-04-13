

from flask import Blueprint, Response, jsonify, make_response

from source.api.utilities.externalapi_helpers import askdoc_helper, auth_helper


askdoc = Blueprint('ask_doc', __name__)

@askdoc.route('/chat', methods=['POST'])
@auth_helper.token_required
def chat_with_ask_doc():
    try:
        chat_response = askdoc_helper.askdoc_query()
        return Response(chat_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
