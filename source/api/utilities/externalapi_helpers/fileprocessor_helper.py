import json
import logging
import os
import re
from io import StringIO

import pandas as pd
from flask import request
from llama_index import SimpleDirectoryReader

from source.api.utilities import db_helper, queries
# from source.api.utilities.externalapi_helpers import openai_helper
from source.api.utilities.constants import PortKeyConfigs
from source.api.endpoints.doc_chat.helpers import DocChatManager
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.api.utilities.vector_search import VectorSearch
from source.common import config

import fitz

logger = logging.getLogger('app')


def get_fileprocessor_content():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        content_type = request.context['content_type']
        collection_id = request.args.get("collection_id")

        if content_type == 'metadata':
            """ collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                            organization_id, collection_id) """
            collection = db_helper.find_one(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                            organization_id, collection_id)
            metadata_response = collection.get('metatadata_prompt')
            return metadata_response

        elif content_type == 'summarise':
            """ metadata = db_helper.find_one(queries.FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                          organization_id, collection_id) """
            metadata = db_helper.find_one(queries.V2_FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                          organization_id, collection_id)
            if not metadata:
                return {
                    "message": "Metadata not found!",
                    "file_name": None,
                    "title": None,
                    "summary_short": None,
                    "summary_long": None
                }

            metadata_response = {
                "file_name": metadata.get('file_name', 'Unknown File'),
                "title": metadata.get('title', 'No Title Available'),
                "summary_short": metadata.get('summary_short', 'No Short Summary Available'),
                "summary_long": metadata.get('summary_long', 'No Long Summary Available')
            }
            return metadata_response

    except Exception as e:
        print(e)
        raise e


def get_fileprocessor_status_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        status_type = request.context['status_type']
        collection_id = request.args.get("collection_id")

        #total_files_count = db_helper.find_one(queries.FIND_FILES_COUNT_BY_COLLECTION_ID_AND_ORGANIZATION_ID, organization_id, collection_id)
        total_files_count = db_helper.find_one(queries.V2_FIND_FILES_COUNT_BY_COLLECTION_ID_AND_ORGANIZATION_ID
                                               , organization_id, collection_id)
        total_files_count = total_files_count['total']

        if status_type == 'metadata':
            #total_processed_files_count = db_helper.find_one(queries.FIND_FILES_COUNT_OF_METADATA_PLUS_BY_COLLECTION_ID_AND_ORGANIZATION_ID, organization_id, collection_id)
            total_processed_files_count = db_helper.find_one(queries.V2_FIND_FILES_COUNT_OF_METADATA_PLUS_BY_COLLECTION_ID_AND_ORGANIZATION_ID, organization_id, collection_id)
            total_processed_files_count = total_processed_files_count['total']
            percentage = 0 if total_files_count == 0 else min(
                int((total_processed_files_count / total_files_count) * 100),
                100)
            return dict(total_files_count=total_files_count, total_processed_files_count=total_processed_files_count,
                        percentage_value=percentage, percentage_display_value=f'{percentage}%')

        elif status_type == 'summarise':
            #total_processed_files_count = db_helper.find_one(queries.FIND_FILES_COUNT_OF_METADATA_BY_COLLECTION_ID_AND_ORGANIZATION_ID, organization_id, collection_id)
            total_processed_files_count = db_helper.find_one(queries.V2_FIND_FILES_COUNT_OF_METADATA_BY_COLLECTION_ID_AND_ORGANIZATION_ID, organization_id, collection_id)
            total_processed_files_count = total_processed_files_count['total']
            percentage = 0 if total_files_count == 0 else min(
                int((total_processed_files_count / total_files_count) * 100),
                100)
            return dict(total_files_count=total_files_count, total_processed_files_count=total_processed_files_count,
                        percentage_value=percentage, percentage_display_value=f'{percentage}%')

    except Exception as e:
        print(e)
        raise e


def update_custom_instruction_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        collection_id = request.json.get("collection_id")
        custom_instruction = request.json.get("custom_instruction")
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        if not collection:
            raise RuntimeError("Collection not found!")
        response = db_helper.execute(queries.UPDATE_CUSTOM_INSTRUCTION_IN_COLLECTION, custom_instruction, collection_id)
        return response
    except Exception as e:
        print(e)
        raise e


def get_custom_instruction_helper():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        collection_id = request.args.get("collection_id")
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        if not collection:
            raise RuntimeError("Collection not found!")
        custom_instruction = collection.get('custom_instructions', '') or ''
        return custom_instruction
    except Exception as e:
        print(e)
        raise e

