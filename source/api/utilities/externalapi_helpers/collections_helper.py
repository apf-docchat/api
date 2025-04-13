import datetime
import json
import logging
import os
from urllib.parse import quote
import uuid

from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, StreamEvent
from source.api.utilities.externalapi_helpers import chat_helper
from source.api.utilities.externalapi_helpers.googledrive_helper import GoogleDriveHelper
from source.common import config
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper

logger = logging.getLogger('app')


""" def get_collections_for_organization():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        organization_id = request.context['organization_id']
        collection_name = request.args.get('collection_name')
        if collection_name:
            collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, collection_name)
            if not collection:
                raise RuntimeError("Collection not found!")
            collections = db_helper.find_many(queries.FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                              organization_id, collection.get('collection_id'))
            if not collections:
                raise RuntimeError("Collection not found!")
        else:    
            # collections = find_collections_by_organization_id(request.context['organization_id'])
            #collections = db_helper.find_many(queries.FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id)
            collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id)
        if len(collections) == 0:
            return []
        for collection in collections:
            collection['files'] = []
        collection_ids = [collection.get('collection_id') for collection in collections]
        # files = find_files_by_collection_ids(collection_ids)
        #files = db_helper.find_many(queries.FIND_FILES_BY_COLLECTION_IDS, collection_ids)
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)

        for file_entry in files:
            collection = list(filter(lambda x: x.get('collection_id') == file_entry.get('collection_id'), collections))[
                0]
            collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                            file_name=file_entry.get('file_name'),
                                            file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                            file_upload_datetime=file_entry.get('upload_datetime').isoformat()))

        result = collections
        return result

    except Exception as e:
        logger.error(e)
        raise e """

""" def get_collections_for_organization():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        organization_id = request.context['organization_id']
        user_id = request.context['user_id']
        logger.debug(f"####################User ID: {user_id}")
        collection_name = request.args.get('collection_name')
        collection_ids = get_collection_ids_for_user(user_id, organization_id)
        if not collection_ids:
            return []

        if collection_name:
            collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, collection_name)
            if not collection:
                raise RuntimeError("Collection not found!")
            elif collection.get('collection_id') not in collection_ids:
                raise RuntimeError("Collection not found!")
            collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                              organization_id, collection.get('collection_id'))
            if not collections:
                raise RuntimeError("Collection not found!")
        else:
            collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id, collection_ids)

        if len(collections) == 0:
            return []
        modules = db_helper.find_many(queries.FIND_ALL_MODULES)
        for collection in collections:
            collection['files'] = []
            module = next(
                (module for module in modules if module.get('id') == collection.get('module_id')), {})
            collection['module_name'] = module.get('button_text')
            collection['module_type'] = module.get('name')
        collection_ids = [collection.get('collection_id') for collection in collections]
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)
        # files = find_files_by_collection_ids(collection_ids)

        for file_entry in files:
            collection = list(filter(lambda x: x.get('collection_id') == file_entry.get('collection_id'), collections))[
                0]
            collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                            file_name=file_entry.get('file_name'),
                                            file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                            file_upload_datetime=file_entry.get('upload_datetime').isoformat()))
        collections = [
            dict(collection_id=collection.get('collection_id'), collection_name=collection.get('collection_name'), collection_description=collection.get('description'),is_private=False if collection.get('sharing_level')=='ORG' else True,module_id=collection.get('module_id'),
                 module_name=collection.get('module_name'), module_type=collection.get('module_type'),
                 files=collection.get('files')) for collection in collections]
        result = collections
        return result

    except Exception as e:
        logger.error(e)
        raise e """

