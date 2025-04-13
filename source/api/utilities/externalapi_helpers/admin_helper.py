import json
import logging
import os
from datetime import datetime, timedelta
import random
from urllib.parse import quote

from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import chats_helper, collections_helper
from source.common import config

import bcrypt

logger = logging.getLogger('app')

# function to create new organization. it also inserts into organization_modules to link organization with modules with id 1,6,8 and 9. It also creates a new folder in this path config.ORGDIR_PATH with org_name as the folder name
def create_organization(org_name, clientid='', user_id=None):
    try:
        #find org_name using org_id and if org with same name already exists, return error
        result = db_helper.find_one(queries.V2_FIND_ORGANIZATION_BY_ORG_NAME, org_name)
        if result:
            return {'message': 'Organization not created!','error': f"Organization '{org_name}' already exists."}

        # Insert the new organization into the organization table
        org_id = db_helper.execute_and_get_id(queries.V2_INSERT_ORGANIZATION, org_name, clientid)
        logger.info(f"Organization '{org_name}' created successfully.")

        # Insert the organization into the user_organization table
        if user_id is None:
            user_id = request.context['user_id']
        db_helper.execute(queries.V2_INSERT_USER_ORGANIZATION, str(user_id), str(org_id), 'SUPER_USER')

        # Link the organization with modules 1, 6, 8, and 9
        module_ids = [1, 6, 8, 9, 10]
        for module_id in module_ids:
            db_helper.execute(
                queries.V2_INSERT_ORGANIZATION_MODULES,
                str(org_id), str(module_id)
            )
        logger.info(f"Organization '{org_name}' linked with modules {module_ids}.")

        # Create a new folder for the organization
        error_message = ''
        try:
            org_folder_path = os.path.join(config.ORGDIR_PATH, quote(org_name))
            os.makedirs(org_folder_path, exist_ok=True)
            
            if not os.path.exists(config.ORGFILES_BASE_DIR):
                os.makedirs(config.ORGFILES_BASE_DIR, exist_ok=True)
            if not os.path.exists(os.path.join(config.ORGFILES_BASE_DIR, org_name)):
                os.makedirs(os.path.join(config.ORGFILES_BASE_DIR, org_name), exist_ok=True)

            logger.info(f"Folder created at '{org_folder_path}' for organization '{org_name}'.")
        except Exception as e:
            logger.error(f"Error creating folder for organization '{org_name}': {str(e)}", exc_info=True)
            error_message = f"Error creating folder for organization '{org_name}': {str(e)}"

        #insert default collection NotInAnyCollection as placeholder for Bulk uploads
        collection_description = 'The default collection placeholder for bulk uploads'
        metadata_prompt_prelude = 'Please return strictly formatted JSON for the text in Context with following fields:\n'
        new_collection_id = db_helper.execute_and_get_id(queries.V2_INSERT_INTO_COLLECTIONS, 'NotInAnyCollection',  
                                                        collection_description, metadata_prompt_prelude, org_id, 10, None, 'ORG', 'file')

        return {'message': f"Organization '{org_name}' created successfully.\n{error_message}", 'org_id': org_id}
    except Exception as e:
        logger.error(f"Error creating organization '{org_name}': {str(e)}", exc_info=True)
        raise e

def get_all_organization_for_user():
    try:
        user_id = request.context['user_id']
        organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if len(organizations) > 0:
            result = [{'organization_id': organization['org_id'], 'organization_name': organization["org_name"], 'role': organization["role"]} for
                      organization in organizations]
            return result
        else:
            return []
    except Exception as e:
        logger.error(e)
        raise e

def add_modules_to_organization(org_id, module_list_csv):
    try:
        # Parse the CSV string into a list of module IDs, ensuring each item is a number
        module_ids = []
        if module_list_csv:
            for module_id in module_list_csv.split(','):
                module_id = module_id.strip()
                if module_id.isdigit():
                    module_ids.append(int(module_id))

        # Delete all existing module IDs for the given org_id
        db_helper.execute(queries.V2_DELETE_ORGANIZATION_MODULES_BY_ORG_ID, org_id)
        logger.info(f"Deleted all existing modules for organization ID {org_id}.")

        # Insert new module IDs
        for module_id in module_ids:
            if module_id:
              db_helper.execute(queries.V2_INSERT_ORGANIZATION_MODULES, org_id, module_id)
              logger.info(f"Module ID {module_id} added to organization ID {org_id}.")

        return {'message': f"Modules updated for organization ID {org_id} successfully."}
    except Exception as e:
        logger.error(f"Error updating modules for organization ID {org_id}: {str(e)}", exc_info=True)
        raise e