def generate_custom_instructions():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to generate custom instructions.")

        organization_id = int(request.context.get('organization_id'))
        collection_id = request.json.get('collection_id')

        logger.info(f"Generating custom instructions for collection id [{collection_id}]")

        if not collection_id:
            raise RuntimeError("Collection ID is required")

        # Get collection details including db_uri if exists
        collection = db_helper.find_one(
            queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
            organization_id, collection_id
        )

        if not collection:
            raise RuntimeError("Collection not found")

        orgname = db_helper.find_one(
            queries.FIND_ORGANIZATION_BY_ORGANIZATION_ID,
            organization_id
        ).get('org_name')

        # Get all files in the collection
        files = db_helper.find_many(
            queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
            collection_id,
            organization_id
        )

        instructions_data = []

        # Process PDF files
        for file in files:
            file_name = file.get('file_name')
            if not file_name:
                continue

            _, file_extension = os.path.splitext(file_name)
            file_extension = file_extension.lower()
            file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, file_name)

            if file_extension == '.pdf':
                pdf_content = ''
                doc = fitz.open(file_path)
                # Get first 2 pages for analysis
                for i in range(min(2, doc.page_count)):
                    page = doc.load_page(i)
                    pdf_content += page.get_text()
                doc.close()

                system_content = """
                Analyze the PDF content and provide a JSON response with the following fields:
                1. 'description': A detailed description of what this document contains and its purpose
                
                Example response:
                {
                    "description": "Comprehensive financial statements and analysis for fiscal year 2023, including balance sheets, income statements, and cash flow statements with detailed notes and auditor's remarks"
                }
                """

                openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_07)
                response = openai_helper.callai_json(system_content, pdf_content, 'admin')
                pdf_info = json.loads(response)
                instructions_data.append({
                    'type': 'pdf',
                    'file_name': file_name,
                    'description': pdf_info.get('description')
                })

            elif file_extension in ['.xlsx', '.xls', '.csv']:
                if file_extension == '.csv':
                    df = pd.read_csv(file_path)
                else:
                    df = pd.read_excel(file_path)

                columns_info = df.columns.tolist()
                sample_data = df.head(5).to_json(orient='records')

                system_content = """
                Analyze the spreadsheet columns and sample data to provide a JSON response with:
                1. 'description': Overall description of the spreadsheet's purpose
                2. 'columns': Array of objects with 'name' and 'description' for each column
                
                Example response:
                {
                    "description": "Daily record of customer transactions including purchase details and payment information",
                    "columns": [
                        {
                            "name": "transaction_date",
                            "description": "Date and time when the transaction occurred"
                        }
                    ]
                }
                """

                user_content = f"Columns: {columns_info}\nSample Data: {sample_data}"
                openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_07)
                response = openai_helper.callai_json(system_content, user_content, 'admin')
                sheet_info = json.loads(response)
                instructions_data.append({
                    'type': 'spreadsheet',
                    'file_name': file_name,
                    'description': sheet_info.get('description'),
                    'columns': sheet_info.get('columns', [])
                })

        # Process database if db_uri exists
        db_uri = collection.get('db_uri')
        if db_uri:
            if 'mysql' in db_uri.lower():
                # Parse MySQL connection string
                import pymysql
                import urllib.parse
                parsed = urllib.parse.urlparse(db_uri)
                connection = pymysql.connect(
                    host=parsed.hostname,
                    user=parsed.username,
                    password=parsed.password,
                    database=parsed.path.strip('/'),
                    port=parsed.port or 3306
                )

                with connection.cursor() as cursor:
                    cursor.execute("SHOW TABLES")
                    tables = cursor.fetchall()

                    for table in tables:
                        table_name = table[0]
                        cursor.execute(f"DESCRIBE {table_name}")
                        columns = cursor.fetchall()
                        columns_info = [{'name': col[0], 'type': col[1]} for col in columns]

                        system_content = """
                        Analyze the database table structure and provide a JSON response with:
                        1. 'description': Purpose and contents of this table
                        2. 'columns': Array of objects with 'name' and 'description' for each column
                        """

                        user_content = f"Table: {table_name}\nColumns: {columns_info}"
                        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_07)
                        response = openai_helper.callai_json(system_content, user_content, 'admin')
                        table_info = json.loads(response)

                        instructions_data.append({
                            'type': 'database_table',
                            'table_name': table_name,
                            'description': table_info.get('description'),
                            'columns': table_info.get('columns', [])
                        })

                connection.close()

            elif 'postgresql' in db_uri.lower():
                import psycopg

                schema_name = db_uri.split('/')[-1]
                db_uri_parts = db_uri.split('/')
                db_uri = '/'.join(db_uri_parts[:-1])

                with psycopg.connect(db_uri) as connection:
                    with connection.cursor() as cursor:
                        # Get all tables in the current schema
                        cursor.execute(f"""
                            SELECT table_name 
                            FROM information_schema.tables 
                            WHERE table_schema = '{schema_name}'
                        """)
                        tables = cursor.fetchall()

                        for table in tables:
                            table_name = table[0]
                            cursor.execute(f"""
                                SELECT column_name, data_type 
                                FROM information_schema.columns 
                                WHERE table_name = '{table_name}'""")
                            columns = cursor.fetchall()
                            columns_info = [{'name': col[0], 'type': col[1]} for col in columns]

                            system_content = """
                            Analyze the database table structure and provide a JSON response with:
                            2. 'description': Purpose and contents of this table
                            3. 'columns': Array of objects with 'name' and 'description' for each column
                            """

                            user_content = f"Table: {table_name}\nColumns: {columns_info}"
                            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_07)
                            response = openai_helper.callai_json(system_content, user_content, 'admin')
                            table_info = json.loads(response)

                            instructions_data.append({
                                'type': 'database_table',
                                'table_name': table_name,
                                'description': table_info.get('description'),
                                'columns': table_info.get('columns', [])
                            })

        # Save the instructions data to the database
        logger.info(f"Saving custom instructions for collection id [{collection_id}]")
        # Format the custom instructions as a JSON string
        custom_instructions = json.dumps([
            {
                'type': item.get('type'),
                'file_name': item.get('file_name') or item.get('table_name'),
                'description': item.get('description'),
                'columns': item.get('columns', [])
            }
            for item in instructions_data
        ])

        # Prepare the values for the query
        instructions_values = [(custom_instructions, collection_id)]

        inserted_ids = db_helper.execute_many_and_get_ids(
            queries.UPDATE_CUSTOM_INSTRUCTION_IN_COLLECTION,
            instructions_values
        )

        logger.info(f"Saved custom instructions for collection id [{collection_id}]")
        return custom_instructions

    except Exception as e:
        logger.error(f"Error generating custom instructions: {str(e)}")
        raise e

def fileprocessor_summarise_update():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")
        is_process_remaining = request.json.get('is_process_remaining')

        """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id) """
        selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id)

        if is_process_remaining:
            """ processed_files = db_helper.find_many(
                queries.FIND_FILES_FOR_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                organization_id, collection_id) """
            processed_files = db_helper.find_many(
                queries.V2_FIND_FILES_FOR_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                organization_id, collection_id)
            processed_files = [file['file_id'] for file in processed_files]
            selected_files = [file for file in selected_files if file.get('file_id') not in processed_files]

        doc_summaries = []
        for file in selected_files:
            file_id = file.get('file_id')
            filename = file.get('file_name')
            logger.info(f"Processing file: {filename}")
            file_path = os.path.join(config.ORGDIR_PATH, organization_name, config.ORGDIR_SUB_PATH, filename)
            if not os.path.exists(file_path):
                logger.error(f'File {file_path} is not exist')
                continue
            # Assuming each file is a document
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

            full_content = ""
            for d in documents:
                full_content += d.get_text()
            print(len(full_content))
            response = summarize(full_content)

            response = re.sub(r'```json', '', response, count=1)
            response = re.sub(r'```', '', response, count=1)
            response = clean_str_for_json_loads(response)
            response_json = json.loads(response)

            title = response_json.get('title', "")
            summary_short = response_json.get('summary_short', "")
            summary_long = response_json.get('summary_long', "")
            updated_rows = db_helper.execute_and_get_row_count(queries.UPDATE_METADATA_IN_FILES_METADATA_BY_FILE_ID,
                                                               title, summary_short, summary_long,
                                                               file_id)
            if updated_rows == 0:
                db_helper.execute(queries.INSERT_FILES_METADATA, file_id, filename, title, summary_short, summary_long)
            doc_summaries.append(response_json)
            return doc_summaries
    except Exception as e:
        print(e)
        raise e


