from flask import Blueprint, make_response, jsonify

from source.api.utilities.externalapi_helpers import auth_helper
from .helpers import get_all_organization_for_user, get_modules_in_organization

orgs_api = Blueprint('orgs_api', __name__)


@orgs_api.route('/', methods=['GET'])
@auth_helper.token_required
def get_all_orgs():
    try:
        organizations = get_all_organization_for_user()
        return make_response(jsonify({'data': organizations, 'message': 'Organizations fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@orgs_api.route('/<org_id>/modules', methods=['GET'])
@auth_helper.token_required
def get_org_modules():
    try:
        modules = get_modules_in_organization()
        return make_response(jsonify({'data': modules, 'message': 'Modules fetched successfully!'}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)
