import io
import logging
import os
from urllib.parse import quote
from urllib.parse import urlparse
import zipfile

import requests
from flask import request, send_file, jsonify, make_response
from pymongo import MongoClient
from werkzeug.exceptions import Conflict

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import FileSupported
from source.common import config

mongo_uri = config.MONGO_URI
mongo_client = MongoClient(mongo_uri)

logger = logging.getLogger('app')


def update_pinecone_vectors_metadata(file_names, org_name, new_folder_name):
    try:
        """ import pinecone
        pinecone.init(api_key=config.pinecone_api_key, environment=config.pinecone_environment)
        index = pinecone.Index(config.pinecone_index_name) """
        from pinecone import Pinecone
        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        index = pc.Index(config.PINECONE_INDEX_NAME)

        # Query to fetch vectors by filename and orgname
        # is namespace needed or does not mentioning take default???
        query_results = index.query(vector=[0] * 1536,
                                    filter={"orgname": {"$eq": org_name},
                                            "filename": {"$in": file_names}},
                                    top_k=10000,
                                    include_metadata=True, include_values=False)

        for match in query_results['matches']:
            index.update(id=match['id'], set_metadata={"collection": new_folder_name})

        # pinecone.close()
    except Exception as e:
        print(e)
        raise e


""" def delete_collection_helper(collection_id):
    try:
        collection_id = int(collection_id)
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        # finding collection by collection id to delete
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)

        # if selected collection is default collection, ignore deletion
        if collection['collection_name'] == 'NotInAnyCollection':
            raise RuntimeError("Cannot delete default collection!")
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']

        # finding default collection ('NotInAnyCollection')
        default_collection_name = 'NotInAnyCollection'
        # default_collection = find_collection_by_collection_name(default_collection_name)
        default_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, default_collection_name)
        default_collection_id = default_collection['collection_id']

        # finding files in collection to be deleted
        # files = find_files_by_collection_ids([collection_id])
        #files = db_helper.find_many(queries.FIND_FILES_BY_COLLECTION_IDS, [collection_id])
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, [collection_id])
        file_ids = [file['file_id'] for file in files]

        # finding files in default collection
        # files_in_default = find_files_by_collection_ids([default_collection_id])
        #files_in_default = db_helper.find_many(queries.FIND_FILES_BY_COLLECTION_IDS, [default_collection_id])
        files_in_default = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, [default_collection_id])
        file_ids_in_default = [file['file_id'] for file in files_in_default]

        # finding file ids in the collection (that going to be deleted) that are not already there in default collection yet
        files_ids_not_in_default = list(filter(lambda x: x not in file_ids_in_default, file_ids))

        # if there is any files associated with this collection, delete the association entry
        if len(file_ids) > 0:
            db_helper.execute(queries.DELETE_FILES_COLLECTION_BY_COLLECTION_ID, collection_id)
            # delete_files_collections_by_collection_id(collection_id)

        # if there are files which are not there in default collection yet
        if len(files_ids_not_in_default) > 0:
            entries = [(file_id, default_collection_id) for file_id in files_ids_not_in_default]

            # moving the files from the collection (that going to be deleted) to default collection
            db_helper.execute(queries.INSERT_COLLECTION, entries)
            # insert_many_files_collection(entries)

        # deleting collection-organization association entries
        db_helper.execute(queries.DELETE_ORGANIZATION_COLLECTION_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id,
                          collection_id)
        # delete_organization_collection_by_organization_id_and_collection_id(organization_id, collection_id)

        # deleting collection
        db_helper.execute(queries.DELETE_COLLECTION_BY_COLLECTION_ID, collection_id)
        # delete_collection_by_collection_id(collection_id)

        files_names_not_in_default = [file['file_name'] for file in
                                      list(filter(lambda x: x['file_id'] in file_ids_in_default, files))]
        update_pinecone_vectors_metadata(files_names_not_in_default, organization_name, default_collection_name)
    except Exception as e:
        print(e)
        raise e """