def clean_str_for_json_loads(string_var):
    string_var = string_var.replace('\u20b9', 'INR')

    start_index = string_var.find('{')
    end_index = string_var.rfind('}')

    # Check if both '{' and '}' are found
    if start_index != -1 and end_index != -1:
        # Extract the part from the first '{' to the last '}'
        return string_var[start_index:end_index + 1]
    else:
        # If either '{' or '}' is not found, return the original string or handle it as needed
        return string_var


def summarize(full_content):
    if len(full_content) < config.MAX_TOKENS:  # roughly a context window of 100000 tokens assuming gpt4-turbo
        system_content = "Context:\n" + full_content
        user_content = """
            For the text given in the Context, provide a strictly formatted JSON value with following values:\n
            1. 'title' which has a sutiable title for the file\n
            2. 'summary_short' which clearly describes what the text in the Context is about in 50 words\n
            3. 'summary_long' which is a summary in 400 words, which has all the important details like names, 
            financials and facts included. Don't say that something is there in the document, 
            instead mention the fact in the summary using as few words as possible. Pack in all the facts or propositions that can be packed into 400 words.\n
            Also escape all control characters including the newline character.
        """
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_03)
        response = openai_helper.callai(system_content, user_content, 'admin')
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

            user_content = """
                Provide a summary of the text in Context in 2000 words, 
                which has all the important details like names, financials and facts included. Don't say that something is there in the document, 
                instead mention the fact in the summary using as few words as possible. 
                Pack in all the facts or propositions that can be packed into 400 words.\n
            """
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_03)
            summary_tillnow = openai_helper.callai(system_content, user_content, 'admin')
        system_content = "Context:\n" + summary_tillnow
        user_content = """
            For the text given in the Context, provide a strictly formatted JSON value with following values:\n
            1. 'title' which has a sutiable title for the file\n
            2. 'summary_short' which clearly describes what the text in the Context is about in 50 words\n
            3. 'summary_long' which is a summary in 400 words, which has all the important details like names, 
            financials and facts included. Don't say that something is there in the document, 
            instead mention the fact in the summary using as few words as possible. Pack in all the facts or propositions that can be packed into 400 words.\n
            Also escape all control characters including the newline character.
        """
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_03)
        response = openai_helper.callai(system_content, user_content, 'admin')
    return response


def get_docchat_faq():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        collection_id = request.args.get('collection_id')
        logger.info(f'Fetching faqs for collection id [{collection_id}] and org id [{organization_id}]')
        faqs = db_helper.find_many(queries.FIND_DOCCHAT_FAQ_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id,
                                   collection_id)
        faq_data = [
            dict(faq_id=faq.get('faq_id'), faq_question=faq.get('faq_question'), faq_answer=faq.get('faq_answer')) for
            faq in faqs]
        logger.info(f'[{len(faq_data)}] number of faqs found!')
        return faq_data
    except Exception as e:
        logger.error(e)
        raise e


def create_docchat_faq():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context.get('user_id')
        questions = request.json.get('questions', [])
        collection_id = request.json.get('collection_id')
        inserted_faqs = []
        logger.info(
            f"Inserting faq questions of [{str(len(questions))}] to docchat_faq with collection id [{str(collection_id)}]")
        for question in questions:
            inserted_id = db_helper.execute_and_get_id(queries.INSERT_DOCCHAT_FAQ, question, '', collection_id,
                                                       organization_id)
            inserted_faqs.append(dict(question=question, faq_id=inserted_id))

        logger.info(
            f"Faq questions inserted successfully, total inserted faq items [{str(len(inserted_faqs))}]. Calling DocChatManager to find faq answers.")
        for faq in inserted_faqs:
            docchat_manager = DocChatManager()
            docchat_manager.user_id = user_id
            docchat_manager.collection_id = collection_id
            docchat_manager.organization_id = organization_id
            docchat_manager.user_query = faq.get('question')
            docchat_manager.find_prompts()
            if docchat_manager.contains_noun():
                docchat_manager.filter_metadata_by_NER()
            else:
                docchat_manager.find_metadata_csv()
            docchat_manager.cumulative_search()
            faq_answer = docchat_manager.final_message

            logger.info(f'Inserting faq answer for faq_id [{faq.get("faq_id")}]')
            db_helper.execute(queries.UPDATE_DOCCHAT_FAQ_ANSWER,
                              faq_answer,
                              faq.get("faq_id"))

    except Exception as e:
        logger.error(f"Error occurred during create_docchat_faq. Error [{str(e)}]")
        raise e


