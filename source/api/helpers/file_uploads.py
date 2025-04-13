import logging
import os
from tempfile import NamedTemporaryFile
from urllib.parse import urlparse

import requests
from flask import Request
from sqlalchemy import select
from werkzeug.datastructures import ImmutableMultiDict, FileStorage
from werkzeug.exceptions import Conflict
from werkzeug.utils import secure_filename

from source.common.app_config import config
from source.common.flask_sqlachemy import db
from source.common.helpers.collections import get_collection, get_module_name_for_collection
from source.common.helpers.orgstorage import OrgStorage
from source.common.helpers.vectorizer import vectorizer_populate_general_metadata, vectorizer_vectorize
from source.common.models.models import Collection, DocguideFile, File
from source.common.utils.check_mimetype import check_mimetype_matches_declared

logger = logging.getLogger('app')


def save_file_to_collection(collection_id: str, filename_original: str, file_content: bytes) -> str:
    collection_id = int(collection_id)
    collection = get_collection(collection_id)

    org_id = str(collection.org_id)

    storage_filename = secure_filename(filename_original)

    with OrgStorage.fs(org_id).open(storage_filename, 'wb') as f:
        f.write(file_content)

    stored_file_path = os.path.join(storage_filename)

    try:
        # Create new File object
        new_file = File(
            file_name=filename_original,
            file_path=stored_file_path,
            collection_id=collection_id
        )
        db.session.add(new_file)
        db.session.commit()
        return str(new_file.file_id)
    except Exception as e:
        # Remove file since DB insert failed
        if OrgStorage.fs(org_id).exists(storage_filename):
            OrgStorage.fs(org_id).rm(storage_filename)
        raise e


def _upload_flask_file_to_collection(collection_id: str, file: FileStorage) -> tuple[str, str]:
    if not file.filename:
        raise RuntimeError("'filename' is not present in the request")

    filename_original = file.filename

    # Get declared MIME type from FileStorage
    declared_mime_type = file.content_type

    # Read content and validate MIME type
    file_content = file.read()

    check_mimetype_matches_declared(file_content, declared_mime_type)

    # check_module_supports_mimetype(module_name, declared_mime_type)

    # Reset file pointer after reading
    file.seek(0)

    # Generate safe filename
    filename_safe = secure_filename(filename_original)

    uploaded_file_id = save_file_to_collection(collection_id, filename_safe, file_content)

    return filename_safe, uploaded_file_id


FlaskFiles = ImmutableMultiDict[str, FileStorage]


def upload_files_from_flask_request(collection_id: str, files: FlaskFiles) -> list[tuple[str, str]]:
    files_list = files.getlist('file')
    results = []

    for file in files_list:
        file_name, uploaded_file_id = _upload_flask_file_to_collection(collection_id, file)
        results.append((file_name, uploaded_file_id))

    return results


def upload_file_from_url(collection_id: str, url: str) -> tuple[str, str]:
    # Validate URL scheme
    parsed_url = urlparse(url)
    if parsed_url.scheme not in ['http', 'https']:
        raise ValueError("Unsupported URL scheme")

    # Use a session for better connection management
    with requests.Session() as session:
        session.headers.update({'User-Agent': config.get('app.user_agent')})

        # Set a reasonable timeout and stream the response
        response = session.get(url, timeout=30, stream=True)
        response.raise_for_status()  # Raises HTTPError for bad status codes

        # Get declared MIME type from Content-Type header
        declared_mime_type = response.headers.get('content-type', '').split(';')[0].strip()

        # Buffer first chunk for MIME detection
        chunk_iterator = response.iter_content(chunk_size=8192)
        first_chunk = next(chunk_iterator, None)

        if not first_chunk:
            raise ValueError("Empty file")

        # Validate MIME type
        check_mimetype_matches_declared(first_chunk, declared_mime_type)

        # check_module_supports_mimetype(module_name, declared_mime_type)

        # Get filename from Content-Disposition header if available
        content_disposition = response.headers.get('content-disposition')
        if content_disposition and 'filename=' in content_disposition:
            filename_original = content_disposition.split('filename=')[1].strip('"\'')
        else:
            filename_original = os.path.basename(url)

        # Sanitize file name
        filename_safe = secure_filename(filename_original)

        # Download file to temp file
        with NamedTemporaryFile(delete=False) as temp_file:
            temp_file.write(first_chunk)

            total_size = len(first_chunk)

            # Stream remaining chunks
            for chunk in chunk_iterator:
                if chunk:
                    # Check if the file size exceeds the maximum limit
                    total_size += len(chunk)
                    if total_size > config.MAX_UPLOAD_FILE_SIZE_MB * 1024 * 1024:
                        # Clean up temp file before raising error
                        temp_file.close()
                        os.unlink(temp_file.name)
                        raise ValueError(f"File size exceeds the maximum limit of {config.MAX_UPLOAD_FILE_SIZE_MB} MB")

                    # Write the chunk to temp file
                    temp_file.write(chunk)

            try:
                # Upload the temp file to storage
                uploaded_file_id = save_file_to_collection(collection_id, filename_safe, temp_file.read())
            finally:
                # Clean up temp file
                temp_file.close()
                os.unlink(temp_file.name)

    return filename_safe, uploaded_file_id


def handle_file_upload(request: Request):
    try:
        # Get collection and module info
        collection_id = request.args.get('collection_id')

        collection = db.session.execute(select(Collection).where(Collection.collection_id == collection_id)).first()

        # TODO: SECURITY RISK, need to check if user has access to this collection

        if not collection:
            raise RuntimeError("Collection not found!")

        uploaded_files = []

        # Handle direct file upload or download from URL
        if request.files:
            uploaded_files = upload_files_from_flask_request(collection_id, request.files)
        elif 'url' in request.form:
            uploaded_files.append(upload_file_from_url(collection_id, request.form['url']))
        else:
            raise RuntimeError('Please attach a file or url to process!')

        module_name = get_module_name_for_collection(collection_id)

        org_id = collection.org_id

        if module_name == 'docguide':
            for file_name, file_id in uploaded_files:
                docguide_file = DocguideFile(
                    file_name=file_name,
                    org_id=org_id,
                    doc_file_id=file_id
                )
                db.session.add(docguide_file)
            db.session.commit()

        # Vectorize files
        for file_name, file_id in uploaded_files:
            vectorizer_vectorize(org_id, file_name)
            vectorizer_populate_general_metadata(org_id, file_name)

        return {'message': 'Files uploaded successfully'}, 200

    except Conflict as e:
        logger.error(e)
        raise e
    except Exception as e:
        logger.error(e)
        raise e