def get_collections_for_organization(role):
    try:
        if 'organization_id' not in request.context:
            user_id = request.context['user_id']
            logger.debug(f"Organization ID not found in context. Fetching organizations for user ID: {user_id}")
            if role == 'ALL':
                organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
            elif role == 'SUPER_USER':
                organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID_SUPER_USER, user_id)
            if not organizations:
                raise RuntimeError('No organizations found for the user!')
            
            organization_collections = {}
            for org in organizations:
                organization_id = org.get('org_id')
                organization_name = org.get('org_name')
                collection_ids = get_collection_ids_for_user(user_id, organization_id)
                if not collection_ids:
                    continue

                collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id, collection_ids)
                if len(collections) == 0:
                    continue

                modules = db_helper.find_many(queries.FIND_ALL_MODULES)
                for collection in collections:
                    collection['files'] = []
                    module = next(
                        (module for module in modules if module.get('id') == collection.get('module_id')), {})
                    collection['module_name'] = module.get('button_text')
                    collection['module_type'] = module.get('name')
                collection_ids = [collection.get('collection_id') for collection in collections]
                files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)

                for file_entry in files:
                    file_entry_metadata = db_helper.find_one(queries.FIND_FILES_METADATA_BY_FILE_ID, file_entry.get('file_id'))
                    collection = list(filter(lambda x: x.get('collection_id') == file_entry.get('collection_id'), collections))[0]
                    if file_entry_metadata is not None:
                        collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                                    file_name=file_entry.get('file_name'),
                                                    file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                                    file_upload_datetime=file_entry.get('upload_datetime').isoformat(), file_description=file_entry_metadata.get('file_description'), training=file_entry_metadata.get('training'), handout=file_entry_metadata.get('handout'), media=file_entry_metadata.get('media')))
                    else:
                        collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                                    file_name=file_entry.get('file_name'),
                                                    file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                                    file_upload_datetime=file_entry.get('upload_datetime').isoformat())
                                                )
                
                #if db_uri get list of all Tables in the DB
                for collection in collections:
                    db_uri = collection.get('db_uri')
                    if db_uri != '' and db_uri is not None:
                        db_tables = get_table(db_uri)
                        collection['tables'] = [{'table_name': table} for table in db_tables]

                collections = [
                    dict(collection_id=collection.get('collection_id'), collection_name=collection.get('collection_name'), collection_description=collection.get('description'), is_private=False if collection.get('sharing_level') == 'ORG' else True, module_id=collection.get('module_id'),
                         module_name=collection.get('module_name'), module_type=collection.get('module_type'),
                         files=collection.get('files'),
                         tables=collection.get('tables')) for collection in collections]
                organization_collections[organization_id] = collections

            return organization_collections

        else:
            organization_name = request.context['organization_name']
            organization_id = request.context['organization_id']
            user_id = request.context['user_id']
            if role == 'SUPER_USER':
                organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID_AND_ORG_ID_SUPER_USER, user_id, organization_id)
                if not organizations:
                    return []

            logger.debug(f"####################User ID: {user_id}")
            collection_name = request.args.get('collection_name')
            collection_ids = get_collection_ids_for_user(user_id, organization_id)
            if not collection_ids:
                return []

            if collection_name:
                collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, collection_name)
                if not collection:
                    raise RuntimeError("Collection not found!")
                elif collection.get('collection_id') not in collection_ids:
                    raise RuntimeError("Collection not found!")
                collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                  organization_id, collection.get('collection_id'))
                if not collections:
                    raise RuntimeError("Collection not found!")
            else:
                collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id, collection_ids)

            if len(collections) == 0:
                return []
            modules = db_helper.find_many(queries.FIND_ALL_MODULES)
            for collection in collections:
                collection['files'] = []
                module = next(
                    (module for module in modules if module.get('id') == collection.get('module_id')), {})
                collection['module_name'] = module.get('button_text')
                collection['module_type'] = module.get('name')
            collection_ids = [collection.get('collection_id') for collection in collections]
            files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)

            for file_entry in files:
                file_entry_metadata = db_helper.find_one(queries.FIND_FILES_METADATA_BY_FILE_ID, file_entry.get('file_id'))
                collection = list(filter(lambda x: x.get('collection_id') == file_entry.get('collection_id'), collections))[0]
                if file_entry_metadata is not None:
                    collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                                file_name=file_entry.get('file_name'),
                                                file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                                file_upload_datetime=file_entry.get('upload_datetime').isoformat(), file_description=file_entry_metadata.get('file_description'), training=file_entry_metadata.get('training'), handout=file_entry_metadata.get('handout'), media=file_entry_metadata.get('media')))
                else:
                    collection['files'].append(dict(file_id=file_entry.get('file_id'),
                                                file_name=file_entry.get('file_name'),
                                                file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry.get("file_name"))}',
                                                file_upload_datetime=file_entry.get('upload_datetime').isoformat())
                                            )
            #if db_uri get list of all Tables in the DB
            for collection in collections:
                db_uri = collection.get('db_uri')
                if db_uri != '' and db_uri is not None:
                    db_tables = get_table(db_uri)
                    collection['tables'] = [{'table_name': table} for table in db_tables]

            collections = [
                dict(collection_id=collection.get('collection_id'), collection_name=collection.get('collection_name'), collection_description=collection.get('description'), is_private=False if collection.get('sharing_level') == 'ORG' else True, module_id=collection.get('module_id'),
                    module_name=collection.get('module_name'), module_type=collection.get('module_type'),
                    files=collection.get('files'),
                    tables=collection.get('tables')) for collection in collections]
            result = collections
            return result

    except Exception as e:
        logger.error(e)
        raise e