def save_organization_name(org_id, org_name):
  try:
    #find org_name using org_id and if org with same name already exists, return error
    result = db_helper.find_one(queries.V2_FIND_ORGANIZATION_BY_ORG_NAME, org_name)
    if result:
        return {'message': 'Org name not saved!','error': f"Organization '{org_name}' already exists."}

    # Retrieve the current organization name using org_id
    current_org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_ORGANIZATION_ID, org_id)
    if not current_org:
        return {'message': 'Org name not saved!', 'error': f"Organization with ID '{org_id}' does not exist."}

    current_org_name = current_org['org_name']

    # Update org name
    db_helper.execute(queries.V2_UPDATE_ORG_NAME, org_name, org_id)
    logger.info(f"Org name '{org_name}' saved successfully.")

    # Rename the org folder name for the organization
    current_org_folder_path = os.path.join(config.ORGDIR_PATH, quote(current_org_name))
    new_org_folder_path = os.path.join(config.ORGDIR_PATH, quote(org_name))

    if os.path.exists(current_org_folder_path):
        os.rename(current_org_folder_path, new_org_folder_path)
        logger.info(f"Folder renamed from '{current_org_folder_path}' to '{new_org_folder_path}' for organization '{org_name}'.")
    else:
        os.makedirs(new_org_folder_path, exist_ok=True)
        logger.info(f"Folder created at '{new_org_folder_path}' for organization '{org_name}'.")

    return {'message': f"Organization '{org_name}' updated successfully.", 'org_id': org_id}
  except Exception as e:
    logger.error(f"Error updating organization '{org_name}': {str(e)}", exc_info=True)
    raise e

def get_all_prompts():
  try:
    prompts = db_helper.find_many(queries.V2_FIND_ALL_PROMPTS)
    formatted_prompts = []

    for prompt in prompts:
      # Fetch archived prompts for the current prompt
      archived_prompts = db_helper.find_many(queries.V2_FIND_ARCHIVED_PROMPTS_BY_PROMPT_ID, prompt['id'])
      formatted_archived_prompts = [
          {
              'id': archived_prompt['id'],
              'prompt_id': archived_prompt['prompt_id'],
              'prompt_type': archived_prompt['prompt_type'],
              'prompt_name': archived_prompt['prompt_name'],
              'name_label': archived_prompt['name_label'],
              'prompt_text': archived_prompt['prompt_text'],
              'description': archived_prompt['description'],
              'datetime_created': archived_prompt['datetime_created'].isoformat()
          }
          for archived_prompt in archived_prompts
      ]

      formatted_prompts.append({
          'id': prompt['id'],
          'prompt_name': prompt['prompt_name'],
          'name_label': prompt['name_label'],
          'prompt_text': prompt['prompt_text'],
          'description': prompt['description'],
          'prompt_type': prompt['prompt_type'],
          'archivedPrompts': formatted_archived_prompts
      })

    return formatted_prompts
  except Exception as e:
    logger.error(e)
    raise e

def save_prompt(prompt_id, prompt_name, name_label, prompt_text, description, prompt_type):
    try:
        if prompt_id:
          # Fetch the current prompt data
          current_prompt = db_helper.find_one(queries.V2_FIND_PROMPT_BY_ID, prompt_id)
          if current_prompt:
            # Archive the current prompt data
            db_helper.execute(
                queries.V2_INSERT_PROMPT_ARCHIVE,
                current_prompt['id'],
                current_prompt['prompt_name'],
                current_prompt['name_label'],
                current_prompt['prompt_text'],
                current_prompt['description'],
                current_prompt['prompt_type'],
                datetime.utcnow()
            )
            logger.info(f"Prompt ID {prompt_id} archived successfully.")

          db_helper.execute(queries.V2_UPDATE_PROMPT, prompt_type, prompt_name, name_label, prompt_text, description, prompt_id)
          logger.info(f"Prompt ID {prompt_id} updated successfully.")
          return {'message': f"Prompt ID {prompt_id} updated successfully."}
        else:
            db_helper.execute(queries.V2_INSERT_PROMPT, prompt_type, prompt_name, name_label, prompt_text, description)
            logger.info(f"Prompt '{prompt_name}' saved successfully.")
            return {'message': f"Prompt '{prompt_name}' saved successfully."}
    except Exception as e:
        logger.error(f"Error saving prompt '{prompt_name}': {str(e)}", exc_info=True)
        raise e

def get_thread_for_user_by_thread_id(thread_id=None):
    try:
        thread = chats_helper.get_chat_history_by_thread_id(thread_id) or {}
        thread.pop('_id')
        thread.pop('user_id')
        thread.pop('organization_id')
        thread_created_datetime = thread.get('thread_created_datetime')
        if thread_created_datetime:
            thread_created_datetime = thread_created_datetime.replace(microsecond=0)
            thread['thread_created_datetime'] = thread_created_datetime.isoformat()
        for message in thread.get('messages'):
            chat_created_datetime = message.get('chat_created_datetime')
            if chat_created_datetime:
                chat_created_datetime = chat_created_datetime.replace(microsecond=0)
                message['chat_created_datetime'] = chat_created_datetime.isoformat()
        return thread
    except Exception as e:
        logger.error(e)
        raise e
    
