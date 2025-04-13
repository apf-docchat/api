from flask import Blueprint, Response, make_response, jsonify

from .helpers import docchat_query, update_faq_response
from source.api.utilities.externalapi_helpers import auth_helper

doc_chat_api = Blueprint('doc_chat_api', __name__)


@doc_chat_api.route('/chat', methods=['POST'])
@auth_helper.token_required
def chat_with_doc_chat():
    try:
        chat_response = docchat_query()
        response = Response(chat_response, content_type='text/event-stream')
        response.headers['Cache-Control'] = 'no-cache, no-transform'
        response.headers['Connection'] = 'keep-alive'
        return response
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_chat_api.route('/faq/update', methods=['POST'])
@auth_helper.token_required
def update_doc_chat_faq():
    try:
        updated_response = update_faq_response()
        return Response(updated_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
