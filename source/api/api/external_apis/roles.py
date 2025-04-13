import json
import random
from flask import Blueprint, Response, jsonify, make_response, request
from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import auth_helper, roles_helper

roles = Blueprint('roles', __name__)

@roles.route('/list/<username>', methods=['GET'])
@auth_helper.token_required
def get_roles_list(username):
    try:
        roles_list = roles_helper.get_roles_list(username)
        return make_response(jsonify({'data': roles_list, 'message': 'List of roles fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('/<id>', methods=['GET'])
@auth_helper.token_required
def get_roles(id):
    try:
        insight = roles_helper.get_role(id)
        return make_response(jsonify({'data': insight, 'message': 'roles fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('', methods=['POST'])
@auth_helper.token_required
def add_role():
    try:
        new_insight = roles_helper.add_role()
        return make_response(jsonify({'data': new_insight, 'message': 'New role created successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('/<id>', methods=['PATCH'])
@auth_helper.token_required
def update_role(id):
    try:
        new_insight = roles_helper.update_role(id)
        return make_response(jsonify({'data': new_insight, 'message': 'Collection insight updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('/<id>/<username>', methods=['DELETE'])
@auth_helper.token_required
def delete_role(id, username):
    try:
        message = roles_helper.delete_role(id, username)
        return make_response(jsonify({'data': message, 'message': 'role deleted successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('/user/<username>', methods=['GET'])
@auth_helper.token_required
def get_user_role(username):
    try:
        message = roles_helper.get_user_role(username)
        return make_response(jsonify({'data': message, 'message': 'Current role is obtained successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@roles.route('/user/<username>/<id>', methods=['PATCH'])
@auth_helper.token_required
def update_user_role(username, id):
    try:
        new_insight = roles_helper.update_user_role(username, id)
        return make_response(jsonify({'data': new_insight, 'message': 'Collection insight updated successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