def update_docchat_faq():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        question = request.json.get('question')
        faq_id = request.json.get('faq_id')
        faq = db_helper.find_one(queries.FIND_DOCCHAT_FAQ_BY_FAQ_IDS, [faq_id])
        collection_id = faq.get('collection_id')
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        collection_name = collection.get('collection_name')
        logger.info(f'Updating question [{question}] in faq table with id [{faq_id}]')
        db_helper.execute(queries.UPDATE_DOCCHAT_FAQ_QUESTION, question, faq_id)

        vs = VectorSearch(question)
        vs.embed_query()
        vs.vector_search(
            search_filter={"orgname": {"$eq": organization_name}, "collection": {"$in": [collection_name]}})
        vs.parse_content()
        context_prompt = vs.context_prompt
        general_prompt = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME,
                                            'docchat',
                                            'FAQ_ANSWER_FINDER')
        general_prompt = general_prompt.get('prompt_text')
        system_content = general_prompt + "\n\nCONTEXT:\n" + context_prompt
        user_content = "\n\nQUESTION:\n" + question

        logger.info(f'Sending openai to find answer for the question from the context')
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_06)
        response = openai_helper.callai_json(system_content, user_content, 'admin')
        response = json.loads(response)
        faq_answer = response.get('answer')
        logger.info(f'Answer found for faq, question [{question}], answer [{faq_answer}]')
        logger.info(f'Updating answer in faq table with id [{faq_id}]')
        db_helper.execute(queries.UPDATE_DOCCHAT_FAQ_ANSWER,
                          faq_answer,
                          faq_id)
        # db_helper.execute_and_get_id(queries.UPDATE_DOCCHAT_FAQ_ANSWER, '', faq_id)
    except Exception as e:
        logger.error(e)
        raise e


def delete_docchat_faq():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        faq_ids = request.json.get('faq_ids')
        db_helper.execute(queries.DELETE_DOCCHAT_FAQ, faq_ids)
    except Exception as e:
        logger.error(e)
        raise e


def get_docchat_metadata_for_download():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        collection_id = request.args.get("collection_id")
        """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id) """
        selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id)
        metadata = db_helper.find_many(queries.FIND_DOCCHAT_METADATA_WITH_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                       organization_id, collection_id)
        # file_ids = [data.get('file_id') for data in metadata]
        # files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        # metadata_schema = db_helper.find_many(queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
        #                                       organization_id, collection_id)
        # grouped_metadata = list()
        for metadata_field in metadata:
            file = next((file for file in selected_files if file.get('file_id') == metadata_field.get('file_id')), {})
            metadata_field.update(dict(file_name=file.get('file_name')))

        df = pd.DataFrame(metadata)

        field_order_df = df[['field', 'order_number']].drop_duplicates().set_index('field')

        # Pivot the DataFrame to reshape it
        pivot_df = df.pivot(index='file_id', columns='field', values='value')

        # Flatten the column headers (optional, for cleaner CSV format)
        pivot_df.columns.name = None

        # Sort columns based on order_number
        sorted_fields = field_order_df.sort_values(by='order_number').index.tolist()
        pivot_df = pivot_df[sorted_fields]

        # Reset the index to make `file_id` a column again
        pivot_df.reset_index(inplace=True)

        # Merge with the original dataframe to include 'file_name'
        file_names = df[['file_id', 'file_name']].drop_duplicates().set_index('file_id')
        pivot_df = pivot_df.merge(file_names, left_on='file_id', right_index=True, how='left')

        # Ensure 'file_id' and 'file_name' are the first two columns
        cols = ['file_id', 'file_name'] + [col for col in pivot_df.columns if col not in ['file_id', 'file_name']]
        pivot_df = pivot_df[cols]
        response = pivot_df.to_dict(orient='records')
        return response
        # grouped_metadata = list()
        # for file in selected_files:
        #     file_metadata = [data for data in metadata if data.get('file_id') == file.get('file_id')]
        #     grouped_metadata.append(dict(file_id=file.get('file_id'), metadata=file_metadata))
        # response = list()
        # for data in grouped_metadata:
        #     file = next((file for file in selected_files if file.get('file_id') == data.get('file_id')), {})
        #     metadata_row = OrderedDict()
        #     metadata_row['file_id'] = file.get('file_id')
        #     metadata_row['file_name'] = file.get('file_name')
        #     for field in metadata_schema:
        #         value = next((metadata_field.get('value') for metadata_field in data.get('metadata') if
        #                       field.get('field') == metadata_field.get('field')), "")
        #         metadata_row[field.get('field')] = value
        #     response.append(metadata_row)
        # return response
    except Exception as e:
        logger.error(e)
        raise e


def get_docchat_metadata_files():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        collection_id = request.args.get("collection_id")
        """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id) """
        selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id)
        metadata_schema = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        metadata = db_helper.find_many(queries.FIND_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                       organization_id, collection_id)
        result = []
        if not metadata_schema or not selected_files:
            return result
        total_metadata_entries = len(metadata_schema)
        for file in selected_files:
            metadata_content = [metadata_entry for metadata_entry in metadata if
                                metadata_entry.get('file_id') == file.get('file_id')] or {}
            processed_entries = [content for content in metadata_content if content.get('value') != ""]
            percentage = (len(processed_entries) / total_metadata_entries) * 100
            percentage = min(max(int(percentage), 0), 100)
            result.append(
                dict(file_id=file.get('file_id'), file_name=file.get('file_name'), processed_percentage=percentage))
        return result
    except Exception as e:
        logger.error(e)
        raise e


def process_docchat_metadata():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")
        file_ids = request.json.get('file_ids')
        is_processing_all_files = True
        if file_ids:
            is_processing_all_files = False
            selected_files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        else:
            """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                 collection_id, organization_id) """
            selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                 collection_id, organization_id)
        logger.info(f'Found [{len(selected_files)}] files in collection [{collection_id}]')
        metadata_schema = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        logger.info(f'Found [{len(metadata_schema)}] metadata schema objects for collection [{collection_id}]')
        json_schema = [dict(field=schema.get('field'), description=schema.get('description')) for schema in
                       metadata_schema]
        # json_schema.extend([dict(field='title', description='A title for the content, around 3-4 words'),
        #                     dict(field='summary_short', description='A short summary for the content'),
        #                     dict(field='summary_long', description='A long summary for the content')])

        for file in selected_files:
            file_id = file.get('file_id')
            filename = file.get('file_name')

            logger.info(f"Processing metadata for fileid/filename [{file_id}/{filename}]")

            file_path = os.path.join(config.ORGDIR_PATH, organization_name, config.ORGDIR_SUB_PATH, filename)
            if not os.path.exists(file_path):
                logger.error(f'File {file_path} is not exist, skipping to next file')
                continue
            # Assuming each file is a document
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
            file_processor_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'file_processor')
            metadata_prompt = next(
                (prompt for prompt in file_processor_prompts if prompt.get('prompt_name') == 'metadata_generation'))
            system_content = metadata_prompt.get('prompt_text')
            user_content = f'JSON_SCHEMA: \n```\n{json.dumps(json_schema)}\n```\n'
            user_content = user_content + "CONTEXT:\n"
            for d in documents:
                user_content += d.get_text()
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_05)
            response = openai_helper.callai_json(system_content, user_content, 'admin')
            dict_response = json.loads(response)
            logger.info(f'Processed [{len(dict_response.items())}/{len(metadata_schema)}] values for metadata')
            for key, value in dict_response.items():
                schema_for_field = next((schema for schema in metadata_schema if schema.get('field') == key))
                schema_id = schema_for_field.get('schema_id')
                db_helper.execute(queries.REPLACE_DOCCHAT_METADATA, organization_id, collection_id, schema_id, file_id,
                                  key, value)
        logger.info(f'Metadata processing completed for collection [{collection_id}]')
        return "Metadata processed successfully for all files" if is_processing_all_files else "Metadata processed successfully for selected files"
    except Exception as e:
        logger.error(e)
        raise e


