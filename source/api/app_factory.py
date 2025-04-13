from flask import Flask, request, jsonify, send_from_directory, \
    make_response
from flask_swagger_ui import get_swaggerui_blueprint

from source.api import flask_config
from source.api.api.external_apis.askdoc import askdoc
from source.api.api.external_apis.auth import auth
from source.api.api.external_apis.chat import chat
from source.api.api.external_apis.collection import collections
from source.api.api.external_apis.doc_guide import doc_guide
from source.api.api.external_apis.entities import entities
from source.api.api.external_apis.fileprocessor import fileprocessor
from source.api.api.external_apis.jobs import jobs
from source.api.api.external_apis.roles import roles
from source.api.api.external_apis.sysadmin import sysadmin
from source.api.api.external_apis.thread import chat_threads
from source.api.api.external_apis.functions import functions
from source.api.api.external_apis.popupbot import popupbot
from source.api.api.external_apis.webhooks import webhooks
from source.api.endpoints.doc_analysis.doc_analysis_api import doc_analysis_api
from source.api.endpoints.doc_chat.doc_chat_api import doc_chat_api
from source.api.endpoints.mock.mock_api import mock_api
from source.api.endpoints.news_scraper.news_scraper_api import news_scraper_api
from source.api.endpoints.orgs.helpers import get_modules_in_organization
from source.api.endpoints.orgs.orgs_api import orgs_api
from source.api.utilities.externalapi_helpers import auth_helper
from source.api.utilities.helper_functions import delete_files_from_db, \
    add_files_to_db
from source.common import config
from source.common.flask_app_logger import setup_app_logger
from source.common.flask_sqlachemy import db


def create_app():
    app = Flask(__name__)

    # Setup custom app logger
    setup_app_logger(app)

    app.config.from_object(flask_config.Config)

    app.url_map.strict_slashes = False

    app.json.sort_keys = False

    db.init_app(app)

    swagger_ui_blueprint = get_swaggerui_blueprint(
        base_url='/api/v2/docs',
        api_url='/static/swagger.json',
        config={
            'app_name': "DocChat"
        }
    )

    extapi_swagger_ui_blueprint = get_swaggerui_blueprint(
        base_url='/api/v2/functions/hr/',
        api_url='/static/swagger_hr.yaml',
        config={
            'app_name': "HR API"
        }
    )

    app.register_blueprint(swagger_ui_blueprint, name='swagger_ui_docchat')
    app.register_blueprint(extapi_swagger_ui_blueprint, name='swagger_ui_hr_api')
    app.register_blueprint(mock_api, url_prefix='/api/v2/mock')
    app.register_blueprint(auth, url_prefix='/api/v2')
    app.register_blueprint(orgs_api, url_prefix='/api/v2/organization')
    app.register_blueprint(doc_chat_api, url_prefix='/api/v2/doc-chat')
    app.register_blueprint(doc_analysis_api, url_prefix='/api/v2/doc-analysis')
    app.register_blueprint(news_scraper_api, url_prefix='/api/v2/news-scraper')
    app.register_blueprint(doc_guide, url_prefix='/api/v2/doc-guide')
    app.register_blueprint(collections, url_prefix='/api/v2/collection')
    app.register_blueprint(fileprocessor, url_prefix='/api/v2/file-processor')
    app.register_blueprint(chat_threads, url_prefix='/api/v2/threads')
    app.register_blueprint(askdoc, url_prefix='/api/v2/ask-doc')
    app.register_blueprint(chat, url_prefix='/api/v2/chat')
    app.register_blueprint(sysadmin, url_prefix='/api/v2/admin')
    app.register_blueprint(entities, url_prefix='/api/v2/entities')
    app.register_blueprint(jobs, url_prefix='/api/v2/jobs')
    app.register_blueprint(roles, url_prefix='/api/v2/roles')
    app.register_blueprint(functions, url_prefix='/api/v2/functions')
    app.register_blueprint(webhooks, url_prefix='/v2/webhooks')
    app.register_blueprint(webhooks, url_prefix='/webhooks', name='webhooks_unversioned')  # Remove after updating URLs
    app.register_blueprint(popupbot, url_prefix='/api/v2/popupbot')

    @app.route('/healthcheck', methods=['GET'])
    def healthcheck():
        app.logger.debug('Checking health')
        app.logger.info('Health check successful')
        return 'OK'

    # route to handle call from vectoriser whenever new files are added to the FTP folder
    @app.route('/addfiles', methods=['POST'])
    def addfiles():
        # Check for the API key in the request header
        api_key = request.headers.get('X-Api-Key')
        if api_key != config.INTERNAL_API_KEY:
            # If the API key is not correct, return a 401 Unauthorized response
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        try:
            data = request.get_json()
            org_name = data['org_name']
            filenames = data['filenames']

            # Add files to the filesystem and database
            add_files_to_db(org_name, filenames)

            return jsonify({'status': 'success', 'message': 'Files added successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # route to handle call from vectoriser whenever files are deleted from the FTP folder
    @app.route('/deletefiles', methods=['POST'])
    def deletefiles():
        # Check for the API key in the request header
        api_key = request.headers.get('X-Api-Key')
        if api_key != config.INTERNAL_API_KEY:
            # If the API key is not correct, return a 401 Unauthorized response
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        try:
            # Extract org_name and filenames from the POST request
            data = request.get_json()
            org_name = data['org_name']
            filenames = data['filenames']

            # Remove records from database
            delete_files_from_db(org_name, filenames)

            return jsonify({'status': 'success', 'message': 'Files deleted successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    # TODO: UNAUTHENTICATED! THIS NEEDS TO BE AUTHENTICATED
    @app.route('/static-files/<path:filename>')
    def serve_static_files(filename):
        try:
            # Use Flask's send_from_directory function to serve the static files
            return send_from_directory(f'{config.ORGDIR_PATH}/', filename)
        except Exception as e:
            print(e)
            return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

    # Remove after moving to /orgs/<org_id>/modules
    @app.route('/api/v2/module', methods=['GET'])
    @auth_helper.token_required
    def get_all_modules():
        try:
            modules = get_modules_in_organization()
            return make_response(jsonify({'data': modules, 'message': 'Modules fetched successfully!'}), 200)
        except RuntimeError as re:
            return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
        except Exception as e:
            return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

    return app
