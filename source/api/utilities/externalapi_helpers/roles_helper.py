import json
import logging
from urllib.parse import quote

from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, StreamEvent
from source.api.utilities.externalapi_helpers import chat_helper
from source.common import config
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper

logger = logging.getLogger('app')

# Role related functions - BEGIN

def get_roles_list(username):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        
        roles_list = db_helper.find_many(queries.FIND_ROLES_LIST_BY_USER_ID, user_id) or []
        print(roles_list)
        return roles_list
    except Exception as e:
        logger.error(e)
        raise e

#get role function: to run a role with input files etc and send back results
def get_role(id): 
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        data = request.get_json()
        username = data.get('username')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        role = db_helper.find_one(queries.FIND_ROLE_BY_ID, id, user_id) or {}
        print(role)
        """ if not roles:
            raise RuntimeError('roles not found!') """
        
        return role
    except Exception as e:
        logger.error(e)
        raise e
    
def get_user_role(username):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        role = db_helper.find_one(queries.FIND_USER_ROLE, user_id) or {}
        print(role)
        """ if not roles:
            raise RuntimeError('roles not found!') """
        
        return role
    except Exception as e:
        logger.error(e)
        raise e

def add_role():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        data = request.get_json()
        username = data.get('username')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        if not username:
            raise RuntimeError('Username is required!')
        role_name = data.get('role_name')
        details = data.get('details', None)
        objectives = data.get('objectives', None)
        #print(objectives)
        #steps = request.context['steps']
        
        new_role_id = db_helper.execute_and_get_id(queries.INSERT_ROLE, user_id, role_name, details, objectives)
        new_role = db_helper.find_one(queries.FIND_ROLE_BY_ID, new_role_id, user_id)
        response_json = dict(id=new_role.get('id'), role_name=new_role.get('role_name'), objectives=new_role.get('objectives'))
        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def update_role(id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        data = request.get_json()
        username = data.get('username')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        role = db_helper.find_one(queries.FIND_ROLE_BY_ID, id, user_id)
        if data.get('role_name'):
            role_name = data.get('role_name')
        else:
            role_name = role.get('role_name')
        if data.get('details'):
            details = data.get('details')
        else:
            details = role.get('details')
        if data.get('objectives'):
            objectives = data.get('objectives')
        else:
            objectives = role.get('objectives')

        updated_role_id = db_helper.execute_and_get_id(queries.UPDATE_ROLE, role_name, details, objectives, id, user_id)
        updated_role = db_helper.find_one(queries.FIND_ROLE_BY_ID, id, user_id)
        return updated_role
    except Exception as e:
        logger.error(e)
        raise e

def update_user_role(username, id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')

        db_helper.execute_and_get_id(queries.DELETE_USER_ALL_ROLES, user_id)
        updated_role_id = db_helper.execute_and_get_id(queries.INSERT_USER_ROLE, id, user_id)
        updated_role = db_helper.find_one(queries.FIND_ROLE_BY_ID, id, user_id)
        response_json = dict(id=updated_role.get('id'), role_name=updated_role.get('role_name'), objectives=updated_role.get('objectives'))
        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def delete_role(id, username):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')

        #delete any user role with the role id
        db_helper.execute_and_get_id(queries.DELETE_USER_ROLE_BY_ID, id, user_id)
        db_helper.execute_and_get_id(queries.DELETE_ROLE, id, user_id)
        return f"role with id {id} deleted successfully"
    except Exception as e:
        logger.error(e)
        raise e

def change_role_status(username, old_id, new_id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get('id')
        db_helper.execute_and_get_id(queries.CHANGE_USER_ROLE, old_id, new_id, user_id)
        role = db_helper.find_one(queries.FIND_ROLE_BY_ID, new_id, user_id)
        return {"id": role.id, "role_name": role.role_name, "objectives": role.objectives}
    except Exception as e:
        logger.error(e)
        raise e

# Role related functions - END