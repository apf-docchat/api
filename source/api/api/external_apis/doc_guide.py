from flask import Blueprint, jsonify, make_response, Response
from source.api.utilities.externalapi_helpers import auth_helper, docguide_helper

doc_guide = Blueprint('doc_guide', __name__)


@doc_guide.route('/chat', methods=['POST'])
@auth_helper.token_required
def chat_with_doc_guide():
    try:
        chat_response = docguide_helper.docguide_general_query()
        return Response(chat_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/files', methods=['GET'])
@auth_helper.token_required
def get_docguide_files():
    try:
        files = docguide_helper.get_docguide_files()
        return make_response(
            jsonify({'data': files, 'message': 'Files fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/collection-files', methods=['GET'])
@auth_helper.token_required
def get_docguide_collection_files():
    try:
        files = docguide_helper.get_docguide_collection_files()
        return make_response(
            jsonify({'data': files, 'message': 'Files fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/sections', methods=['GET'])
@auth_helper.token_required
def get_docguide_sections():
    try:
        sections = docguide_helper.get_docguide_sections()
        return make_response(
            jsonify({'data': sections, 'message': 'Sections fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/sections/<section_id>', methods=['GET'])
@auth_helper.token_required
def get_docguide_section(section_id):
    try:
        section = docguide_helper.get_docguide_section(section_id)
        return make_response(
            jsonify({'data': section, 'message': 'Section fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/sections/chat/summary', methods=['POST'])
@auth_helper.token_required
def summary_for_doc_guide_sections_chat():
    try:
        chat_response = docguide_helper.docguide_sections_chat_summary()
        return Response(chat_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/sections/chat', methods=['POST'])
@auth_helper.token_required
def doc_guide_sections_chat():
    try:
        chat_response = docguide_helper.docguide_sections_chat()
        return Response(chat_response, content_type='text/event-stream')
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_guide.route('/sections/chat/event-message', methods=['POST'])
@auth_helper.token_required
def doc_guide_sections_event_message():
    try:
        event_payload = docguide_helper.docguide_section_chat_events()
        return make_response(jsonify({'data': event_payload, 'message': 'Event message fetched successfully.'}),
                             200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
