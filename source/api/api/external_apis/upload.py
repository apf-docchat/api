from flask import Blueprint, jsonify, make_response
from source.api.utilities.externalapi_helpers import auth_helper, upload_helper

app = Blueprint('fileprocessor_legacy', __name__)


@app.route('/metadata/upload', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised
def upload_metadata_file():
    try:
        upload_helper.upload_metadata_file()
        return make_response(jsonify({'message': 'File metadata updated successfully!'}), 200)
    except Exception as e:
        return make_response(jsonify({'message': str(e)}), 500)