def get_table(db_uri):
    try:
        logger.debug(f"Fetching tables from DB")

        # Extract the database name and schema name from the db_uri
        db_uri_parts = db_uri.split('/')
        if 'postgres' in db_uri or 'postgresql' in db_uri:
            db_name = db_uri_parts[-2]  # Database name is the second last part
            schema_name = db_uri_parts[-1]  # Schema name is the last part
        else:
            db_name = db_uri_parts[-1]  # Database name is the last part
            schema_name = None  # No schema name for MySQL

        print(f"DB Name: {db_name}, Schema Name: {schema_name}")
        # Modified query to get both table_schema and table_name
        if schema_name:
            get_tables_query = f"""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{schema_name}'
                AND table_type = 'BASE TABLE'
            """
        else:
            get_tables_query = f"""
                SELECT table_schema, table_name 
                FROM information_schema.tables 
                WHERE table_schema = '{db_name}'
            """

        tables_df = db_helper.find_collection_db_many(get_tables_query, db_uri)
        print(tables_df)

        if not tables_df.empty:
            # Process both schema and table name from the query results
            if schema_name:
                tables = [f"{row['table_name']}" for index, row in tables_df.iterrows()]
            else:
                tables = [f"{row['table_name']}" for index, row in tables_df.iterrows()]

            # logger.info(f"Tables found: {tables}")
            return tables
        else:
            logger.info("No tables found.")
            return []
    except Exception as e:
        logger.error(f"Error fetching tables from DB: {e}", exc_info=True)
        return []

def get_collection_table_columnnames(collection_id, table_name):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        db_uri = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id).get('db_uri')
        columns = get_table_columns(db_uri, table_name)
        return columns
    except Exception as e:
        logger.error(e)
        raise e