def process_docchat_metadata_for_schema(schema_ids):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")

        """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id) """
        selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id)
        logger.info(f'Found [{len(selected_files)}] files in collection [{collection_id}]')
        metadata_schema = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_SCHEMA_IDS, schema_ids)
        logger.info(f'Found [{len(metadata_schema)}] metadata schema objects for collection [{collection_id}]')
        json_schema = [dict(field=schema.get('field'), description=schema.get('description')) for schema in
                       metadata_schema]
        # json_schema.extend([dict(field='title', description='A title for the content, around 3-4 words'),
        #                     dict(field='summary_short', description='A short summary for the content'),
        #                     dict(field='summary_long', description='A long summary for the content')])

        for file in selected_files:
            file_id = file.get('file_id')
            filename = file.get('file_name')

            logger.info(f"Processing metadata for fileid/filename [{file_id}/{filename}]")

            file_path = os.path.join(config.ORGDIR_PATH, organization_name, config.ORGDIR_SUB_PATH, filename)
            if not os.path.exists(file_path):
                logger.error(f'File {file_path} is not exist, skipping to next file')
                continue
            # Assuming each file is a document
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()
            file_processor_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'file_processor')
            metadata_prompt = next(
                (prompt for prompt in file_processor_prompts if prompt.get('prompt_name') == 'metadata_generation'))
            system_content = metadata_prompt.get('prompt_text')
            user_content = f'JSON_SCHEMA: \n```\n{json.dumps(json_schema)}\n```\n'
            user_content = user_content + "CONTEXT:\n"
            for d in documents:
                user_content += d.get_text()
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_02)
            response = openai_helper.callai_json(system_content, user_content, 'admin')
            dict_response = json.loads(response)
            logger.info(f'Processed [{len(dict_response.items())}/{len(metadata_schema)}] values for metadata')
            for key, value in dict_response.items():
                schema_for_field = next((schema for schema in metadata_schema if schema.get('field') == key))
                schema_id = schema_for_field.get('schema_id')
                db_helper.execute(queries.REPLACE_DOCCHAT_METADATA, organization_id, collection_id, schema_id, file_id,
                                  key, value)
        logger.info(f'Metadata processing completed for collection [{collection_id}]')
    except Exception as e:
        logger.error(e)
        raise e


def delete_docchat_metadata_for_schema(schema_ids):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        collection_id = request.json.get("collection_id")

        db_helper.execute(queries.DELETE_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID_AND_SCHEMA_IDS,
                          organization_id, collection_id, schema_ids)

        logger.info(f'Metadata processing completed for collection [{collection_id}]')
    except Exception as e:
        logger.error(e)
        raise e


def get_metadata_for_download():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        status_type = request.context['status_type']
        collection_id = request.args.get("collection_id")

        if status_type == 'metadata':
            # inaccessible code as /metadata endpoint calls another def. can be removed later
            metadata_list = db_helper.find_many(queries.FIND_FILES_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                organization_id, collection_id)

            metadata_response = [dict(file_name=metadata.get('file_name'), metadata=metadata.get('metadata')) for
                                 metadata in metadata_list]
            # headers = ['file_name', 'metadata']
            # body = [[metadata.get('file_name'), metadata.get('metadata')] for
            #         metadata in metadata_list]
            # metadata_response = dict(headers=headers, body=body)
            return metadata_response
        elif status_type == 'summarise':
            """ metadata_list = db_helper.find_many(queries.FIND_FILES_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                organization_id, collection_id) """
            metadata_list = db_helper.find_many(queries.V2_FIND_FILES_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                                organization_id, collection_id)
            metadata_response = [dict(file_name=metadata.get('file_name'), title=metadata.get('title'),
                                      summary_short=metadata.get('summary_short'),
                                      summary_long=metadata.get('summary_long')) for metadata in metadata_list]
            # headers = ['file_name', 'title', 'summary_short', 'summary_long']
            # body = [[metadata.get('file_name'), metadata.get('title'),
            #          metadata.get('summary_short'),
            #          metadata.get('summary_long')] for metadata in metadata_list]
            # metadata_response = dict(headers=headers, body=body)
            return metadata_response
    except Exception as e:
        print(e)
        raise e


