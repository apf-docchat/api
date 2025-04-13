import logging

from flask import request
from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, Prompts, StreamEvent, ChatFileCategory
from source.api.utilities.externalapi_helpers.collections_helper import create_collection_helper, get_collection_ids_for_user
from source.api.utilities.externalapi_helper import file_upload_helper
from source.common import config

logger = logging.getLogger('app')

def add_candidates(job_id):
    try:
        # Check if the collection for the job ID exists
        collection_name = f"job_{job_id}"
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, collection_name)

        if not collection:
            # Create a new collection if it doesn't exist
            collection_description = f"Collection for job {job_id}"
            module_id = 10  # Setting defauls module_id to 10 i.e. new chat mod
            org_id = int(request.context['organization_id'])
            is_private = False

            create_collection_helper(collection_name, collection_description, module_id, org_id, is_private, None, 'file', '', '')
            collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, collection_name)
            collection_id = collection.get('collection_id')
        else:
            collection_id = collection.get('collection_id')

        file_upload_helper(collection_id)
        
        return collection_id
    except Exception as e:
        logger.error(e)
        raise e