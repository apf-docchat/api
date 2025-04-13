import json
import logging
import os
import re

from flask import Blueprint, render_template, session, jsonify, request
from llama_index import SimpleDirectoryReader
from openai import OpenAI

from source.legacy.utilities.helper_functions import generic_query, get_connection, get_files_for_collection_and_org, \
    get_org_id_by_name, get_collection_id_by_name, get_metadata_prompt, set_custom_instructions, \
    set_metadata_prompt
from source.legacy.utilities.openai_calls import callai
from source.common import config

""" from llama_index import (
    VectorStoreIndex,
    StorageContext,
    ServiceContext,
    OpenAIEmbedding,
    PromptHelper,
    load_index_from_storage,
    get_response_synthesizer,
    DocumentSummaryIndex
) """

#import logging
#import sys
""" from llama_index.llms import OpenAI
from llama_index.text_splitter import SentenceSplitter
from llama_index import set_global_service_context
from llama_index.node_parser import SimpleNodeParser


from llama_index.extractors import (
    SummaryExtractor,
    QuestionsAnsweredExtractor,
    TitleExtractor,
    KeywordExtractor,
    EntityExtractor,
    BaseExtractor,
)
from llama_index.text_splitter import TokenTextSplitter
from llama_index.ingestion import IngestionPipeline """


filewizard = Blueprint('filewizard', __name__, template_folder='templates')

logger = logging.getLogger('app')

_client = OpenAI(
        api_key=config.OPENAI_API_KEY
    )

#From the list of files given, return only files which don't have the metadata populated in the DB
def list_files_without_metadata(org_name, file_names):
    print(json.dumps(file_names))
    # Connect to the database
    connection = get_connection()

    missing_files = []

    try:
      with connection.cursor() as cursor:
        org_id = get_org_id_by_name(org_name)
        if org_id is None:
                raise ValueError("Organization not found")

        # Query to check if file_id exists in files_metadata table
        query = f"""
            SELECT DISTINCT f.file_name
            FROM files f
            JOIN files_metadata fm ON f.file_id = fm.file_id
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """

        cursor.execute(query, (org_id,))
        result = cursor.fetchall()
        files_in_metadata = [row[0] for row in result]

    finally:
        connection.close()

    # Return file names that are in file_names but not in files_in_metadata
    missing_files = [name for name in file_names if name not in files_in_metadata]

    return missing_files

