from flask import Blueprint, make_response, jsonify, request, Response, stream_with_context

from .helpers import DocAnalysis
from source.api.utilities.externalapi_helpers import auth_helper

doc_analysis_api = Blueprint('doc_analysis_api', __name__)


@doc_analysis_api.route('/upload/temp', methods=['POST'])
@auth_helper.token_required
def doc_analysis_upload_temp():
    try:
        response = DocAnalysis().upload_file_temp()
        return make_response(jsonify(response), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_analysis_api.route('/upload/process', methods=['POST'])
@auth_helper.token_required
def doc_analysis_process_upload():
    try:
        # Extract collection_id from the request data
        data = request.get_json()
        collection_id = data.get('collection_id')

        return Response(
            DocAnalysis().process_upload_file(collection_id),
            content_type='text/event-stream',
            headers={
                'Cache-Control': 'no-cache, no-transform',
                'Connection': 'keep-alive',
            }
        )
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_analysis_api.route('/chat', methods=['POST'])
@auth_helper.token_required
def doc_analysis_chat():
    try:
        # Extract collection_id from the request data
        data = request.get_json()
        collection_id = data.get('collection_id')

        """ response = docanalysis_helper.execute_file_analysis()
        return make_response(jsonify(response), 200) """
        # chat_response = docanalysis_helper.execute_file_analysis()
        # response = Response(docanalysis_helper.execute_file_analysis(), content_type='text/event-stream')
        # response.headers['Cache-Control'] = 'no-cache, no-transform'
        # response.headers['Connection'] = 'keep-alive'
        # return response
        return Response(stream_with_context(DocAnalysis().execute_file_analysis(collection_id)),
                        content_type='text/event-stream')
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_analysis_api.route('/parse-file', methods=['POST'])
@auth_helper.token_required
def doc_analysis_parse_file():
    try:
        response = DocAnalysis().parse_file()
        return make_response(jsonify(dict(data=response, message="File parsed successfully")), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@doc_analysis_api.route('/file', methods=['DELETE'])
@auth_helper.token_required
def doc_analysis_delete_file():
    try:
        response = DocAnalysis().delete_file()
        return make_response(jsonify(response), 200)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
