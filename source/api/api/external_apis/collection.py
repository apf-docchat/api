import os
from flask import Blueprint, jsonify, make_response
from source.api.utilities.externalapi_helper import delete_collection_helper, file_get_helper, files_get_helper, \
    update_collection_helper, file_upload_helper, file_delete_helper, move_files_between_collection_helper
from source.api.utilities.externalapi_helpers import auth_helper, collections_helper
from werkzeug.exceptions import Conflict

collections = Blueprint('collection', __name__)

# @app.route('/', methods=['GET'])
# @auth_helper.token_required
# def get_all_collections_for_organization():
#     try:
#         collections = collections_helper.get_collections_for_organization()
#         return make_response(jsonify({'data': collections, 'message': 'Collections fetched successfully!'}), 200)
#     except RuntimeError as re:
#         return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
#     except Exception as e:
#         return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
#
#
# @app.route('/', methods=['POST'])
# @auth_helper.token_required
# def create_collection():
#     try:
#         collections_helper.create_collection_helper()
#         return make_response(jsonify({'message': 'Collection created successfully!'}), 200)
#     except RuntimeError as re:
#         return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
#     except Exception as e:
#         return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@collections.route('/<collection_id>', methods=['DELETE'])
@auth_helper.token_required
def delete_collection(collection_id):
    try:
        delete_collection_helper(collection_id)
        return make_response(jsonify({'message': 'Collection deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


# @app.route('/<collection_id>', methods=['PUT'])
# @auth_helper.token_required
# def update_collection(collection_id):
#     try:
#         updated_collection = update_collection_helper(collection_id)
#         return make_response(jsonify({'data': updated_collection, 'message': 'Collection updated successfully!'}), 200)
#     except RuntimeError as re:
#         return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
#     except Exception as e:
#         return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
#
#
# @app.route('/file/move-file', methods=['PATCH'])
# @auth_helper.token_required
# def move_files_between_collection():
#     try:
#         move_files_between_collection_helper()
#         return make_response(jsonify({'message': 'Files moved successfully!'}), 200)
#     except RuntimeError as re:
#         return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
#     except Exception as e:
#         return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
#
#
# @app.route('/file', methods=['POST'])
# @auth_helper.token_required
# def file_upload():
#     try:
#         file_upload_helper()
#         return make_response(jsonify({'message': 'Files uploaded successfully!'}), 200)
#     except RuntimeError as re:
#         return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
#     except Exception as e:
#         return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/file', methods=['GET'])
@auth_helper.token_required
def file_get():
    try:
        return file_get_helper()
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

#get all files of a collection
@collections.route('/files', methods=['GET'])
@auth_helper.token_required
def files_get():
    try:
        return files_get_helper()
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/file', methods=['DELETE'])
@auth_helper.token_required
def file_delete():
    try:
        file_delete_helper()
        return make_response(jsonify({'message': 'Files deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


#following routes were earlier in routes.py inside v2. moved back here to eliminate v2 folder

@collections.route('/file', methods=['POST'])
@auth_helper.token_required
def file_upload():
    try:
        file_upload_helper()
        return make_response(jsonify({'message': 'Files uploaded successfully!'}), 200)
    except Conflict as e:
        response = make_response(jsonify({'message': 'Conflict error occurred.', 'error': str(e)}), 200)
        response.headers['Content-Type'] = 'application/json'
        return response
    except RuntimeError as re:
        response = make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
        response.headers['Content-Type'] = 'application/json'
        return response
    except Exception as e:
        response = make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
        response.headers['Content-Type'] = 'application/json'
        return response


@collections.route('/<collection_id>', methods=['PUT'])
@auth_helper.token_required
def update_collection(collection_id):
    try:
        updated_collection = update_collection_helper(collection_id)
        return make_response(jsonify({'data': updated_collection, 'message': 'Collection updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@collections.route('/file/move-file', methods=['PATCH'])
@auth_helper.token_required
def move_files_between_collection():
    try:
        move_files_between_collection_helper()
        return make_response(jsonify({'message': 'Files moved successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/insights/list/<collection_id>', methods=['GET'])
@auth_helper.token_required
def get_collection_insights_list(collection_id):
    try:
        insights_list = collections_helper.get_collection_insights_list(collection_id)
        return make_response(jsonify({'data': insights_list, 'message': 'List of Collection insights fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/insights/<collection_id>/<id>', methods=['GET'])
@auth_helper.token_required
def get_collection_insights(collection_id, id):
    try:
        insight = collections_helper.get_collection_insight(collection_id, id)
        return make_response(jsonify({'data': insight, 'message': 'Collection insights fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/insights/<collection_id>', methods=['POST'])
@auth_helper.token_required
def add_collection_insight(collection_id):
    try:
        new_insight = collections_helper.add_collection_insight(collection_id)
        return make_response(jsonify({'data': new_insight, 'message': 'New Collection insight created successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/insights/<collection_id>/<id>', methods=['PATCH'])
@auth_helper.token_required
def update_collection_insight(collection_id, id):
    try:
        new_insight = collections_helper.update_collection_insight(collection_id, id)
        return make_response(jsonify({'data': new_insight, 'message': 'Collection insight updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/insights/<collection_id>/<id>', methods=['DELETE'])
@auth_helper.token_required
def delete_collection_insight(collection_id, id):
    try:
        message = collections_helper.delete_collection_insight(collection_id, id)
        return make_response(jsonify({'data': message, 'message': 'Collection insight deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/<collection_id>/columns/<table_name>', methods=['GET'])
@auth_helper.token_required
def get_collection_table_columnnames(collection_id, table_name):
    try:
        column_list = collections_helper.get_collection_table_columnnames(collection_id, table_name)
        return make_response(jsonify({'data': column_list, 'message': 'Table columns fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('', methods=['GET'])
@auth_helper.token_required
def get_all_collections_for_organization():
    try:
        collections_list = collections_helper.get_collections_for_organization("ALL")
        return make_response(jsonify({'data': collections_list, 'message': 'Collections fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/admin', methods=['GET'])
@auth_helper.token_required
def get_all_collections_for_admin_for_organization():
    try:
        collections_list = collections_helper.get_collections_for_organization("SUPER_USER")
        return make_response(jsonify({'data': collections_list, 'message': 'Collections for admin fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('', methods=['POST'])
@auth_helper.token_required
def create_collection():
    try:
        collections_helper.create_collection_helper()
        return make_response(jsonify({'message': 'Collection created successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@collections.route('/faq/<faq_id>', methods=['DELETE'])
@auth_helper.token_required
def delete_faq(faq_id):
    try:
        collections_helper.delete_faq_helper(faq_id)
        return make_response(jsonify({'message': 'FAQ deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)