def delete_collection_helper(collection_id):
    try:
        collection_id = int(collection_id)
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        # finding collection by collection id to delete
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        # Convert collection_id to a tuple
        collection_ids = (collection_id,)
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)
        if files:
            file_ids = [file['file_id'] for file in files]
            #logger.info(f"Deleting files: {', '.join(map(str, file_ids))}")

            # Convert file_ids to a format suitable for SQL IN clause
            formatted_file_ids = tuple(file_ids)
            #logger.info(f"Formatted file ids: {str(formatted_file_ids)}")

            #delete vectors if any from pinecone - PENDING TASK - TODO LATER

            #delete files from server folder
            file_path = os.path.join(config.ORGDIR_PATH, organization_name)
            files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, formatted_file_ids)
            #logger.debug(f"Files found for deletion: {files}")
            file_names = [file['file_name'] for file in files]
            logger.info(f"Deleting files: {', '.join(file_names)}")
            for file_name in file_names:
                #logger.info(f"Deleting file with name: {file_name}")
                full_file_path = os.path.join(file_path, file_name)
                #logger.info(f"Full file path: {file_path}")
                if os.path.exists(full_file_path):
                    logger.info(f"file path exists")
                    os.remove(full_file_path)

            #delete files from db
            db_helper.execute(queries.DELETE_FILES_BY_FILE_ID, formatted_file_ids)
            db_helper.execute(queries.DELETE_FILES_METADATA_BY_FILE_ID, formatted_file_ids)
            db_helper.execute(queries.DELETE_FILES_METADATA_PLUS_BY_FILE_ID, formatted_file_ids)

        # finally remove the collection
        db_helper.execute(queries.DELETE_COLLECTION_BY_COLLECTION_ID, collection_id)

    except Exception as e:
        print(e)
        raise e


""" def update_collection_helper(collection_id):
    try:
        collection_id = int(collection_id)
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        if collection['collection_name'] == 'NotInAnyCollection':
            raise RuntimeError("Cannot update default collection!")
        organization_name = request.context['organization_name']
        collection_name = request.json.get('name')
        collection_description = request.json.get('description') or collection['description']
        db_helper.execute(queries.UPDATE_COLLECTION, collection_id, collection_name, collection_description)
        # update_collection(collection_id, collection_name, collection_description)
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        # files = find_files_by_collection_ids([collection_id])
        #files = db_helper.find_many(queries.FIND_FILES_BY_COLLECTION_IDS, [collection_id])
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, [collection_id])
        updated_collection = {'collection_id': collection['collection_id'],
                              'collection_name': collection['collection_name'],
                              'collection_description': collection['description'], 'files': []}
        for file_entry in files:
            updated_collection['files'].append({'file_id': file_entry['file_id'],
                                                'file_name': file_entry['file_name'],
                                                'file_url': f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry["file_name"])}'})
        return updated_collection
    except Exception as e:
        print(e)
        raise e """

def update_collection_helper(collection_id):
    try:
        collection_id = int(collection_id)
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')

        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        if not collection:
            raise RuntimeError("Collection not found!")

        organization_name = request.context['organization_name']

        # Only update fields that are provided in the request
        update_fields = {}
        if 'name' in request.json:
            update_fields['collection_name'] = request.json['name']
        if 'description' in request.json:
            update_fields['description'] = request.json['description']

        if update_fields:
            update_query = "UPDATE collections SET "
            update_query += ", ".join(f"{key} = %s" for key in update_fields)
            update_query += " WHERE collection_id = %s"

            update_values = list(update_fields.values()) + [collection_id]

            db_helper.execute(update_query, *update_values)

        # Fetch the updated collection
        updated_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)

        # Fetch associated files
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, [collection_id])

        # Prepare the response
        response_data = {
            'collection_id': updated_collection['collection_id'],
            'collection_name': updated_collection['collection_name'],
            'collection_description': updated_collection['description'],
            'files': []
        }

        for file_entry in files:
            response_data['files'].append({
                'file_id': file_entry['file_id'],
                'file_name': file_entry['file_name'],
                'file_url': f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry["file_name"])}'
            })

        return response_data

    except Exception as e:
        logger.error(e)
        raise e



""" def move_files_between_collection_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        collection_name = collection['collection_name']
        file_ids = request.json.get("file_ids")
        file_ids = [int(file_id) for file_id in file_ids]
        db_helper.execute(queries.UPDATE_COLLECTION_ID_IN_FILES_COLLECTION_BY_FILE_IDS_AND_ORGANIZATION_ID,
                          collection_id, file_ids,
                          organization_id)
        # update_collection_in_files_collection_by_collection_id_and_organization_id(collection_id, file_ids,
        #                                                                            organization_id)
        # files = find_files_by_file_ids(file_ids)
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        file_names = [file['file_name'] for file in files]
        update_pinecone_vectors_metadata(file_names, organization_name, collection_name)
    except Exception as e:
        print(e)
        raise e """