def fileprocessor_metadata_update():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        collection_id = request.json.get("collection_id")
        content = request.json.get('content')
        is_process_remaining = request.json.get('is_process_remaining')

        if content and len(content) > 0:
            db_helper.execute(queries.UPDATE_METADATA_PROMPT_IN_COLLECTION_BY_COLLECTION_ID, content, collection_id)

        """ selected_files = db_helper.find_many(queries.FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id) """
        selected_files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                             collection_id, organization_id)
        if is_process_remaining:
            """ processed_files = db_helper.find_many(
                queries.FIND_FILES_FOR_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                organization_id, collection_id) """
            processed_files = db_helper.find_many(
                queries.V2_FIND_FILES_FOR_METADATA_PLUS_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                organization_id, collection_id)
            processed_files = [file['file_id'] for file in processed_files]
            selected_files = [file for file in selected_files if file.get('file_id') not in processed_files]

        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, collection_id)
        collection_prompt = collection.get('metatadata_prompt_prelude') or ''
        collection_prompt += collection.get(
            'metatadata_prompt') or ''

        for file in selected_files:
            file_id = file.get('file_id')
            filename = file.get('file_name')
            logger.info(f"Processing file: {filename}")

            file_path = os.path.join(config.ORGDIR_PATH, organization_name, config.ORGDIR_SUB_PATH, filename)
            if not os.path.exists(file_path):
                logger.error(f'File {file_path} is not exist')
                continue
            # Assuming each file is a document
            documents = SimpleDirectoryReader(input_files=[file_path]).load_data()

            system_content = "Context:\n"
            for d in documents:
                system_content += d.get_text()
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_04)
            response = openai_helper.callai(system_content, collection_prompt, 'admin')

            logger.info(f"Summary received from LLM")
            response = re.sub(r'```json', '', response, count=1)
            response = re.sub(r'```', '', response, count=1)

            response = clean_str_for_json_loads(response)
            updated_rows = db_helper.execute_and_get_row_count(
                queries.UPDATE_METADATA_IN_FILES_METADATA_PLUS_BY_FILE_ID, response, file_id)
            if updated_rows == 0:
                db_helper.execute(queries.INSERT_FILES_METADATA_PLUS, file_id, response)
            logger.info(f"Metadata update for the file completed")
    except Exception as e:
        print(e)
        raise e


def save_metadata_schema():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to save metadata content.")

        organization_id = int(request.context.get('organization_id'))
        collection_id = request.json.get('collection_id')
        schema = request.json.get('schema')

        logger.info(f"Creating metadata schema for collection id [{collection_id}], schema list [{len(schema)}]")

        if not collection_id or not schema:
            raise RuntimeError("Collection ID and Schema are required")

        existing_metadata_schemas = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        if len(existing_metadata_schemas) > 0:
            existing_metadata_schemas.sort(key=lambda x: x.get('order_number'))

        order_number_count = len(existing_metadata_schemas)
        for value in schema:
            field = value.get('field')
            description = value.get('description')
            value['order_number'] = order_number_count
            if not field or not description:
                raise RuntimeError("Field and Description are required for each schema")
            order_number_count += 1

        metadata_values = [
            (organization_id, collection_id, value.get('field'), value.get('description'), value.get('order_number'))
            for value in
            schema]
        logger.info(f"Inserting metadata schema for collection id [{collection_id}]")
        inserted_schema_ids = db_helper.execute_many_and_get_ids(queries.INSERT_DOCCHAT_METADATA_SCHEMA,
                                                                 metadata_values)
        logger.info(
            f"Inserted metadata schema for collection id [{collection_id}], processing metadata for created schema")
        process_docchat_metadata_for_schema(inserted_schema_ids)

        logger.info(f"Metadata content saved successfully for organization_id: {organization_id}")
    except Exception as e:
        print(e)
        raise e

