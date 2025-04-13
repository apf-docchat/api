import logging

from flask import Blueprint, jsonify, request, make_response

from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import auth_helper, admin_helper

sysadmin = Blueprint('sysadmin', __name__)

logger = logging.getLogger('app')

@sysadmin.route('/organization', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def admin_create_new_organization():
    try:
        data = request.json
        org_name = data.get('org_name')
        if not org_name:
           return make_response(jsonify({'message': 'Organization name is required.'}), 400)

        result = admin_helper.create_organization(org_name)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in create_organization_endpoint: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 200)


@sysadmin.route('/organization', methods=['GET'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def admin_get_all_orgs():
    try:
        organizations = admin_helper.get_all_organization_for_user()
        return make_response(jsonify({'data': organizations, 'message': 'Organizations fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/organization/module', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def add_modules_to_organization():
    try:
        data = request.json
        org_id = data.get('org_id')
        module_list_csv = data.get('module_list_csv')
        if not org_id or module_list_csv is None:
            return make_response(jsonify({'message': 'Organization ID and module list are required.'}), 400)

        # Call the helper function to save the module list
        result = admin_helper.add_modules_to_organization(org_id, module_list_csv)
        return make_response(jsonify({'data': result, 'message': 'Modules saved successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in add_modules_to_organization: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/organization/name', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def admin_save_org_name():
    try:
        data = request.json
        org_id = data.get('org_id')
        org_name = data.get('org_name')
        if not org_id or not org_name:
            return make_response(jsonify({'error': 'Organization ID and Org name are required.'}), 200)

        # Call the helper function to save the module list
        result = admin_helper.save_organization_name(org_id, org_name)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 200)
    except Exception as e:
        logger.error(f"Error in admin_save_org_name: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 200)

@sysadmin.route('/prompt', methods=['GET'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def get_all_prompts():
    try:
        # Call the helper function to get all prompts
        prompts = admin_helper.get_all_prompts()
        return make_response(jsonify({'data': prompts, 'message': 'Prompts fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 200)
    except Exception as e:
        logger.error(f"Error in get_all_prompts: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 200)

@sysadmin.route('/prompt', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def save_prompt():
    try:
        data = request.json
        prompt_id = data.get('id')
        prompt_name = data.get('prompt_name')
        name_label = data.get('name_label')
        prompt_text = data.get('prompt_text')
        description = data.get('description')
        prompt_type = data.get('prompt_type')

        if not prompt_name or not name_label or not prompt_text or not prompt_type:
            return make_response(jsonify({'message': 'All fields are required.'}), 400)

        # Call the helper function to save the prompt
        result = admin_helper.save_prompt(prompt_id, prompt_name, name_label, prompt_text, description, prompt_type)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 200)
    except Exception as e:
        logger.error(f"Error in save_prompt: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 200)

# GET - Retrieve multiple entities
@sysadmin.route('/<entity_type>', methods=['GET'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def get_entities(entity_type):
    try:
        # Example: Query to retrieve all entities of a specific type
        entity_list = db_helper.find_many(
            queries.V2_FIND_ENTITIES_BY_TYPE, entity_type
        )
        return jsonify({'data': entity_list}), 200
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/<entity_type>', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def post_entity(entity_type):
    try:
        result = admin_helper.post_entity(entity_type)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/thread/<thread_id>', methods=['GET'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def get_chat_thread(thread_id):
    try:
        thread = admin_helper.get_thread_for_user_by_thread_id(thread_id)
        return make_response(jsonify({'data': thread, 'message': 'Thread fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/user', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def create_user():
    try:
        data = request.json
        username = data.get('username')
        password = data.get('password')
        email = data.get('email')
        if not username or not password or not email:
            return make_response(jsonify({'message': 'Username, password, and email are required.'}), 400)

        result = admin_helper.create_user(username, password, email)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in create_user: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/user', methods=['GET'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def get_user_list():
    try:
        users = admin_helper.get_user_list()
        return make_response(jsonify({'data': users, 'message': 'User list fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in get_user_list: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/user/username', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def save_user_name():
    try:
        data = request.json
        user_id = data.get('id')
        username = data.get('username')
        if not user_id or not username:
            return make_response(jsonify({'message': 'User ID and username are required.'}), 400)

        result = admin_helper.save_user_name(user_id, username)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in save_user_name: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/user/email', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def save_email():
    try:
        data = request.json
        user_id = data.get('id')
        email = data.get('email')
        if not user_id or not email:
            return make_response(jsonify({'message': 'User ID and email are required.'}), 400)

        result = admin_helper.save_email(user_id, email)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in save_email: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@sysadmin.route('/collection/dashboard/<org_id>', methods=['POST'])
@auth_helper.token_required
@auth_helper.authorised_sysadmin
def collection_dashboard_populate(org_id):
    try:
        result = admin_helper.populate_collection_dashboard(org_id)
        return make_response(jsonify(result), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        logger.error(f"Error in collection_dashboard_populate: {str(e)}", exc_info=True)
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)