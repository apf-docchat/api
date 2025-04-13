import logging

from flask import request

from source.api.utilities import db_helper, queries

logger = logging.getLogger('app')


def get_all_organization_for_user():
    try:
        user_id = request.context['user_id']
        organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if len(organizations) > 0:
            result = [{'organization_id': organization['org_id'], 'organization_name': organization["org_name"],
                       'role': organization["role"]} for
                      organization in organizations]
            return result
        else:
            return []
    except Exception as e:
        logger.error(e)
        raise e


def get_modules_in_organization():
    try:
        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            # modules = find_modules_by_organization_id(request.context['organization_id'])
            modules = db_helper.find_many(queries.FIND_MODULES_BY_ORGANIZATION_ID, organization_id)
        else:
            modules = db_helper.find_many(queries.FIND_ALL_MODULES)
        if len(modules) > 0:
            result = [{'module_id': module['id'], 'module_name': module["button_text"], 'module_type': module['name'],
                    'module_description': module['description']}
                    for
                    module in modules]
            return result
        else:
            return []
    except Exception as e:
        logger.error(e)
        raise e
