from flask import request, Flask

from source.common import config
from source.common.flask_app_logger import setup_app_logger
from source.common.flask_sqlachemy import db
from source.internal_api import flask_config


def create_app():
    app = Flask(__name__)

    # Setup custom app logger
    setup_app_logger(app)

    app.config.from_object(flask_config.Config)

    app.url_map.strict_slashes = False

    app.json.sort_keys = False

    db.init_app(app)

    @app.before_request
    def validate_api_key():
        api_key = request.headers.get('x-api-key')

        if not api_key or api_key != config.INTERNAL_API_KEY:
            raise Exception('Invalid API key')

    @app.route('/files/upload', methods=['POST'])
    def upload_files():
        # Request args
        org_dir = request.args.get('org_dir')
        files = request.files.getlist('file')

        # Validations
        if not org_dir:
            return {'error': 'Missing org_dir parameter'}, 400

        if not files:
            return {'error': 'No files provided'}, 400

        return {'status': 'ok'}, 200

    @app.route('/files/update', methods=['POST'])
    def update_files():
        # Request args
        org_dir = request.args.get('org_dir')
        files = request.files.getlist('file')

        # Validations
        if not org_dir:
            return {'error': 'Missing org_dir parameter'}, 400

        if not files:
            return {'error': 'No files provided'}, 400

        # Processing

        return {'status': 'ok'}, 200

    @app.route('/files/remove', methods=['POST'])
    def remove_files():
        # Request args
        org_dir = request.get_json().get('org_dir')
        files = request.get_json().get('files')

        # Validations
        if not org_dir:
            return {'error': 'Missing org_dir parameter'}, 400

        if not files:
            return {'error': 'No files provided'}, 400

        return {'status': 'ok'}, 200

    return app
