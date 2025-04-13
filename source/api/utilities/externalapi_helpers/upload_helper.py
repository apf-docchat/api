import logging
from io import StringIO

import pandas as pd
from flask import request

from source.api.utilities import db_helper, queries

logger = logging.getLogger('app')


def upload_metadata_file():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')

        organization_id = request.context['organization_id']
        collection_id = request.json.get('collection_id')

        if 'file' not in request.files:
            raise RuntimeError('No file part in the request!')

        file = request.files['file']
        if file.filename == '':
            raise RuntimeError('No file selected!')

        if not file.filename.lower().endswith('.csv'):
            raise RuntimeError('File must be a CSV!')

        csv_content = file.read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))

        if 'file_id' not in df.columns:
            return RuntimeError('file_id column not found in CSV!')

        csv_values = df.set_index('file_id').to_dict('index')

        metadata = db_helper.find_many(queries.FIND_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        metadata_values = {}
        for _doc in metadata:
            metadata_values.setdefault(_doc['file_id'], {})[_doc['field']] = _doc['value']

        updates = []

        for file_id, _obj in metadata_values.items():
            for field, value in _obj.items():
                if field == 'file_name':
                    continue

                if csv_values[file_id][field] != value:
                    updates.append((value, organization_id, collection_id, file_id, field))

        if updates:
            db_helper.execute_many(SET_VALUE_IN_DOCCHAT_METADATA, updates)

    except Exception as e:
        logger.error(e)
        raise e



SET_VALUE_IN_DOCCHAT_METADATA = """
    UPDATE docchat_metadata
    SET value = %s
    WHERE organization_id = %s AND collection_id = %s AND file_id = %s AND field = %s
"""

INSERT_IN_DOCCHAT_METADATA = """
    INSERT INTO docchat_metadata (organization_id, collection_id, file_id, field, value)
    VALUES (%s, %s, %s, %s, %s)
"""