def generate_metadata_schema():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to save metadata content.")

        organization_id = int(request.context.get('organization_id'))
        collection_id = request.json.get('collection_id')

        logger.info(f"Generating metadata schema for collection id [{collection_id}]")

        if not collection_id:
            raise RuntimeError("Collection ID is required")

        existing_metadata_schemas = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        if len(existing_metadata_schemas) > 0:
            raise RuntimeError("Metadata fields are already there")

        # Generate metadata schema for text files in the collection
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID, collection_id, organization_id)
        orgname = db_helper.find_one(queries.FIND_ORGANIZATION_BY_ORGANIZATION_ID, organization_id).get('org_name')
        logger.debug(f"Number of files: {len(files)}")
        text_file_ids = []
        for file in files:
            file_name = file.get('file_name')
            if file_name:
              _, file_extension = os.path.splitext(file_name)
              file_extension = file_extension.lower()
              if file_extension == '.pdf':
                    file_path = os.path.join(config.ORGDIR_PATH, orgname, config.ORGDIR_SUB_PATH, file_name)
                    doc = fitz.open(file_path)
                    num_pages = doc.page_count
                    logger.debug(f"File name: {file_name}, Number of pages: {num_pages}")
                    text_file_ids.append({
                        'file_id': file.get('file_id'),
                        'file_name': file_name,
                        'file_path': file_path,
                        'page_number': num_pages
                    })
                    doc.close()

        # Sort the text_file_ids list by page_number
        text_file_ids = sorted(text_file_ids, key=lambda x: x['page_number'])

        sample_file_content = ''
        # for 3 files with the lowest page numbers, store their full page_text in sample_file_content
        for text_file in text_file_ids[:3]:
            doc = fitz.open(text_file['file_path'])
            # load all pages text into sample_file_content
            for i in range(text_file['page_number']):
                page = doc.load_page(i)
                if i == 0:
                    sample_file_content += "\nFile name: " + text_file['file_name'] + "\n"
                sample_file_content += page.get_text()
            doc.close()
        logger.debug(f"Length of Sample file content: {len(sample_file_content)}")

        system_content = f"""
            Identify the metadata fields for the text files who are of the type indicated by the sample files given by the user. The response should be strictly formatted as JSON array with the following fields:
            1. 'field' which is the name of the metadata field
            2. 'description' which is a description of the metadata field
            3. 'order_number' which is the order in which the metadata fields should be displayed

            Example:
            [{{"field": "fullname", "description": "Fullname of the candidate", "order_number": 0}},
            {{"field": "email_id", "description": "email id", "order_number": 1}},
            {{"field": "year_of_graduation", "description": "Year of passing out of undergrad degree", "order_number": 2}},
            {{"field": "college_name", "description": "Name of the college", "order_number": 3}},
            {{"field": "course_name", "description": "Name of the Course or Program completed in Undergrad", "order_number": 4}},
            {{"field": "percentage_marks_secured", "description": "% of total marks for the total course or program", "order_number": 5}},
            {{"field": "name_of_company1", "description": "Name of first company worked for", "order_number": 6}},
            {{"field": "month_year_joining1", "description": "Month and Year of joining", "order_number": 7}},
            {{"field": "roles1a", "description": "First role within company", "order_number": 8}},
            {{"field": "duration1a", "description": "Duration of Role 1", "order_number": 9}},
            {{"field": "roles1b", "description": "Second role within company", "order_number": 10}},
            {{"field": "duration1b", "description": "Duration of Role 2", "order_number": 11}},
            {{"field": "name_of_company2", "description": "Name of second company worked for", "order_number": 12}},
            {{"field": "month_year_joining2", "description": "Month and Year of joining", "order_number": 13}},
            {{"field": "roles2a", "description": "First role within company", "order_number": 14}},
            {{"field": "duration2a", "description": "Duration of Role 1", "order_number": 15}},
            {{"field": "roles2b", "description": "Second role within company", "order_number": 16}},
            {{"field": "duration2b", "description": "Duration of Role 2", "order_number": 17}},
            {{"field": "skills", "description": "Key skills or proficiencies", "order_number": 18}},
            {{"field": "certifications", "description": "Professional certifications obtained", "order_number": 19}},
            {{"field": "languages_known", "description": "Languages the candidate is fluent in", "order_number": 20}},
            {{"field": "projects", "description": "Notable projects completed", "order_number": 21}},
            {{"field": "volunteer_experience", "description": "Volunteer activities or experiences", "order_number": 22}},
            {{"field": "hobbies", "description": "Personal hobbies or interests", "order_number": 23}},
            {{"field": "linkedin_profile", "description": "URL to the LinkedIn profile", "order_number": 24}},
            {{"field": "github_profile", "description": "URL to the GitHub profile", "order_number": 25}},
            {{"field": "personal_website", "description": "URL to the personal website or portfolio", "order_number": 26}},
            {{"field": "awards", "description": "Awards or recognitions received", "order_number": 27}},
            {{"field": "references", "description": "References with contact details", "order_number": 28}}]

            Use the content from the Sample files to identify the nature of the documents like are they financial reports, legal documents, HR documents, healthcare documents, reports of some specific kind etc. and then identify the metadata fields accordingly.

            The field names and descriptions should be selected so that the values can be string, number, date, boolean, list of strings, list of numbers, list of dates, list of booleans etc.. No Dictionaries or nested structures are allowed. The field names should be such that they can be used as keys in a JSON object.
        """
        user_content = sample_file_content

        logger.info(f'Sending openai to generate metadata')
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.FILE_PROCESSOR_07)
        response = openai_helper.callai_json(system_content, user_content, 'admin')
        logger.info(f'Metadata generated: {response}')
        response = json.loads(response)
        schema =[]
        response_fields = response.get('metadata_fields')
        if response_fields is None:
            response_fields = response
        #if response is a dictionary and not a list, convert it to a list
        if not isinstance(response_fields, list):
            response_fields = [response_fields]

        for index, value in enumerate(response_fields):
            schema.append({
                'field': value.get('field'),
                'description': value.get('description'),
                'order_number': index
            })
        logger.info(f'Metadata schema generated successfully')

        metadata_values = [
            (organization_id, collection_id, value.get('field'), value.get('description'), value.get('order_number'))
            for value in
            schema]
        logger.info(f"Inserting metadata schema for collection id [{collection_id}]")
        inserted_schema_ids = db_helper.execute_many_and_get_ids(queries.INSERT_DOCCHAT_METADATA_SCHEMA,
                                                                 metadata_values)
        logger.info(
            f"Inserted metadata schema for collection id [{collection_id}]")

        process_docchat_metadata_for_schema(inserted_schema_ids)

    except Exception as e:
        print(e)
        raise e

def get_metadata_schema():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to get metadata content.")

        organization_id = request.context['organization_id']
        collection_id = request.args.get('collection_id')

        if not collection_id:
            raise RuntimeError("Collection ID is required")

        metadata_content = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)

        response = [dict(schema_id=metadata.get('schema_id'), field=metadata.get('field'),
                         description=metadata.get('description'), order_number=metadata.get('order_number')) for
                    metadata in metadata_content]

        response.sort(key=lambda x: x.get('order_number'))
        logger.info(f"Metadata content fetched successfully for organization_id: {organization_id}")
        return response
    except Exception as e:
        print(e)
        raise e


def update_metadata_schema():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to update metadata content.")

        organization_id = request.context.get('organization_id')
        schema_id = request.json.get('schema_id')
        field = request.json.get('field')
        description = request.json.get('description')

        logger.info(f"Updating metadata schema for schema id [{schema_id}]")

        if not schema_id or not field or not description:
            raise RuntimeError("Collection ID, Schema ID, Field, Description  are required")

        db_helper.execute(queries.UPDATE_FIELD_AND_DESCRIPTION_IN_DOCCHAT_METADATA_BY_SCHEMA_ID,
                          field, description, schema_id)

        logger.info(f"Metadata content updated successfully for organization_id: {organization_id}")
        process_docchat_metadata_for_schema([schema_id])
    except Exception as e:
        print(e)
        raise e


def update_metadata_schema_weight():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to update metadata content.")

        organization_id = request.context.get('organization_id')
        collection_id = request.json.get('collection_id')
        schema_id = request.json.get('schema_id')
        weight_to = int(request.json.get('weight_to'))

        logger.info(
            f"Updating metadata schema weight for collection id [{collection_id}], schema id [{schema_id}], wight_to [{weight_to}]")

        if not schema_id or not collection_id or weight_to is None or weight_to == "":
            raise RuntimeError("Schema ID, Collection Id and weight are required")

        metadata_schemas = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        metadata_schemas.sort(key=lambda x: x.get('order_number'))
        metadata_schema = next(
            (metadata_schema for metadata_schema in metadata_schemas if metadata_schema.get('schema_id') == schema_id),
            {})
        weight_from = metadata_schema.get('order_number')

        item = metadata_schemas.pop(weight_from)

        logger.info(
            f"Changing metadata schema weight for collection id [{collection_id}], schema id [{schema_id}] from position [{weight_from}] to [{weight_to}]")

        # Insert the dictionary at the 3rd index
        metadata_schemas.insert(weight_to, item)

        # Update order_number fields
        update_args = list()
        for index, data in enumerate(metadata_schemas):
            update_args.append((index, data.get('schema_id')))

        def callback(cursor):
            random_counter = 100000  # FIXME: make sure this number is not already exist in table as order_number, that might cause duplicate error
            temp_update_args = list()
            for _, schema_id in update_args:
                temp_update_args.append((random_counter, schema_id))
                random_counter += 1
            cursor.executemany(queries.UPDATE_ORDER_NUMBER_IN_DOCCHAT_METADATA_BY_SCHEMA_ID, temp_update_args)
            cursor.executemany(queries.UPDATE_ORDER_NUMBER_IN_DOCCHAT_METADATA_BY_SCHEMA_ID, update_args)

        db_helper.execute_many_with_transaction_callback(callback)

        logger.info(f"Metadata weight updated successfully for organization_id: {organization_id}")
    except Exception as e:
        print(e)
        raise e


