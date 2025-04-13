# Run this program after ensuring that Vector DB is up to date (either through automatic pw-backend service or via run_manual python script inside vectorizer)
#This script will rebuild the MySQL DB needed for the pw-api frontend to match with Vector DB. It will not delete the existing files in the DB for safety purposes. So please delete the files and files_collections entries from DB manually. Then run this script. It will rebuild from Pinecone.

from pinecone import Pinecone
from source.common import config
from source.api.utilities.helper_functions import get_connection

# Pinecone setup
pinecone_api_key = config.PINECONE_API_KEY
pinecone_index_name = config.PINECONE_INDEX_NAME
pc = Pinecone(api_key=pinecone_api_key)
index = pc.Index(pinecone_index_name)

def get_vector_metadata():
    # Fetch all vector metadata from Pinecone
    query_results = index.query(vector=[0]*1536, include_metadata=True, include_values=False, top_k=10000)
    return query_results['matches']

def process_file(filename, collection):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            # Check if file already exists in 'files' table
            cur.execute("SELECT file_id FROM files WHERE file_name = %s", (filename,))
            file_id = cur.fetchone()

            if not file_id:
                # Insert file into 'files' table
                cur.execute("INSERT INTO files (file_name) VALUES (%s)", (filename,))
                print("inserted file: " + filename)
                file_id = cur.lastrowid
                conn.commit()


                # Find collection_id from 'collections' table
                cur.execute("SELECT collection_id FROM collections WHERE collection_name = %s", (collection,))
                collection_id = cur.fetchone()

                if collection_id:
                    # Insert file and collection relationship into 'files_collections' table
                    cur.execute("INSERT INTO files_collections (file_id, collection_id) VALUES (%s, %s)",
                                (file_id, collection_id[0]))
                    conn.commit()
                    print("added " + filename + " to collection: " + collection)
    finally:
        conn.close()

metadata = get_vector_metadata()
for data in metadata:
    filename = data['metadata'].get('filename')
    collection = data['metadata'].get('collection', [])
    if filename:
        process_file(filename, collection)