def get_table_columns(db_uri, table_name):
    logger.debug(f"Fetching columns from DB")

    # Extract the database name and schema name from the db_uri
    db_uri_parts = db_uri.split('/')
    if 'postgres' in db_uri or 'postgresql' in db_uri:
        db_name = db_uri_parts[-2]  # Database name is the second last part
        schema_name = db_uri_parts[-1]  # Schema name is the last part
    else:
        db_name = db_uri_parts[-1]  # Database name is the last part
        schema_name = None  # No schema name for MySQL

    print(f"DB Name: {db_name}, Schema Name: {schema_name}")
    # Modified query to get both table_schema and table_name
    if schema_name:
        get_columns_query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{schema_name}'
            AND table_name = '{table_name}'
        """
    else:
        get_columns_query = f"""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_schema = '{db_name}'
            AND table_name = '{table_name}'
        """

    columns_df = db_helper.find_collection_db_many(get_columns_query, db_uri)
    print(columns_df)

    if not columns_df.empty:
        # Process both schema and table name from the query results
        columns = [f"{row['column_name']}" for index, row in columns_df.iterrows()]

        #logger.info(f"Tables found: {tables}")
        return columns
    else:
        logger.info("No columns found.")
        return []

def get_collection_ids_for_user(user_id, organization_id):
    try:
        # Query to get all collections

        collections = db_helper.find_many(queries.V2_FIND_ALL_COLLECTIONS_BY_ORGANIZATION_ID, organization_id)

        # List to store collection_ids the user has permission to access
        accessible_collection_ids = []

        for collection in collections:
            sharing_level = collection.get('sharing_level')
            owner_id = collection.get('user_id')
            shared_with = collection.get('shared_with')

            if sharing_level is None or sharing_level == 'ORG':
                # User has access to all collections with sharing_level NULL or ORG
                accessible_collection_ids.append(collection.get('collection_id'))
            elif sharing_level in ['PRIVATE', 'LIMITED']:
                # User has access if they are the owner or in the shared_with list
                if owner_id == user_id or (shared_with and user_id in json.loads(shared_with)):
                    accessible_collection_ids.append(collection.get('collection_id'))

        return accessible_collection_ids

    except Exception as e:
        logger.error(e)
        raise e

""" def create_collection_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        collection_name = request.json.get('name')
        collection_description = request.json.get('description')
        # collection_id = insert_collection(collection_name, collection_description)
        metadata_prompt_prelude = 'Please return strictly formatted JSON for the text in Context with following fields:\n'
        collection_id = db_helper.execute_and_get_id(queries.INSERT_COLLECTION, collection_name, collection_description,
                                                     metadata_prompt_prelude)
        db_helper.execute(queries.INSERT_ORGANIZATION_COLLECTION, organization_id, collection_id)
        # insert_organization_collection(collection_id, organization_id)
    except Exception as e:
        print(e)
        raise e """

def create_collection_helper(collection_name=None, collection_description=None, module_id=None, org_id=None, is_private=None, user_id=None, collection_type=None, db_uri=None, googlesheet_url=None):
    try:
        """ if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id'] """
        if user_id is None:
            user_id = request.context['user_id']
        if collection_name is None:
            collection_name = request.json.get('name')
        if collection_description is None:
            collection_description = request.json.get('description')
        if module_id is None:
            module_id = request.json.get('module_id')
        if org_id is None:
            org_id = request.json.get('org_id')
        if collection_type is None:
            collection_type = request.json.get('type')
        if db_uri is None:
            db_uri = request.json.get('db_uri')
        if googlesheet_url is None:
            googlesheet_url = request.json.get('googlesheet_url')
        
        if org_id is not None and org_id != 0:
            # Fetch all organizations for the user
            user_orgs = db_helper.find_many(queries.FIND_ORG_ID_BY_USER_ID, user_id)
            user_org_ids = [org.get('org_id') for org in user_orgs]
            print(user_org_ids, org_id)
            if org_id not in user_org_ids:
                raise RuntimeError(f'User does not have permission to create Space in the team!')
            organization_id = org_id
        elif 'organization_id' in request.context:
            organization_id = request.context['organization_id']
        else:
            raise RuntimeError('Organization Id is required!')
        
        if is_private is None:
            is_private = request.json.get('is_private', False)

        if collection_type == 'googlesheet':
            credentials_json = db_helper.find_one(queries.V2_FIND_GOOGLESHEET_COLLECTIONS_CREDENTIALS_JSON, 'googlesheet').get('credentials_json')
            gdrive_service = GoogleDriveHelper(json.loads(credentials_json))
            gsheet_file_id = googlesheet_url.split('/')[5]
            file_name = gdrive_service.get_filename(gsheet_file_id)

        # collection_id = insert_collection(collection_name, collection_description)
        metadata_prompt_prelude = 'Please return strictly formatted JSON for the text in Context with following fields:\n'
        if is_private:
            collection_id = db_helper.execute_and_get_id(queries.V2_INSERT_INTO_COLLECTIONS, collection_name,
                                                     collection_description, metadata_prompt_prelude, organization_id,
                                                     module_id, user_id, 'PRIVATE', collection_type)
        else:
            collection_id = db_helper.execute_and_get_id(queries.V2_INSERT_INTO_COLLECTIONS, collection_name,
                                                     collection_description, metadata_prompt_prelude, organization_id,
                                                     module_id, None, 'ORG', collection_type)
        if collection_type == 'db':
            db_uri_json = json.dumps({'db_uri': db_uri})
            new_cc_id = db_helper.execute_and_get_id(queries.V2_INSERT_INTO_COLLECTIONS_CREDENTIALS_DB_URI, collection_type, db_uri_json)
            db_helper.execute(queries.V2_UPDATE_COLLECTIONS_WITH_CREDENTIAL_ID, new_cc_id, collection_id)
        elif collection_type == 'googlesheet':
            cc_id = db_helper.find_one(queries.V2_FIND_GOOGLESHEET_COLLECTIONS_CREDENTIALS_ID, 'googlesheet').get('id')
            db_helper.execute(queries.V2_UPDATE_COLLECTIONS_WITH_CREDENTIAL_ID, cc_id, collection_id)
            db_helper.execute(queries.V2_INSERT_FILE, file_name, '', collection_id, googlesheet_url)

        # insert_organization_collection(collection_id, organization_id)
    except Exception as e:
        print(e)
        raise e