def move_files_between_collection_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")
        # collection = find_collection_by_collection_id(collection_id)
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        collection_name = collection['collection_name']

        file_ids = request.json.get("file_ids")
        file_ids = [int(file_id) for file_id in file_ids]

        # Check if all files belong to the same collection from the files_collection table
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)

        if len(files) == 0:
            raise RuntimeError("Files not found!")

        collection_ids = set([file['collection_id'] for file in files])
        
        if len(collection_ids) > 0:
            # Get the source collection's module ID
            source_collection_id = list(collection_ids)[0]  # Take any one as they should all be from the same collection
            source_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, source_collection_id)
            
            if not source_collection:
                raise RuntimeError("Source collection not found!")
            
            # Compare module IDs of source and target collections
            source_module_id = source_collection.get('module_id')
            target_module_id = collection.get('module_id')
            
            if source_module_id != target_module_id:
                raise RuntimeError("Cannot move files between collections with different modules.")

        db_helper.execute(queries.V2_UPDATE_COLLECTION_ID_IN_FILES_BY_FILE_IDS,
                          collection_id, file_ids)
        # update_collection_in_files_collection_by_collection_id_and_organization_id(collection_id, file_ids,
        #                                                                            organization_id)
        # files = find_files_by_file_ids(file_ids)
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        file_names = [file['file_name'] for file in files]
        update_pinecone_vectors_metadata(file_names, organization_name, collection_name)
    except Exception as e:
        print(e)
        raise e


""" def file_upload_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context.get('organization_name')
        files_path = os.path.join(config.ORGDIR_PATH, organization_name)
        if not os.path.exists(files_path):
            os.makedirs(files_path)

            # Check whether a file or a URL is being uploaded
        if 'file' in request.files:
            # Save the uploaded file in the data/unprocessed folder
            file = request.files['file']
            file_name = file.filename
            current_saved_file_path = os.path.join(str(files_path), str(file_name))
            file.save(current_saved_file_path)
        elif 'url' in request.form:
            # Download the content from the URL and save it to the data/unprocessed folder
            url = request.form['url']
            parsed_url = urlparse(url)

            # Reconstruct the URL without query string
            url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            response = requests.get(url)
            if response.status_code != 200:
                raise RuntimeError("Failed to download the file from the provided URL.")
            file_content = response.content
            file_name = os.path.basename(url)
            current_saved_file_path = os.path.join(str(files_path), str(file_name))
            with open(current_saved_file_path, 'wb') as f:
                f.write(file_content)
        else:
            raise RuntimeError('Please attach a file or url to process!')
    except Exception as e:
        print(e)
        raise e """

def file_upload_helper(collection_id=None):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context.get('organization_name')

        # Get collection_id from request parameters
        if collection_id is None:
            collection_id = request.args.get('collection_id')
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        if not collection:
            raise RuntimeError("Collection not found!")

        # Get Module id
        module_id = collection.get('module_id')
        if not module_id:
            raise RuntimeError("Module not found!")

        module_name = db_helper.find_one(queries.FIND_MODULES_BY_MODULE_ID, module_id).get('name')
        current_saved_file_path = ''

        files_path = os.path.join(config.ORGDIR_PATH, organization_name)
        if not os.path.exists(files_path):
            os.makedirs(files_path)

        # Check whether a file or a URL is being uploaded
        if 'file' in request.files:
            # Save the uploaded file in the data/unprocessed folder
            file = request.files['file']
            file_name = file.filename

            file_extension = file_name.split('.')[-1]
            file_supported = FileSupported.is_extension_supported(module_name, file_extension)
            if not file_supported:
                raise RuntimeError(f"File type {file_extension} is not supported for module {module_name}")

            current_saved_file_path = os.path.join(str(files_path), str(file_name))

            # Check if file already exists
            if os.path.exists(current_saved_file_path):
                raise Conflict(f"A file with the name '{file_name}' already exists in the directory.")

            # Save in DB first
            file_id = db_helper.execute_and_get_id(queries.V2_INSERT_FILE, file_name, current_saved_file_path, collection_id, '')
            if module_name == 'docguide':
                # Save the file in the docguide_files table
                db_helper.execute(queries.INSERT_DOCGUIDE_FILES, file_name, organization_id, file_id)

            file.save(current_saved_file_path)

        elif 'url' in request.form:
            # Download the content from the URL and save it to the data/unprocessed folder
            url = request.form['url']
            parsed_url = urlparse(url)

            # Reconstruct the URL without query string
            url = parsed_url.scheme + "://" + parsed_url.netloc + parsed_url.path
            response = requests.get(url)
            if response.status_code != 200:
                raise RuntimeError("Failed to download the file from the provided URL.")
            file_content = response.content
            file_name = os.path.basename(url)

            file_extension = file_name.split('.')[-1]
            file_supported = FileSupported.is_extension_supported(module_name, file_extension)
            if not file_supported:
                raise RuntimeError(f"File type {file_extension} is not supported for module {module_name}")

            current_saved_file_path = os.path.join(str(files_path), str(file_name))

            # Check if file already exists
            if os.path.exists(current_saved_file_path):
                raise Conflict(f"A file with the name '{file_name}' already exists in the directory.")

            # Save in DB first
            file_id = db_helper.execute_and_get_id(queries.V2_INSERT_FILE, file_name, current_saved_file_path, collection_id, '')
            if module_name == 'docguide':
                # Save the file in the docguide_files table
                db_helper.execute(queries.INSERT_DOCGUIDE_FILES, file_name, organization_id, file_id)

            with open(current_saved_file_path, 'wb') as f:
                f.write(file_content)
        else:
            raise RuntimeError('Please attach a file or url to process!')

    except Conflict as e:
        logger.error(e)
        raise e
    except Exception as e:
        logger.error(e)
        raise e