def delete_metadata_schema():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required to delete metadata content.")

        organization_id = request.context.get('organization_id')
        schema_ids = request.json.get('schema_ids')
        collection_id = request.json.get('collection_id')

        logger.info(f"Deleting metadata schema for collection id [{collection_id}], schema ids [{schema_ids}]")
        if not schema_ids:
            raise RuntimeError("Collection ID and Schema IDs are required")

        to_delete = [(schema_id,) for schema_id in schema_ids]
        existing_metadata_schemas = db_helper.find_many(
            queries.FIND_DOCCHAT_METADATA_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        existing_metadata_schemas.sort(key=lambda x: x.get('order_number'))
        # Filter out items to be removed
        non_remove_metadata_schemas = [item for item in existing_metadata_schemas if
                                       item.get('schema_id') not in schema_ids]

        # Update order_number fields
        update_args = list()
        for index, data in enumerate(non_remove_metadata_schemas):
            update_args.append((index, data.get('schema_id')))

        def callback(cursor):
            random_counter = 100000  # FIXME: make sure this number is not already exist in table as order_number, that might cause duplicate error
            temp_update_args = list()
            for _, schema_id in update_args:
                temp_update_args.append((random_counter, schema_id))
                random_counter += 1
            cursor.executemany(queries.DELETE_DOCCHAT_METADATA_BY_SCHEMA_ID, to_delete)
            cursor.executemany(queries.UPDATE_ORDER_NUMBER_IN_DOCCHAT_METADATA_BY_SCHEMA_ID, temp_update_args)
            cursor.executemany(queries.UPDATE_ORDER_NUMBER_IN_DOCCHAT_METADATA_BY_SCHEMA_ID, update_args)

        logger.info(f"Rearranging order numbers and deleting metadata schema")
        db_helper.execute_many_with_transaction_callback(callback)

        logger.info(f"Metadata content deleted successfully for organization_id: {organization_id}")
        delete_docchat_metadata_for_schema(schema_ids)
    except Exception as e:
        print(e)
        raise e


def upload_metadata_file():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')

        organization_id = request.context['organization_id']
        collection_id = request.form.get('collection_id')

        if 'file' not in request.files:
            raise RuntimeError('No file part in the request!')

        file = request.files['file']
        if file.filename == '':
            raise RuntimeError('No file selected!')

        if not file.filename.lower().endswith('.csv'):
            raise RuntimeError('File must be a CSV!')

        csv_content = file.read().decode('utf-8')
        df = pd.read_csv(StringIO(csv_content))

        # Replace NaN values with an empty string
        df.fillna('', inplace=True)

        # Convert all data to string
        df = df.astype(str)

        if 'file_id' not in df.columns:
            return RuntimeError('file_id column not found in CSV!')

        csv_values = df.set_index('file_id').to_dict('index')

        metadata = db_helper.find_many(queries.FIND_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                       organization_id, collection_id)
        metadata_values = {}
        for _doc in metadata:
            metadata_values.setdefault(_doc['file_id'], {})[_doc['field']] = _doc['value']

        updates = []

        for file_id, _obj in metadata_values.items():
            for field, value in _obj.items():
                if field == 'file_name':
                    continue
                csv_row = csv_values.get(str(file_id), {})
                csv_value = csv_row.get(field, '')
                if csv_value != value:
                    updates.append((csv_value, organization_id, collection_id, file_id, field))

        if updates:
            db_helper.execute_many(
                queries.UPDATE_VALUE_IN_DOCCHAT_METADATA_BY_ORGANIZATION_ID_AND_COLLECTION_ID_FILE_ID_AND_FIELD,
                updates)

    except Exception as e:
        logger.error(e)
        raise e


def save_collection_rule():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required!")
        collection_id = request.json.get('collection_id')
        collection_rules = request.json.get("collection_rules")
        collection_rule = json.dumps(collection_rules)
        db_helper.execute(queries.UPDATE_COLLECTION_RULE_IN_COLLECTION_BY_COLLECTION_ID, collection_rule, collection_id)
    except Exception as e:
        logger.error(f"Error occurred during saving collection rule, Error: {str(e)}")
        raise e


def get_collection_rule():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError("Organization ID is required!")
        organization_id = request.context.get('organization_id')
        collection_id = request.args.get('collection_id')
        """ collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id,
                                        collection_id) """
        collection = db_helper.find_one(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID_AND_COLLECTION_ID, organization_id, collection_id)
        collection_rule = collection.get('collection_rule', None)
        if collection_rule is None:
            try:
                configurations = db_helper.find_many(queries.V2_FIND_GENERAL_COLLECTION_RULE_CONFIGURATION)
                configuration_entry = next((config.get('data') for config in configurations if json.loads(config.get('data')).get('name') == 'chatbox_instructions'), None)
                if configuration_entry:
                    collection_rules = json.loads(configuration_entry).get('value', '[]')
                    collection_rules = json.loads(collection_rules)
            except Exception as e:
                collection_rules = []
        else:
            collection_rules = json.loads(collection_rule) if collection_rule else []
        return collection_rules
    except Exception as e:
        logger.error(f"Error occurred during fetching collection rule, Error: {str(e)}")
        raise e