def post_entity(entity_type):
    try:
        data = request.json
        if entity_type == 'issues':
            user_issue = json.loads(data.get('user_issue'))
            id = data.get('id')
            print(user_issue, id)
            if not id:
                return {'message': 'id field is required.'}
            user_issue['remarks'] = user_issue.get('remarks', '')
            user_issue['ticket_number'] = user_issue.get('ticket_number', random.randint(1000000000, 9999999999))
            user_issue['status'] = user_issue.get('status', 'Open')
            #construct Data field in the format: {"title": "issue 1", "description": "test", "status": "Open", "thread_id": "b7ad0b9d-7bbd-4974-83cc-631c4ffa62c0", "username": "user32", "collection_id": 133, "remarks": "test remarks", "ticket_number": 2850015642}
            """ issue_data = {
                'title': f"Issue {ticket_number}",
                'description': remarks,
                'status': status,
                'thread_id': data.get('thread_id'),
                'username': data.get('username'),
                'collection_id': data.get('collection_id'),
                'remarks': remarks,
                'ticket_number': ticket_number
            } """
            db_helper.execute(queries.UPDATE_ENTITY, json.dumps(user_issue), id, 'issues')
            logger.info(f"User Ticket {user_issue['ticket_number']} updated successfully.")
            return {'message': f"User Ticket {user_issue['ticket_number']} updated successfully."}
        else:
            return {'message': 'Entity type not supported.'}
    except Exception as e:
        logger.error(f"Error in post_entity: {str(e)}", exc_info=True)
        raise e

def create_user(username, password, email):
    try:
        # Check if the user already exists
        existing_user = db_helper.find_one(queries.FIND_USER_BY_USERNAME, username)
        if existing_user:
            return {'message': 'User not created!', 'error': f"User '{username}' already exists."}

        # Hash the password using bcrypt
        hashed_password = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())

        # Insert the new user into the users table
        user_id = db_helper.execute_and_get_id(queries.INSERT_USER, username, hashed_password.decode('utf-8'), email)
        logger.info(f"User '{username}' created successfully.")

        # Insert the "Default" role for the new user
        role_name = "Default"
        details = "Default role for new users"
        objectives = "1. Do research based on available context."
        user_role_id = db_helper.execute_and_get_id(queries.INSERT_ROLE, user_id, role_name, details, objectives)
        logger.info(f"Role '{role_name}' created for user '{username}' successfully.")

        # Set this role as the currently chosen role for the new user
        db_helper.execute(queries.INSERT_USER_ROLE, user_role_id, user_id)
        logger.info(f"Role '{role_name}' set as the current role for user '{username}' successfully.")

        return {'message': f"User '{username}' created successfully with role '{role_name}'.", 'user_id': user_id}
    except Exception as e:
        logger.error(f"Error creating user '{username}': {str(e)}", exc_info=True)
        raise e

def get_user_list():
    try:
        users = db_helper.find_many(queries.FIND_ALL_USERNAMES)
        if users:
            result = [{'user_id': user['id'], 'username': user['username'], 'email': user['email']} for user in users]
            return result
        else:
            return []
    except Exception as e:
        logger.error(e)
        raise e

def save_user_name(user_id, username):
    try:
        # Check if the username already exists
        existing_user = db_helper.find_one(queries.FIND_USER_BY_USERNAME, username)
        if existing_user:
            return {'message': 'Username not saved!', 'error': f"Username '{username}' already exists."}

        # Update the username
        db_helper.execute(queries.UPDATE_USER_NAME, username, user_id)
        logger.info(f"Username for user ID '{user_id}' updated to '{username}' successfully.")

        return {'message': f"Username for user ID '{user_id}' updated to '{username}' successfully."}
    except Exception as e:
        logger.error(f"Error updating username for user ID '{user_id}': {str(e)}", exc_info=True)
        raise e
    
def save_email(user_id, email):
    try:
        # Check if the username already exists
        existing_user = db_helper.find_one(queries.FIND_USER_BY_EMAIL, email)
        if existing_user:
            return {'message': 'Email not saved!', 'error': f"Email '{email}' already exists."}

        # Update the username
        db_helper.execute(queries.UPDATE_EMAIL, email, user_id)
        logger.info(f"Email for user ID '{user_id}' updated to '{email}' successfully.")

        return {'message': f"Email for user ID '{user_id}' updated to '{email}' successfully."}
    except Exception as e:
        logger.error(f"Error updating email for user ID '{user_id}': {str(e)}", exc_info=True)
        raise e

def populate_collection_dashboard(org_id):
    #find all collections within the org which were created in the last week and which don't have any insight added for them
    #identify start and end time to match timestamp datatype of mysql and set the value to one week back to today

    start_time = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    end_time = start_time.replace(hour=23, minute=59, second=59)
    start_time = start_time - timedelta(days=7)
    start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
    end_time = end_time.strftime('%Y-%m-%d %H:%M:%S')
    
    collections = db_helper.find_many(queries.FIND_COLLECTIONS_WITHOUT_INSIGHTS_FOR_ORG_WITHIN_TIMEFRAME, org_id, start_time, end_time)
    for collection in collections:
        collection_id = collection['collection_id']
        collections_helper.add_collection_insight(collection_id, org_id)
        print(f"Collection {collection_id} populated successfully.")
    return {'message': 'Collection dashboard populated successfully.'}