def file_get_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        file_ids = request.args.get('file_ids')
        if file_ids:
            file_ids = [int(file_id) for file_id in file_ids.split(',')]
        if not file_ids or not isinstance(file_ids, list):
            raise RuntimeError('File ids to be downloaded not found!')

        # Find files by file_ids
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        if not files:
            raise RuntimeError('Files not found!')

        file_paths = []
        for file in files:
            folders_path = os.path.join(config.ORGDIR_PATH, organization_name)
            file_path = os.path.join(folders_path, file['file_name'])
            if not os.path.exists(file_path):
                raise RuntimeError(f"File {file['file_name']} not found!")
            file_paths.append(file_path)

        if len(file_paths) == 1:
            # Send a single file
            response = make_response(send_file(file_paths[0], as_attachment=True))
            response.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_paths[0])}"'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response
        else:
            # Create a zip file for multiple files
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
                for file_path in file_paths:
                    zip_file.write(file_path, os.path.basename(file_path))
            zip_buffer.seek(0)
            response = make_response(send_file(zip_buffer, as_attachment=True, mimetype='application/zip'))
            response.headers['Content-Disposition'] = 'attachment; filename="files.zip"'
            response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
            return response

    except Exception as e:
        print(e)
        return jsonify({'message': str(e), 'error': str(e)}), 500

def files_get_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.args.get('collection_id')
        collection_name = request.args.get('collection_name')
        if not collection_id:
            raise RuntimeError('Collection Id is required!')
        # Fetch file_ids as a list of dictionaries
        file_rows = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID, collection_id, organization_id)
        if not file_rows or not isinstance(file_rows, list):
            raise RuntimeError('File ids to be downloaded not found!')

        # Extract file_ids from the result set
        file_ids = [row['file_id'] for row in file_rows if 'file_id' in row]
        if not file_ids:
            raise RuntimeError('File ids to be downloaded not found!')

        # Find files by file_ids
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        if not files:
            raise RuntimeError('Files not found!')

        file_paths = []
        for file in files:
            folders_path = os.path.join(config.ORGDIR_PATH, organization_name)
            file_path = os.path.join(folders_path, file['file_name'])
            if not os.path.exists(file_path):
                raise RuntimeError(f"File {file['file_name']} not found!")
            file_paths.append(file_path)

        # Create a zip file for multiple files
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for file_path in file_paths:
                zip_file.write(file_path, os.path.basename(file_path))
        zip_buffer.seek(0)
        response = make_response(send_file(zip_buffer, as_attachment=True, mimetype='application/zip', download_name=f'{collection_name}.zip'))
        response.headers['Content-Disposition'] = 'attachment; filename="'+collection_name+'.zip"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response

    except Exception as e:
        print(e)
        return jsonify({'message': str(e), 'error': str(e)}), 500

def file_delete_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        file_ids = request.json.get('file_ids')
        if not file_ids or not isinstance(file_ids, list):
            raise RuntimeError('File ids to be deleted not found!')
        # files = find_files_by_file_ids(file_ids)
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        if not files:
            raise RuntimeError('Files not found!')
        for file in files:
            folders_path = os.path.join(config.ORGDIR_PATH, organization_name)
            file_path = os.path.join(folders_path, file['file_name'])
            if os.path.exists(file_path):
                os.remove(file_path)  # Remove the existing file

        # Convert file_ids to a format suitable for SQL IN clause
        file_ids = tuple(file_ids)

        #first delete all the bm25 entries for these files
        db_helper.execute(queries.DELETE_BM25_TERMS_FOR_FILE, file_ids)
        db_helper.execute(queries.DELETE_BM25_AVG_DOC_LENGTH, file_ids)
        db_helper.execute(queries.DELETE_BM25_TOKENS, file_ids)

        db_helper.execute(queries.DELETE_FILES_BY_FILE_ID, file_ids)
        db_helper.execute(queries.DELETE_FILES_METADATA_BY_FILE_ID, file_ids)
        db_helper.execute(queries.DELETE_FILES_METADATA_PLUS_BY_FILE_ID, file_ids)

    except Exception as e:
        print(e)
        raise e


def get_organization_name_from_organization_id(organization_id):
    try:
        # organization = find_organization_by_organization_id(organization_id)
        organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_ORGANIZATION_ID, organization_id)
        if organization:
            return organization['org_name']
        else:
            raise RuntimeError("Organization not found!")
    except Exception as e:
        print(e)
        raise e