def delete_faq_helper(faq_id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context['user_id']
        if faq_id != '0':
            db_helper.execute(queries.DELETE_COLLECTIONS_FAQ, faq_id)
    except Exception as e:
        print(e)
        raise e

# Insight related functions - BEGIN

def format_timestamp(db_timestamp):
    # Ensure the input is a datetime object
    if isinstance(db_timestamp, str):
        db_timestamp = datetime.datetime.strptime(db_timestamp, "%Y-%m-%d %H:%M:%S")  # Adjust format as needed

    now = datetime.datetime.now()
    today_start = datetime.datetime(now.year, now.month, now.day)
    yesterday_start = today_start - datetime.timedelta(days=1)

    # If timestamp is today
    if db_timestamp >= today_start:
        time_diff = now - db_timestamp
        minutes_ago = time_diff.total_seconds() // 60
        if minutes_ago < 60:
            return f"{int(minutes_ago)} mins ago" if minutes_ago > 1 else "Just now"
        else:
            return f"{int(minutes_ago // 60)} hrs ago"

    # If timestamp is yesterday
    elif db_timestamp >= yesterday_start:
        return "Yesterday"

    # If timestamp is this year but before yesterday
    elif db_timestamp.year == now.year:
        return db_timestamp.strftime("%b %d")  # Format: "Feb 10"

    # If timestamp is from a previous year
    else:
        return db_timestamp.strftime("%b %d, %Y")  # Format: "Feb 10, 2023"

def get_collection_insights_list(collection_id):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        collection_insights_list = db_helper.find_many(queries.FIND_COLLECTION_INSIGHTS_LIST_BY_COLLECTION_ID, collection_id)
        if not collection_insights_list:
            collection_insights_list = []
        i = 0
        for collection_insight in collection_insights_list:
            collection_insights_list[i]['updated_at'] = format_timestamp(collection_insight.get('updated_at'))
            file_path_uuid = collection_insight.get('file_path_uuid') or ''
            collection_insights_list[i]['html_data'] = ''
            collection_insights_list[i]['image_data'] = ''
            if file_path_uuid != '':
                folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
                html_file_path = f"{folder_path}/1_html"  #1_html keeping in mind future multi-step if reqd.
                image_file_path = f"{folder_path}/1_image"
                if os.path.exists(html_file_path):
                    with open(html_file_path) as f:
                        collection_insights_list[i]['html_data'] = f.read()
                if os.path.exists(image_file_path):
                    with open(image_file_path) as f:
                        collection_insights_list[i]['image_data'] = f.read()
            i += 1

        return collection_insights_list
    except Exception as e:
        logger.error(e)
        raise e

""" def get_collection_insight(collection_id, id):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        insight = db_helper.find_one(queries.FIND_COLLECTION_INSIGHT_BY_COLLECTION_ID, collection_id, id)

        file_path_uuid = insight.get('file_path_uuid')
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        html_file_path = f"{folder_path}/1_html"  #1_html keeping in mind future multi-step if reqd.
        image_file_path = f"{folder_path}/1_image"
        if os.path.exists(html_file_path):
            with open(html_file_path) as f:
                insight['html_data'] = f.read()
        if os.path.exists(image_file_path):
            with open(image_file_path) as f:
                insight['image_data'] = f.read()

        print(insight)

        return insight
    except Exception as e:
        logger.error(e)
        raise e """

def get_collection_insight(collection_id, id):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        insight = db_helper.find_one(queries.FIND_COLLECTION_INSIGHT_BY_COLLECTION_ID, collection_id, id)
        #print(insight)

        file_path_uuid = insight.get('file_path_uuid')
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        os.makedirs(folder_path, exist_ok=True)
        #delete all old files in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            # Check if it is a file and delete it
            if os.path.isfile(file_path):
                os.remove(file_path)

        response_json = []
        chat_response = chat_helper.chat_query(query=insight.get('query'), collection_id = collection_id, thread_id = '')
        for response in chat_response:
            # Parse the response string while preserving spaces
            event = None
            data = None
            for line in response.splitlines():
                if line.startswith("event:"):
                    event = line[len("event:"):].strip()  # Remove trailing spaces only
                elif line.startswith("data:"):
                    data = line.replace("data: ","")  # Remove trailing spaces only

            # Reformat the response and yield it
            if (event == StreamEvent.FINAL_OUTPUT):
                data = data.encode('utf-8', errors='replace').decode('utf-8')
                data_json = json.loads(data)
                if data_json.get('image_data') is not None:
                    response_json = dict(order_number=insight.get('order_number'), title=insight.get('title'), html_data=data_json['message'], image_data=data_json['image_data'], query=insight.get('query'))
                else:
                    response_json = dict(order_number=insight.get('order_number'), title=insight.get('title'), html_data=data_json['message'], query=insight.get('query'))
        
                #store intermediate results as files & add to html_data and image_data array variables for each step
                file_name = '1'
                file_data = data_json['message'].strip('\n')
                htmlfile_path = f"{folder_path}/{file_name}_html"
                with open(htmlfile_path, 'w') as file:
                    file.write(file_data)

                if data_json.get('image_data') is not None:
                    image_data = data_json['image_data']
                    image_path = f"{folder_path}/{file_name}_image"
                    with open(image_path, 'wb') as image_file:
                        image_file.write(image_data.encode('utf-8'))

        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def add_collection_insight(collection_id, organization_id=None):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if organization_id is None:
            if 'organization_id' not in request.context:
                raise RuntimeError('Organization Id is required!')
            organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        manager = chat_helper.ChatManager(PortKeyConfigs.NEW_CHAT_INSIGHT)
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.user_current_role = db_helper.find_one(queries.FIND_USER_ROLE, user_id) or {}
        print(manager.user_current_role)
        manager.query = ''
        manager.collection_id = collection_id
        manager.thread_id = ''
        new_insight_query, new_insight_title, new_insight_order_number = manager.chat_insight_generate(collection_id)

        file_path_uuid = str(uuid.uuid4())
        print(new_insight_query, new_insight_title, new_insight_order_number)
        new_insight_id = db_helper.execute_and_get_id(queries.INSERT_COLLECTION_INSIGHT, collection_id, new_insight_query, new_insight_title, new_insight_order_number, user_id, file_path_uuid)
        new_insight = db_helper.find_one(queries.FIND_COLLECTION_INSIGHT_BY_COLLECTION_ID, collection_id, new_insight_id)
        response_json = dict(order_number=new_insight.get('order_number'), title=new_insight.get('title'), query=new_insight.get('query'), id=new_insight.get('id'), updated_at=format_timestamp(new_insight.get('updated_at')))
        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def update_collection_insight(collection_id, id):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        query = request.json.get('query')

        #get a new title appropriate to new query
        new_title = get_query_title(query, user_id)
        updated_insight_id = db_helper.execute_and_get_id(queries.UPDATE_COLLECTION_INSIGHT, query, new_title, user_id, id)
        updated_insight = db_helper.find_one(queries.FIND_COLLECTION_INSIGHT_BY_COLLECTION_ID, collection_id, id)
        return updated_insight
    except Exception as e:
        logger.error(e)
        raise e

def delete_collection_insight(collection_id, id):
    try:
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']

        db_helper.execute_and_get_id(queries.DELETE_COLLECTION_INSIGHT, user_id, id)
        return f"Insight with id {id} deleted successfully"
    except Exception as e:
        logger.error(e)
        raise e

def get_query_title(query, user_id):
    try:
        # Call AI to identify get new title
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DEFAULT_GPT4o)
        response = json.loads(openai_helper.callai_json(
            system_content="For the english language query given by the user give an appropriate 2-3 word title. Return the output as a JSON in the following format: {'title': <appropriate 2-3 word title for this insight>}",
            user_content=query,
            user_id=user_id
        ))
        #print(response)
        return response['title']
    except Exception as e:
        logger.error(e)
        raise e

# Insight related functions - END