def insert_file_metadata(org_id, filename, title, summary_short, summary_long):
    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch file_id from files table
            query = f"""
            SELECT f.file_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND f.file_name = %s
            """
            cursor.execute(query, (org_id, filename))
            file = cursor.fetchone()
            if file is None:
                raise ValueError(f"No file found with filename: {filename}")

            file_id = file[0]

            # Insert into files_metadata
            insert_query = """
            INSERT INTO files_metadata (file_id, file_name, title, summary_short, summary_long)
            VALUES (%s, %s, %s, %s, %s)
            """
            cursor.execute(insert_query, (file_id, filename, title, summary_short, summary_long))
            connection.commit()

            print(f"Metadata for '{filename}' inserted successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

def update_file_metadata(org_id, filename, title, summary_short, summary_long):
    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch file_id from files table
            query = f"""
            SELECT f.file_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND f.file_name = %s
            """
            cursor.execute(query, (org_id, filename))
            file = cursor.fetchone()
            if file is None:
                raise ValueError(f"No file found with filename: {filename}")

            file_id = file[0]

            # Update files_metadata
            update_query = """
            UPDATE files_metadata
            SET title = %s, summary_short = %s, summary_long = %s
            WHERE file_id = %s
            """
            cursor.execute(update_query, (title, summary_short, summary_long, file_id))
            connection.commit()

            if cursor.rowcount == 0:
                print(f"No metadata was updated for '{filename}'.")
            else:
                print(f"Metadata for '{filename}' updated successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()


def insert_file_metadata_plus(org_id, filename, metadata):
    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch file_id from files table
            query = f"""
            SELECT f.file_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND f.file_name = %s
            """
            cursor.execute(query, (org_id, filename))
            file = cursor.fetchone()
            if file is None:
                raise ValueError(f"No file found with filename: {filename}")

            file_id = file[0]

            # Insert into files_metadata
            insert_query = """
            INSERT INTO files_metadata_plus (file_id, metadata)
            VALUES (%s, %s)
            """
            cursor.execute(insert_query, (file_id, metadata))
            connection.commit()

            print(f"Metadata for '{filename}' inserted successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()

def update_file_metadata_plus(org_id, filename, metadata):
    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Fetch file_id from files table
            query = f"""
            SELECT f.file_id
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND f.file_name = %s
            """
            cursor.execute(query, (org_id, filename))
            file = cursor.fetchone()
            if file is None:
                raise ValueError(f"No file found with filename: {filename}")
            else:
                file_id = file[0]

                # Update files_metadata_plus
                update_query = """
                UPDATE files_metadata_plus
                SET metadata = %s
                WHERE file_id = %s
                """
                cursor.execute(update_query, (metadata, file_id))
                connection.commit()

                if cursor.rowcount == 0:
                    #print(f"No metadata was updated for '{filename}'.")
                    insert_file_metadata_plus(org_id, filename, metadata)
                else:
                    print(f"Metadata for '{filename}' updated successfully.")

    except Exception as e:
        print(f"An error occurred: {e}")
    finally:
        connection.close()


def clean_str_for_json_loads(string_var):
  string_var = string_var.replace('\u20b9', 'INR')
  #string_var = string_var.replace("'", "\'")
  #string_var = string_var.replace('\n', '\\n')
  #string_var = string_var.replace('\r', '\\r')
  #string_var = string_var.replace('’', "\'")
  # Find the first occurrence of '{'
  start_index = string_var.find('{')
  # Find the last occurrence of '}'
  end_index = string_var.rfind('}')

  # Check if both '{' and '}' are found
  if start_index != -1 and end_index != -1:
      # Extract the part from the first '{' to the last '}'
      return string_var[start_index:end_index + 1]
  else:
      # If either '{' or '}' is not found, return the original string or handle it as needed
      return string_var

#From the list of files given, return only files which don't have the metadata populated in the DB
def list_files_without_metadata_plus(org_name, file_names):
    #print(json.dumps(file_names))
    # Connect to the database
    connection = get_connection()

    missing_files = []

    try:
      with connection.cursor() as cursor:
        org_id = get_org_id_by_name(org_name)
        if org_id is None:
                raise ValueError("Organization not found")

        # Query to check if file_id exists in files_metadata table
        query = f"""
            SELECT DISTINCT f.file_name
            FROM files f
            JOIN files_metadata_plus fmp ON f.file_id = fmp.file_id
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            WHERE oc.org_id = %s
            """

        cursor.execute(query, (org_id,))
        result = cursor.fetchall()
        files_in_metadata = [row[0] for row in result]

    finally:
        connection.close()

    # Return file names that are in file_names but not in files_in_metadata
    missing_files = [name for name in file_names if name not in files_in_metadata]

    return missing_files

def callai_summarize(full_content):
    if (len(full_content) < config.MAX_TOKENS):  #roughly a context window of 100000 tokens assuming gpt4-turbo
        system_content = "Context:\n" + full_content
        previous_messages = []
        user_content = "For the text given in the Context, provide a strictly formatted JSON value with following values:\n1. 'title' which has a sutiable title for the file\n2. 'summary_short' which clearly describes what the text in the Context is about in 50 words\n3. 'summary_long' which is a summary in 400 words, which has all the important details like names, financials and facts included. Don't say that something is there in the document, instead mention the fact in the summary using as few words as possible. Pack in all the facts or propositions that can be packed into 400 words.\nAlso escape all control characters including the newline character."
        repeat_count = 2
        [response, error] = callai(system_content, previous_messages, user_content, repeat_count, "admin")
        response = response.choices[0].message.content
    else:
        iter_count = (len(full_content) // config.MAX_TOKENS) + 1
        summary_tillnow = ''
        for i in range(iter_count):
            # Calculate start index for slicing the content
            start_index = i * config.MAX_TOKENS

            # Calculate end index, ensuring it doesn't exceed the length of system_content
            end_index = min(start_index + config.MAX_TOKENS, len(full_content))

            # Slice the full_content to get the current chunk
            system_content = "Context:\n" + summary_tillnow + '\n' + full_content[start_index:end_index]
            previous_messages = []
            user_content = "Provide a summary of the text in Context in 2000 words, which has all the important details like names, financials and facts included. Don't say that something is there in the document, instead mention the fact in the summary using as few words as possible. Pack in all the facts or propositions that can be packed into 400 words.\n"
            repeat_count = 2
            [response, error] = callai(system_content, previous_messages, user_content, repeat_count, "admin")
            summary_tillnow = response.choices[0].message.content
        system_content = "Context:\n" + summary_tillnow
        previous_messages = []
        user_content = "For the text given in the Context, provide a strictly formatted JSON value with following values:\n1. 'title' which has a sutiable title for the file\n2. 'summary_short' which clearly describes what the text in the Context is about in 50 words\n3. 'summary_long' which is a summary in 400 words, which has all the important details like names, financials and facts included. Don't say that something is there in the document, instead mention the fact in the summary using as few words as possible. Pack in all the facts or propositions that can be packed into 400 words.\nAlso escape all control characters including the newline character."
        repeat_count = 2
        [response, error] = callai(system_content, previous_messages, user_content, repeat_count, "admin")
        response = response.choices[0].message.content
    return response

@filewizard.route('/filewizard', methods=['POST'])
def filewizard_script():
  return render_template('filewizard.html',active_page='/filewizard',
        modules=session.get('modules', []))

@filewizard.route('/getcustominstructions', methods=['POST'])
def getcustominstructions():
  selected_collection = request.form.get("collection","")
  orgname = session.get("orgname", "")
  collection_id = get_collection_id_by_name(orgname, selected_collection)
  custom_instructions = generic_query('collections', 'custom_instructions', {"collection_id": collection_id})
  print(custom_instructions)
  return jsonify({"custom_instructions":custom_instructions[0][0]})

@filewizard.route('/summarize', methods=['POST'])
def summarize():
    #basic llamaindex setup
    """ llm = OpenAI(model=config.LLM_MODEL, temperature=0.1, max_tokens=4096)
    service_context = ServiceContext.from_defaults(llm=llm, chunk_size=1024)
    response_synthesizer = get_response_synthesizer(
        response_mode="tree_summarize", use_async=True) """

    orgname = session.get("orgname", "")
    org_id = get_org_id_by_name(orgname)
    selected_collection = request.form.get("collection","")
    print(selected_collection)
    selected_filenames = get_files_for_collection_and_org(selected_collection, orgname)
    selected_filenames = [item['filename'] for item in selected_filenames]
    print(json.dumps(selected_filenames))
    filenames = list_files_without_metadata(orgname,selected_filenames)
    print(json.dumps(filenames))
    # Process each document separately
    doc_summaries = []
    for filename in filenames:
        #print(f"Processing collection: {subfolder} File: {filename}")
        file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, filename)
        # Assuming each file is a document
        documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

        full_content = ""
        for d in documents:
            full_content +=  d.get_text()
        print(len(full_content))
        response = callai_summarize(full_content)

        #print(response.choices[0].message.content)
        response =  re.sub(r'```json', '', response, count=1)
        response =  re.sub(r'```', '', response, count=1)
        response = clean_str_for_json_loads(response)
        response_json = json.loads(response)
        insert_file_metadata(org_id, filename, response_json.get('title',""), response_json.get('summary_short',""), response_json.get('summary_long',""))
        doc_summaries.append(response_json)

    return jsonify({"status": "success","summary":doc_summaries})

@filewizard.route('/summaryupdate', methods=['POST'])
def summary_update():

  orgname = session.get("orgname", "")
  org_id = get_org_id_by_name(orgname)
  selected_collection = request.form.get("collection","")
  selected_filenames = get_files_for_collection_and_org(selected_collection, orgname)
  selected_filenames = [item['filename'] for item in selected_filenames]
  #filenames = list_files_without_metadata(orgname,selected_filenames)
  filenames = selected_filenames #update for all files and ignore current summaries
  # Process each document separately
  doc_summaries = []
  for filename in filenames:
    #print(f"Processing collection: {subfolder} File: {filename}")
    file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, filename)
    # Assuming each file is a document
    documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

    full_content = ""
    for d in documents:
        full_content +=  d.get_text()
    print(len(full_content))
    response = callai_summarize(full_content)

    #print(response.choices[0].message.content)
    response =  re.sub(r'```json', '', response, count=1)
    response =  re.sub(r'```', '', response, count=1)
    response = clean_str_for_json_loads(response)
    response_json = json.loads(response)
    update_file_metadata(org_id, filename, response_json.get('title',""), response_json.get('summary_short',""), response_json.get('summary_long',""))
    doc_summaries.append(response_json)

  return jsonify({"status": "success","summary":doc_summaries})

@filewizard.route('/getsamplesummary', methods=['POST'])
def get_sample_summary():
    org_id = get_org_id_by_name(session.get('orgname', ""))
    data = request.form
    collection = data.get('collection')

    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            sql = """
            SELECT summary_short, summary_long AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            JOIN files_metadata fm ON fm.file_id = f.file_id
            WHERE oc.org_id = %s AND c.collection_name = %s
            """
            cursor.execute(sql, (org_id, collection))
            files_with_metadata_result = cursor.fetchone()
            if files_with_metadata_result:
                return jsonify({"summary_short": files_with_metadata_result[0], "summary_long": files_with_metadata_result[1]})
            else:
                return jsonify({"summary_short": '', "summary_long": ''})
    finally:
        connection.close()

@filewizard.route('/checkstatus', methods=['POST'])
def check_status():
    org_id = get_org_id_by_name(session.get('orgname', ""))
    data = request.form
    collection = data.get('collection')
    type = data.get('type')

    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            # Query to count total files in the collection
            query_total_files = f"""
            SELECT COUNT(*) AS total
            FROM files f
            JOIN files_collections fc ON f.file_id = fc.file_id
            JOIN organization_collections oc ON fc.collection_id = oc.collection_id
            JOIN collections c ON c.collection_id = oc.collection_id
            WHERE oc.org_id = %s AND c.collection_name = %s
            """
            cursor.execute(query_total_files, (org_id, collection))
            total_files_result = cursor.fetchone()
            total_files = total_files_result[0] if total_files_result else 0

            if(type == 'summarise'):
                # Query to count files with metadata
                query_files_with_metadata = """
                SELECT COUNT(*) AS total
                FROM files f
                JOIN files_collections fc ON f.file_id = fc.file_id
                JOIN organization_collections oc ON fc.collection_id = oc.collection_id
                JOIN collections c ON c.collection_id = oc.collection_id
                JOIN files_metadata fm ON fm.file_id = f.file_id
                WHERE oc.org_id = %s AND c.collection_name = %s
                """
                cursor.execute(query_files_with_metadata, (org_id, collection))
                files_with_metadata_result = cursor.fetchone()
                files_with_metadata = files_with_metadata_result[0] if files_with_metadata_result else 0
            elif(type == 'metadata'):
                # Query to count files with metadata
                query_files_with_metadata_plus = """
                SELECT COUNT(*) AS total
                FROM files f
                JOIN files_collections fc ON f.file_id = fc.file_id
                JOIN organization_collections oc ON fc.collection_id = oc.collection_id
                JOIN collections c ON c.collection_id = oc.collection_id
                JOIN files_metadata_plus fmp ON fmp.file_id = f.file_id
                WHERE oc.org_id = %s AND c.collection_name = %s
                """
                cursor.execute(query_files_with_metadata_plus, (org_id, collection))
                files_with_metadata_result = cursor.fetchone()
                files_with_metadata = files_with_metadata_result[0] if files_with_metadata_result else 0

    finally:
        connection.close()

    # Prepare and send the JSON response
    response = {
        'total_files': total_files,
        'files_with_metadata': files_with_metadata
    }
    return jsonify(response)

@filewizard.route('/download', methods=['POST'])
def download_csv():
    orgname = session.get('orgname')  # Fetch orgname from session
    collection = request.form.get('collection')  # Fetch collection from POST request
    type = request.form.get('type')  # Fetch collection from POST request
    org_id = get_org_id_by_name(orgname)
    # Connect to the database
    connection = get_connection()

    try:
        with connection.cursor() as cursor:
            if (type == 'summarise'):
                # SQL query to join and fetch the required data
                query = """
                SELECT fm.file_name, fm.title, fm.summary_short, fm.summary_long
                FROM files_metadata fm
                JOIN files f ON fm.file_id = f.file_id
                JOIN files_collections fc ON fc.file_id = f.file_id
                JOIN collections c ON fc.collection_id = c.collection_id
                JOIN organization_collections oc ON oc.collection_id = fc.collection_id
                JOIN organization o ON o.org_id = oc.org_id
                WHERE o.org_id = %s AND c.collection_name = %s
                """
                cursor.execute(query, (org_id, collection))
                result = cursor.fetchall()

                # Format data for CSV conversion
                data = [{"file_name": row[0], "title": row[1], "summary_short": row[2], "summary_long": row[3]} for row in result]
            elif(type == 'metadata'):
                # SQL query to join and fetch the required data
                query = """
                SELECT f.file_name, fmp.metadata
                FROM files_metadata_plus fmp
                JOIN files f ON fmp.file_id = f.file_id
                JOIN files_collections fc ON fc.file_id = f.file_id
                JOIN collections c ON fc.collection_id = c.collection_id
                JOIN organization_collections oc ON oc.collection_id = fc.collection_id
                JOIN organization o ON o.org_id = oc.org_id
                WHERE o.org_id = %s AND c.collection_name = %s
                """
                cursor.execute(query, (org_id, collection))
                result = cursor.fetchall()

                # Format data for CSV conversion
                data = [{"file_name": row[0], "metadata": row[1]} for row in result]

    finally:
        connection.close()

    return jsonify(data)

@filewizard.route('/getmetadataprompt', methods=['POST'])
def getmetadataprompt():
  selected_collection = request.form.get("collection","")
  orgname = session.get("orgname", "")
  collection_id = get_collection_id_by_name(orgname, selected_collection)
  metadata_prompt = get_metadata_prompt(collection_id, False) #false as prelude not needed, only metadata field list
  return jsonify(metadata_prompt)

@filewizard.route('/metadatasave', methods=['POST'])
def save_metadata():
    data = request.json
    metadata_prompt = data['content']
    selected_collection = data['collection']
    orgname = session.get("orgname", "")
    collection_id = get_collection_id_by_name(orgname, selected_collection)
    set_metadata_prompt(metadata_prompt, collection_id)
    return jsonify({"status": "success", "message": "Data saved successfully"})

@filewizard.route('/savecustominstructions', methods=['POST'])
def savecustominstructions():
    data = request.json
    custom_instructions = data['content']
    selected_collection = data['collection']
    orgname = session.get("orgname", "")
    collection_id = get_collection_id_by_name(orgname, selected_collection)
    set_custom_instructions(custom_instructions, collection_id)
    return jsonify({"status": "success", "message": "Data saved successfully"})

@filewizard.route('/populatemetadata', methods=['POST'])
def populatemetadata():

  orgname = session.get("orgname", "")
  org_id = get_org_id_by_name(orgname)
  selected_collection = request.form.get("collection","")
  collection_id = get_collection_id_by_name(orgname, selected_collection)
  #print(selected_collection)
  selected_filenames = get_files_for_collection_and_org(selected_collection, orgname)
  selected_filenames = [item['filename'] for item in selected_filenames]
  #print(json.dumps(selected_filenames))
  filenames = list_files_without_metadata_plus(orgname,selected_filenames)
  #print(json.dumps(filenames))

  # Process each document separately
  user_content = get_metadata_prompt(collection_id, True)  #true as prelude also needed along with metadata field list
  for filename in filenames:
      #print(f"Processing collection: {subfolder} File: {filename}")
      file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, filename)
      # Assuming each file is a document
      documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

      system_content = "Context:\n"
      for d in documents:
        system_content +=  d.get_text()
      previous_messages = []
      #user_content = get_metadata_prompt(collection_id, True) moved above outside loop to reduce DB calls
      repeat_count = 2
      [response, error] = callai(system_content, previous_messages, user_content, repeat_count, "admin")
      response = response.choices[0].message.content

      #print(response.choices[0].message.content)
      response =  re.sub(r'```json', '', response, count=1)
      response =  re.sub(r'```', '', response, count=1)
      #print(response)
      response = clean_str_for_json_loads(response)
      print(response)
      insert_file_metadata_plus(org_id, filename, response)

  return jsonify({"status": "success"})

@filewizard.route('/metadataupdate', methods=['POST'])
def metadataupdate():

  orgname = session.get("orgname", "")
  org_id = get_org_id_by_name(orgname)
  selected_collection = request.form.get("collection","")
  collection_id = get_collection_id_by_name(orgname, selected_collection)
  selected_filenames = get_files_for_collection_and_org(selected_collection, orgname)
  selected_filenames = [item['filename'] for item in selected_filenames]
  #filenames = list_files_without_metadata_plus(orgname,selected_filenames)
  filenames = selected_filenames #update has to be done for all files

  # Process each document separately
  user_content = get_metadata_prompt(collection_id, True)  #true as prelude also needed along with metadata field list
  for filename in filenames:
      logger.error(f"Processing file: {filename}")
      file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, filename)
      # Assuming each file is a document
      documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

      system_content = "Context:\n"
      for d in documents:
        system_content +=  d.get_text()
      previous_messages = []
      #user_content = get_metadata_prompt(collection_id, True) moved above outside loop to reduce DB calls
      repeat_count = 2
      [response, error] = callai(system_content, previous_messages, user_content, repeat_count, "admin")
      response = response.choices[0].message.content

      logger.error(f"Summary received from LLM")
      response =  re.sub(r'```json', '', response, count=1)
      response =  re.sub(r'```', '', response, count=1)
      #print(response)
      response = clean_str_for_json_loads(response)
      update_file_metadata_plus(org_id, filename, response)
      logger.error(f"Metadata update for the file completed")

  return jsonify({"status": "success"})
