from flask import Blueprint, Response, stream_with_context

from .helpers import generate_data

mock_api = Blueprint('mock_api', __name__)


@mock_api.route('/generate-response', methods=['POST'])
def generate_response():
    return Response(generate_data(), content_type='text/event-stream')


@mock_api.route('/stream2', methods=['GET'])
def stream_data2():
    data_generator = generate_data()
    return Response(stream_with_context(data_generator), content_type='text/plain')
