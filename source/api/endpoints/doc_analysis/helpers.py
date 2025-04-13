import asyncio
import base64
import json
import logging
import os
import shutil
import subprocess
import sys
import uuid
from enum import Enum

import numpy as np
import pandas as pd
from flask import request, stream_with_context, jsonify
from werkzeug.utils import secure_filename

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, Prompts, StreamEvent
from source.api.utilities.externalapi_helpers import chats_helper
from source.api.utilities.externalapi_helpers.googledrive_helper import GoogleDriveHelper
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.common import config

from google.oauth2 import service_account
from googleapiclient.discovery import build

logger = logging.getLogger('app')

class DocAnalysis:
    class CATEGORY(Enum):
        QUALITATIVE = '1'
        QUANTITATIVE = '2'
        SEARCH = '3'


    def __init__(self, organization_id = None, organization_name = None, user_id = None):
        if organization_id is None:
            self.organization_id = request.context.get('organization_id')
        else:
            self.organization_id = organization_id
        if organization_name is None:
            self.organization_name = request.context.get('organization_name')
        else:
            self.organization_name = organization_name
        if user_id is None:
            self.user_id = request.context.get('user_id')
            self.user_is_admin = request.context.get('is_admin') or 0
        else:
            self.user_id = user_id

    def upload_file_temp(self):
        try:
            file = request.files.get('file')
            if not file:
                logger.warning("No file provided in the request")
                raise Exception("No file provided in the request")

            temp_dir = os.path.join(config.DOCANALYSIS_TEMP_FILE_PATH, str(self.user_id))
            os.makedirs(temp_dir, exist_ok=True)

            temp_filename = f"{uuid.uuid4()}_{secure_filename(file.filename)}"
            temp_filepath = os.path.join(temp_dir, temp_filename)
            file.save(temp_filepath)

            logger.info(f"File saved to: {temp_filepath}")

            return {'temp_filepath': temp_filepath}
        except Exception as e:
            logger.error(f"Error occurred during file upload: {str(e)}", exc_info=True)
            raise Exception(f"An error occurred during file upload")

    def process_upload_file(self, collection_id):
        try:
            temp_filepath = request.json.get('temp_filepath')
            if not temp_filepath:
                logger.warning("No temp_filepath provided in the request")
                raise Exception("No temp_filepath provided in the request")

            ignore = request.json.get('ignore', False)
            logger.info(f"Ignore: {ignore}")

            with open(temp_filepath, 'rb') as file:
                file.file_path = temp_filepath
                file.filename = os.path.basename(temp_filepath)
                return stream_with_context(self._generate_events(file, self.organization_name, collection_id, ignore))
        except Exception as e:
            logger.error(f"Exception: {str(e)}", exc_info=True)
            raise e

    def execute_file_analysis(self, collection_id, file_ids=None, query=None, thread_id=None, db_uri=None, gsheets_credentials_file_path=None, gsheet_ids_and_worksheets=None, custom_instructions=None):
        print("@@@@@@@@@@@@@@@@@@@@@@@@ Commencing execute_file_analysis")
        print(f"Query: {query}")
        try:
            if file_ids is None:
                file_ids = request.json.get('file_ids')
            if query is None:
                query = request.json.get('user_query')
            if thread_id is None:
                thread_id = request.json.get('thread_id')

            if not thread_id:
                thread_id = self._create_thread()

            yield self._sse_response(StreamEvent.PROGRESS_EVENT, "File reading in progress...", True, thread_id)
            category = self._categorize_query(query, thread_id)
            #category = self.CATEGORY.QUANTITATIVE

            if category == self.CATEGORY.SEARCH:
                msg = "Query identified as needing search for a specific name. Please rephrase your question."
            elif category == self.CATEGORY.QUALITATIVE:
                msg = "Query identified as needing Qualitative processing...\nNow identifying the data processing steps."
            else:
                msg = "Query identified as needing structured analysis/processing of data...\nNow identifying the data processing steps."


            yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)
            # yield self._sse_response(StreamEvent.PROGRESS_EVENT, f"Query identified as {'needing' if category == self.CATEGORY.QUALITATIVE else 'not needing'} Qualitative processing...", False, thread_id)

            #yield self._sse_response(StreamEvent.PROGRESS_EVENT, "Commencing call to AI to filter data...", False, thread_id)
            code, faq_id = self._find_code(query, collection_id)
            #faq_id = ''
            if code == '':
                code = self._generate_code(category, query, thread_id, file_ids, collection_id, db_uri, gsheets_credentials_file_path, gsheet_ids_and_worksheets, custom_instructions)
                faq_id = db_helper.execute_and_get_id(queries.INSERT_COLLECTION_FAQ, collection_id, query, code, self.user_id)
            msg = self._explain_code(code)
            yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)
            
            """ replacing this with check=true for better exception handling - 16th Feb 2025. if new code stable, remove the following by 31st March
            result, error, errorcode, image_data = self._execute_code(code, db_uri)

            if errorcode != 0:
                #if _execute_code returned an error, generate code once more by also giving the error message as input to llm
                yield self._sse_response(StreamEvent.PROGRESS_EVENT, "There was an error, trying again...", False, thread_id)
                erroneous_result = f"\nCode produced based on user query:\n{code}\nstdout Result: {result}\nstderr Error message on code execution:\n{error}"
                self._add_assistant_chat_history(query, erroneous_result, thread_id, code)
                code = self._improve_code(thread_id, code, erroneous_result)
                result, error, errorcode, image_data = self._execute_code(code, db_uri)
                #yield self._sse_response(StreamEvent.PROGRESS_EVENT, "###Error:"+error, False, thread_id)
                if errorcode != 0:
                    print('2nd time error. Create explanation for user.')
                    msg = "Ran into error again..."
                    yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)
                    user_content = f"In trying to answer a query got the following result:
                    {result}

                    Explain the error briefly to the user without being too technical. Dont repeat the error message mentioned above as it is too technical for the User. Use language which is of the type 'Unable to respond due to an error. The reason for the error is...'.
                    Mention clearly if the error is:
                    due to missing data and if so what is missing or
                    if it is due to some datatype issue and if so which fields are causing that or
                    if it is due to unexpected empty data in some intermediate step and if so which step is causing that.
                    "
                    previous_chat_context = []

                    openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
                    response = json.loads(openai_helper.callai_json(
                        system_content="As an AI Assitant, respond to the User query. Mention the response as a JSON in a field named 'answer'",
                        user_content=user_content,
                        user_id=str(self.user_id) or 'admin',
                        extra_context=previous_chat_context
                    ))

                    result = response.get('answer', 'Unable to respond. Try rephrasing the query by sharing more details. Include more details of the context that could help answer this query.') """
            image_data = ''
            try:
                if gsheets_credentials_file_path is not None and gsheet_ids_and_worksheets is not None:
                    #format is: gsheet_ids_and_worksheets[SPREADSHEET_ID] = {'name': SPREADSHEET_NAME,'worksheets': sheet_names}
                    #spreadsheet_ids = str(list(gsheet_ids_and_worksheets.keys()))
                    spreadsheet_ids = next(iter(gsheet_ids_and_worksheets))
                    result, error, errorcode, image_data = self._execute_code(code, db_uri, gsheets_credentials_file_path, spreadsheet_ids)
                else:
                    result, error, errorcode, image_data = self._execute_code(code, db_uri)
            except subprocess.CalledProcessError as e:
                #if _execute_code returned an error, generate code once more by also giving the error message as input to llm
                if faq_id != '':
                    db_helper.execute_and_get_id(queries.DELETE_COLLECTIONS_FAQ, faq_id)
                yield self._sse_response(StreamEvent.PROGRESS_EVENT, "There was an error, trying again...", False, thread_id)
                erroneous_result = f"\nCode produced based on user query:\n{code}\nstdout Result: {e.stdout}\nstderr Error message on code execution:\n{e.stderr}"
                self._add_assistant_chat_history(query, erroneous_result, thread_id, code)
                code = self._improve_code(thread_id, code, erroneous_result)
                faq_id = db_helper.execute_and_get_id(queries.INSERT_COLLECTION_FAQ, collection_id, query, code, self.user_id)
                try:
                    if gsheets_credentials_file_path is not None and gsheet_ids_and_worksheets is not None:
                        #format is: gsheet_ids_and_worksheets[SPREADSHEET_ID] = {'name': SPREADSHEET_NAME,'worksheets': sheet_names}
                        #spreadsheet_ids = str(list(gsheet_ids_and_worksheets.keys()))
                        spreadsheet_ids = next(iter(gsheet_ids_and_worksheets))
                        result, error, errorcode, image_data = self._execute_code(code, db_uri, gsheets_credentials_file_path, spreadsheet_ids)
                    else:
                        result, error, errorcode, image_data = self._execute_code(code, db_uri)
                except subprocess.CalledProcessError as e:
                    if faq_id != '':
                        db_helper.execute_and_get_id(queries.DELETE_COLLECTIONS_FAQ, faq_id)
                    print('2nd time error. Create explanation for user.')
                    msg = "Ran into error again..."
                    yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)
                    user_content = f"""In trying to answer a query got the following result:
                    {e.stderr}

                    Explain the error briefly to the user without being too technical. Dont repeat the error message mentioned above as it is too technical for the User. Use language which is of the type 'Unable to respond due to an error. The reason for the error is...'.
                    Mention clearly if the error is:
                    due to missing data and if so what is missing or
                    if it is due to some datatype issue and if so which fields are causing that or
                    if it is due to unexpected empty data in some intermediate step and if so which step is causing that.
                    """
                    previous_chat_context = []

                    openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
                    response = json.loads(openai_helper.callai_json(
                        system_content="As an AI Assitant, respond to the User query. Mention the response as a JSON in a field named 'answer'",
                        user_content=user_content,
                        user_id=str(self.user_id) or 'admin',
                        extra_context=previous_chat_context
                    ))

                    result = response.get('answer', 'Unable to respond. Try rephrasing the query by sharing more details. Include more details of the context that could help answer this query.')

            if category == self.CATEGORY.QUALITATIVE:
                msg = "I got the data I needed to respond. Processing it now to give you a response..."
                yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)
                yield from self._process_qualitative_output(result, query, thread_id, code)
                """ elif category == self.CATEGORY.QUANTITATIVE:
                yield from self._process_quantitative_output(result, query, thread_id, code) """
            else:
                self._add_assistant_chat_history(query, result, thread_id, code)
                yield self._sse_response(StreamEvent.FINAL_OUTPUT, result, False, thread_id, image_data, faq_id)

        except Exception as e:
            if faq_id != '':
                db_helper.execute_and_get_id(queries.DELETE_COLLECTIONS_FAQ, faq_id)
            logger.error(f"Error in execute_file_analysis: {str(e)}", exc_info=True)
            error_msg = json.loads(openai_helper.callai_json(
                        system_content="Go through the error message and explain this in 50 words so that a non-technical person can understand. Please retain any Table and Column names as that helps. Mention the response as a JSON in a field named 'answer'",
                        user_content=f"Error message: {str(e)}",
                        user_id=str(self.user_id) or 'admin',
                        extra_context=previous_chat_context
                    ))
            error_msg = error_msg.get('answer', str(e))
            yield self._sse_response(StreamEvent.FINAL_OUTPUT, f"Unable to answer the query. {error_msg}", True, thread_id)

    def delete_file(self):
        try:
            file_ids = request.json.get('file_ids', [])
            if not file_ids:
                raise ValueError("No file IDs provided for deletion")

            # Convert file_ids to a format suitable for SQL IN clause
            file_ids = tuple(file_ids)

            files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
            if not files:
                raise Exception(f"No files found in database for file_ids: {file_ids}")

            #self._delete_file_associations(file_ids) #not needed as collection_id is not stored in files table itself
            self._delete_file_records(file_ids)
            deleted_files = self._delete_files_from_disk(files)

            return {'message': 'Files deleted successfully', 'deleted_file_ids': deleted_files}
        except Exception as e:
            logger.error(f"Error occurred during file deletion process: {str(e)}", exc_info=True)
            raise Exception(f"An error occurred during file deletion process")

    """     def parse_file(self):
        try:
            file_id = request.json.get('file_id')
            file_path = self._get_file_path(file_id)
            df = self._read_file(file_path)
            df = df.replace({np.nan: ""})
            headers = list(df.columns)
            rows = df.head(100).to_dict(orient='records')
            return dict(headers=headers, rows=rows)
        except Exception as e:
            logger.error(f"Error occurred during parsing file, Error: {str(e)}")
            raise Exception(f"An error occurred during file parsing") """

    def parse_file(self):
        try:
            file_id = request.json.get('file_id')
            file_path = self._get_file_path(file_id)
            df = self._read_file(file_path, 100)

            # Identify datetime columns and convert them to strings
            for col in df.columns:
                if pd.api.types.is_datetime64_any_dtype(df[col]):
                    df[col] = df[col].astype(str)

            # Replace NaN values with an empty string
            df = df.replace({np.nan: ""})

            # Convert NaT values to a string or another placeholder
            df = df.applymap(lambda x: x if not isinstance(x, pd._libs.tslibs.nattype.NaTType) else "")

            headers = list(df.columns)
            rows = df.head(100).to_dict(orient='records')
            return dict(headers=headers, rows=rows)
        except Exception as e:
            logger.error(f"Error occurred during parsing file, Error: {str(e)}")
            raise Exception(f"An error occurred during file parsing")

    ###############################################################################################################
    ######################################### HELPER METHODS ######################################################
    ###############################################################################################################

    def _generate_events(self, file, organization_name, collection_id, ignore = False):
        async_generator = self._validate_and_process_file(file)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

        has_errors = False

        try:
            if (self.user_is_admin != 1):  # Bypass error check for Admins
                while not ignore:
                    try:
                        response = loop.run_until_complete(async_generator.__anext__())

                        if response.get('event') == StreamEvent.COLUMN_ERROR:
                            has_errors = True
                            yield f"event: {StreamEvent.COLUMN_ERROR}\ndata: {response.get('payload')}\n\n"
                        elif response.get('event') == StreamEvent.PROGRESS_EVENT:
                            yield f"event: {StreamEvent.PROGRESS_EVENT}\ndata: {response.get('payload')}\n\n"
                    except StopAsyncIteration:
                        break

            if not has_errors:
                file_id, message = self._save_file_to_disk(file, organization_name, collection_id)
                if file_id == None:
                    yield self._gen_message(StreamEvent.FINAL_OUTPUT, dict(success=False, message=message))
                else:
                    yield self._gen_message(StreamEvent.FINAL_OUTPUT, dict(success=True, file_id=file_id))
            else:
                yield self._gen_message(StreamEvent.FINAL_OUTPUT, dict(success=False, message="Errors found in file"))
        finally:
            loop.close()

    """ async def _validate_and_process_file(self, file):
        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': 'Validating file columns started'}
        
        sheets = self._get_sheets_from_file(file.file_path)
        
        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': f'Found {len(sheets)} sheets in the file'}    
        
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01, async_client=True)
        
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        validate_column_prompt_obj = next((p for p in docanalysis_prompts if p.get('prompt_name') == Prompts.DOCANALYSIS_VALIDATE_COLUMN), None)
        if not validate_column_prompt_obj:
            raise Exception('No prompt found for validating column')
        validate_column_prompt_text = validate_column_prompt_obj.get('prompt_text')
        logger.info(f"Validate column prompt:\n{validate_column_prompt_text}")
        
        async def validate_column(column):
            samples = df[column].sample(n=min(20, len(df))).tolist()
            user_content = f"Column Name: {column}\nSample Data: {samples}\n"
            
            response = json.loads(await openai_helper.callai_async_json(validate_column_prompt_text, user_content, 'admin'))
            validation_code = response.get('code', None)
            if not validation_code:
                return column, []
            logger.info(f"COLUMN NAME: {column}")
            logger.info(f"SAMPLE DATA: {samples}")
            logger.info(f"VALIDATION CODE:\n{validation_code}")
            try:
                local_env = {'pd': pd, 'np': np, 'column': column, 'df': df, 'logger': logger}
                exec(validation_code, local_env)
                if 'validate_column' not in local_env:
                    logger.error(f"Validation function not found in code response")
                    return column, [{'index': -1, 'value': 'Error', 'reason': 'Validation function not found in code response'}]
                return column, local_env['validate_column'](df[column])
            except Exception as e:
                logger.error(f"Error validating column {column}: {str(e)}")
                return column, [{'index': -1, 'value': 'Error','reason': str(e)}]

        async def process_errors(column, errors):
            if not errors:
                return None

            num_samples = min(20, len(errors))
            sampled_errors = errors[:num_samples]
            sampled_errors.sort(key=lambda x: x['index'])
            
            error_summary = f"Column: {column}\nTotal Error count: {len(errors)}\nSample errors:\n"
            for error in sampled_errors:
                error_summary += f"- Index {error['index']}: {error['value']} - {error['reason']}\n"
                
            beautify_error_prompt_obj = next((p for p in docanalysis_prompts if p.get('prompt_name') == Prompts.DOCANALYSIS_BEAUTIFY_ERRORS), None)
            if not beautify_error_prompt_obj:
                raise Exception('No prompt found for beautifying errors')
            beautify_error_prompt_text = beautify_error_prompt_obj.get('prompt_text')
            
            user_content = f"Error Summary:\n{error_summary}"
            
            response = await openai_helper.callai_async(beautify_error_prompt_text, user_content, 'admin')
            response = response.replace('"', '')
            return response

        for sheet_name, df in sheets:
            yield {'event': StreamEvent.PROGRESS_EVENT, 'payload':f'Validating sheet: {sheet_name}'}
            
            tasks = [validate_column(column) for column in df.columns]
            for task in asyncio.as_completed(tasks):
                column, errors = await task
                logger.info(f"Column: {column}, Errors: {errors}")
                if errors:
                    beautified_errors = await process_errors(column, errors)
                    if beautified_errors:
                        yield {'event': StreamEvent.COLUMN_ERROR, 'payload': beautified_errors}

        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': 'File validation completed'} """

    async def _validate_and_process_file(self, file):
        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': 'Validating file columns started'}

        sheets = self._get_sheets_from_file(file.file_path)

        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': f'Found {len(sheets)} sheets in the file'}

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01, async_client=True)

        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        validate_column_prompt_obj = next((p for p in docanalysis_prompts if p.get('prompt_name') == Prompts.DOCANALYSIS_VALIDATE_COLUMN), None)
        if not validate_column_prompt_obj:
            raise Exception('No prompt found for validating column')
        validate_column_prompt_text = validate_column_prompt_obj.get('prompt_text')

        async def validate_column(column):
            column_values = df[column].sample(n=min(500, len(df))).tolist() #send all rows up to 5000
            user_content = f"Column Name: {column}\nData: {column_values}\n"

            response = json.loads(await openai_helper.callai_async_json(validate_column_prompt_text, user_content, 'admin'))
            error_list = response
            if not error_list:
                return column, []
            logger.info(f"COLUMN NAME: {column}")

            return column, error_list

        MAX_COLUMNS = 5
        MAX_ERRORS = 20
        """ for sheet_name, df in sheets:
            yield {'event': StreamEvent.PROGRESS_EVENT, 'payload':f'Validating sheet: {sheet_name}'}
            
            tasks = [validate_column(column) for column in df.columns]
            for task in asyncio.as_completed(tasks):
                column, errors = await task
                logger.info(f"Column: {column}, Errors: {errors}")

                yield {'event': StreamEvent.COLUMN_ERROR, 'payload': errors} """
        for sheet_name, df in sheets:
            yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': f'Validating sheet: {sheet_name}. \nNote: Only the first few data issues will be shown below.'}

            columns = df.columns.tolist()
            total_columns = len(columns)
            errors_encountered = 0
            columns_processed = 0

            while columns and errors_encountered < MAX_ERRORS:
                current_columns = columns[:MAX_COLUMNS]
                columns = columns[MAX_COLUMNS:]

                #tasks = [validate_column(column) for column in current_columns]
                tasks = [asyncio.create_task(validate_column(column)) for column in current_columns]

                for task in asyncio.as_completed(tasks):
                    column, errors = await task
                    columns_processed += 1
                    if errors:
                        errors_encountered += len(errors['issues'])
                        logger.debug(f"Column: {column}, Errors: {errors}, number of errors: {errors_encountered}")
                        yield {'event': StreamEvent.COLUMN_ERROR, 'payload': json.dumps(errors)}

                    if errors_encountered >= MAX_ERRORS:
                        # Cancel remaining tasks
                        for t in tasks:
                            if not t.done():
                                t.cancel()
                        break

                if columns_processed >= total_columns:
                    break

            if errors_encountered >= MAX_ERRORS:
                break

        yield {'event': StreamEvent.PROGRESS_EVENT, 'payload': f"File validation completed. Found {errors_encountered} errors."}

    def _perform_database_operations(self, filename, file_path, collection_id):
        """ file_id = db_helper.execute_and_get_id(queries.INSERT_FILE, filename, file_path, collection_id) """
        file_id = db_helper.execute_and_get_id(queries.V2_INSERT_FILE, filename, file_path, collection_id, '')
        logger.info(f"File inserted into database with ID: {file_id} with collection_id: {collection_id}")

        """ COLLECTION_NAME = 'DocAnalysis'
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_NAME, COLLECTION_NAME)
        collection_id = collection.get('collection_id') """

        """ db_helper.execute(queries.INSERT_MANY_FILES_COLLECTION, file_id, collection_id)
        logger.info("File-collection association saved in database") """

        return file_id

    def _save_file_to_disk(self, file, organization_name, collection_id):
        original_filename = file.filename.replace(" ", "_")
        file_path = os.path.join(config.ORGDIR_PATH, organization_name)
        logger.info(f"File path: {file_path}")
        logger.info(f"Original filename: {original_filename}")
        os.makedirs(file_path, exist_ok=True)

        if '_' in original_filename:
            original_filename = original_filename.split('_', 1)[1]

        save_file_path = os.path.join(str(file_path), original_filename)

        # Check if the file already exists
        if os.path.exists(save_file_path):
            message = f"File with the same name already exists. Rename the file and upload."
            logger.warning(message)
            return None, message

        if hasattr(file, 'file_path') and os.path.exists(file.file_path):
            shutil.copy2(file.file_path, save_file_path)
        else:
            try:
                file.seek(0)
                with open(save_file_path, 'wb') as f:
                    shutil.copyfileobj(file, f)
            except ValueError as e:
                if 'closed file' in str(e):
                    with open(file.filename, 'rb') as reopened_file:
                        with open(save_file_path, 'wb') as f:
                            shutil.copyfileobj(reopened_file, f)
                else:
                    raise
        logger.info("File successfully written to disk")

        file_id = self._perform_database_operations(original_filename, file_path, collection_id)
        return file_id, "File uploaded successfully."

    def _gen_message(self, event, payload : dict) -> str:
        message = dict()
        message.update(payload)
        message = json.dumps(message)
        return f"event: {event}\ndata: {message}\n\n"

    def _create_thread(self):
        thread_payload = dict(user_id=self.user_id, organization_id=self.organization_id, module='DOC_ANALYSIS')
        thread = chats_helper.create_thread(thread_payload)
        return thread['thread_id']

    def _get_file_path(self, file_id):
        file = db_helper.find_one(queries.FIND_FILES_BY_FILES_IDS, [file_id])
        file_name = file.get('file_name')
        return os.path.join(config.ORGDIR_PATH, self.organization_name, file_name)

    def _get_sheets_from_file(self, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.csv':
            df = pd.read_csv(file_path)
            return [('Sheet1', df)]
        elif file_extension in ['.xls', '.xlsx']:
            xlsx = pd.ExcelFile(file_path)
            return [(name, pd.read_excel(xlsx, sheet_name=name)) for name in xlsx.sheet_names]
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _read_file(self, file_path, nrows):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.csv':
            return pd.read_csv(file_path, nrows=nrows)
        elif file_extension in ['.xls', '.xlsx']:
            return pd.read_excel(file_path, nrows=nrows)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _categorize_query(self, query, thread_id):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        categorise_qual_needed_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_CATEGORISE_QUAL_NEEDED)

        user_content = f"USER QUESTION:\n{query}\n\n"
        previous_chat_context = self._fetch_previous_chat_history(thread_id, 7)

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
        response = json.loads(openai_helper.callai_json(
            system_content=categorise_qual_needed_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        logger.info(f"Response from categorize query: {response}")
        if not response or response.get('category') not in ['1', '2', '3']:
            logger.error("Received empty/invalid response from categorize query defaulting to Quantitative")

        cat = response.get('category', '2')
        if cat not in ['1', '2', '3']:
            cat = '2'

        if cat == '1':
            return self.CATEGORY.QUALITATIVE
        elif cat == '2':
            return self.CATEGORY.QUANTITATIVE
        else:
            return self.CATEGORY.SEARCH

    """ def _id_relevant_tables(self, query, db_uri, thread_id):

        db_uri_parts = db_uri.split('/')
        schema_name = db_uri_parts[-1]

        get_tables_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'"
        tables = db_helper.find_collection_db_many(get_tables_query, db_uri)
        tables_str = [f"{schema_name}.{','.join(table.values())}" for table in tables]
        identify_tables_prompt_text = f"
            Given the user query, identify the tables that are relevant to the user query.
            {tables_str}
            Give the output as a JSON array of table names for the field 'tables'.
        "

        user_content = f"USER QUERY:\n{query}\n\n"
        previous_chat_context = self._fetch_previous_chat_history(thread_id, 7)

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
        response = json.loads(openai_helper.callai_json(
            system_content=identify_tables_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        logger.info(f"Response from identify tables: {response}")
        if not response or response.get('tables') is None:
            logger.error("Received empty/invalid response from identify tables")

        return response.get('tables', []) """
    
    def _id_relevant_tables(self, query, db_uri, thread_id, collection_id):
        db_uri_parts = db_uri.split('/')
        if 'postgres' in db_uri or 'postgresql' in db_uri:
            schema_name = db_uri_parts[-1]  # Schema name is the last part
        else:
            schema_name = None  # No schema name for MySQL

        # Modify the query to use the correct schema name
        if schema_name:
            get_tables_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'"
        else:
            get_tables_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{db_uri_parts[-1]}'"

        tables_df = db_helper.find_collection_db_many(get_tables_query, db_uri)
        if not tables_df.empty:
            if schema_name:
                tables_str = [f"{schema_name}.\"{row['table_name']}\"" for index, row in tables_df.iterrows()]
            else:
                tables_str = [f"`{row['table_name']}`" for index, row in tables_df.iterrows()]
        else:
            tables_str = []

        print(f"@@@@@@@@@@@@@@@@@@@@@@@Tables string: {tables_str}")
        custom_instructions = db_helper.find_one(queries.FIND_CUSTOM_INSTRUCTIONS_BY_COLLECTION_ID, collection_id)
        if (custom_instructions == None or custom_instructions == ''):
            custom_instructions = ''
        else:
            custom_instructions = f"INSTRUCTIONS ABOUT THE DATA:\n{custom_instructions}"

        identify_tables_prompt_text = f"""
            Given the user query, identify the tables that are relevant to the user query.
            {tables_str}

            Details about the Tables:
            {custom_instructions}
            Give the output as a JSON array of table names for the field 'tables'.
        """

        user_content = f"USER QUERY:\n{query}\n\n"
        previous_chat_context = self._fetch_previous_chat_history(thread_id, 7)

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
        response = json.loads(openai_helper.callai_json(
            system_content=identify_tables_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        logger.info(f"Response from identify tables: {response}")
        if not response or response.get('tables') is None:
            logger.error("Received empty/invalid response from identify tables")

        return response.get('tables', [])

    def _find_code(self, query, collection_id):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        code_gen_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_FIND_CODE_FROM_FAQ)
        #find all faq_ids for the given query for the collection
        faqs = db_helper.find_many(queries.FIND_FAQ_IDS_BY_QUERY, collection_id)
        print(f"@@@@@@@@@@@@@@@@@@@@@@@@faqs: {faqs}")
        user_content = f"""
            User Query:
            {query}

            Candidate User queries with faq_id:
        """
        for faq in faqs:
            user_content += f"""
                FAQ ID: {faq.get('faq_id')}
                User query: {faq.get('query')}
            """
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_02)
        response = json.loads(openai_helper.callai_json(
            system_content=code_gen_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=[]
        ))

        faq_id = response.get('faq_id', '')
        logger.info(f"\n{faq_id}")
        code = ''
        if faq_id != '':
            for faq in faqs:
                if str(faq.get('faq_id')) == str(faq_id):
                    code = faq.get('script')
                    print("@@@@@@@@@@@@@ FAQ item found")
                    break
        return code, faq_id

    def _generate_code(self, category, query, thread_id, file_ids, collection_id, db_uri, gsheets_credentials_file_path, gsheet_ids_and_worksheets, custom_instructions):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')

        if category == self.CATEGORY.SEARCH:
            code_gen_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_CODE_GEN_FUZZY_INSTRUCTIONS)
        elif category == self.CATEGORY.QUALITATIVE:
            code_gen_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_CODE_GEN_FILTERING)
        elif category == self.CATEGORY.QUANTITATIVE:
            code_gen_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_CODE_GEN_PROCESSING_CODE_SPECS)

        #Get custom instructions for the Collection
        if custom_instructions == None:
            custom_instructions = db_helper.find_one(queries.FIND_CUSTOM_INSTRUCTIONS_BY_COLLECTION_ID, collection_id)
        if (custom_instructions == None or custom_instructions == ''):
            custom_instructions = ''
        else:
            custom_instructions = f"INSTRUCTIONS ABOUT THE DATA:\n{custom_instructions}"

        user_content = f"""
            USER QUESTION:
            {query}
            {custom_instructions}
        """

        file_path = []
        for file_id in file_ids:
            file_path.append(self._get_file_path(file_id))
            df = self._read_file(file_path[len(file_path) - 1], nrows=100)

            data_header = df.columns.tolist()
            sample_data = df.head(2).to_dict('records')
            user_content += f"""
                Full File Path of the File:
                {file_path[len(file_path) - 1]}

                DATA HEADER:
                {data_header}

                DATA SAMPLE:
                {sample_data}
            """
        """ if db_uri is not None:
            relevant_tables = self._id_relevant_tables(query, db_uri, thread_id)
            if relevant_tables:
                for table in relevant_tables:
                    #load the header and first 2 rows of table data onto pandas dataframe
                    query = f"SELECT * FROM {table} LIMIT 2"
                    rows = db_helper.find_collection_db_many(query, db_uri)
                    table_previews = {}
                    if rows:
                        print(f"############# ROWS: {rows}")
                        table_previews[table] = pd.DataFrame(rows)
                        
                        #data_header = table_previews[table].columns.tolist()
                        # Get column names from information_schema.columns
                        if 'postgres' in db_uri or 'postgresql' in db_uri:
                            schema_name = db_uri.split('/')[-1]
                            column_query = f"
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_schema = '{schema_name}' AND table_name = '{table}'
                            "
                        else:
                            column_query = f"
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}'
                            "
                        
                        column_names = db_helper.find_collection_db_many(column_query, db_uri)
                        data_header = [col['column_name'] for col in column_names]

                        sample_data = table_previews[table].head(2).to_dict('records')
                        user_content += f"
                            TABLE NAME:
                            {table}
                            
                            DATA HEADER:
                            {data_header}

                            DATA SAMPLE:
                            {sample_data}
                        "
        """

        if db_uri is not None:
            relevant_tables = self._id_relevant_tables(query, db_uri, thread_id, collection_id)
            if relevant_tables:
                for table in relevant_tables:
                    # Load the header and first 2 rows of table data onto pandas dataframe
                    query = f"SELECT * FROM {table} LIMIT 2"
                    rows_df = db_helper.find_collection_db_many(query, db_uri)
                    table_previews = {}
                    if not rows_df.empty:
                        print(f"############# ROWS: {rows_df}")
                        table_previews[table] = rows_df
                        
                        # Get column names from information_schema.columns
                        if 'postgres' in db_uri or 'postgresql' in db_uri:
                            schema_name = db_uri.split('/')[-1]
                            column_query = f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_schema = '{schema_name}' AND table_name = '{table}'
                            """
                        else:
                            column_query = f"""
                                SELECT column_name 
                                FROM information_schema.columns 
                                WHERE table_name = '{table}'
                            """
                        
                        column_names_df = db_helper.find_collection_db_many(column_query, db_uri)
                        if not column_names_df.empty:
                            data_header = column_names_df['column_name'].tolist()
                        else:
                            data_header = []

                        sample_data = table_previews[table].head(2).to_dict('records')
                        user_content += f"""
                            TABLE NAME:
                            {table}
                            
                            DATA HEADER:
                            {data_header}

                            DATA SAMPLE:
                            {sample_data}
                        """

        if gsheets_credentials_file_path is not None:
            # read file contents from file in path gsheets_credentials_file_path using file read function
            with open(gsheets_credentials_file_path, 'r') as file:
                credentials_json = json.loads(file.read())
            # gsheet_ids_and_worksheets[SPREADSHEET_ID] = {'name': SPREADSHEET_NAME, 'worksheets': sheet_names}
            for gsheet_id in gsheet_ids_and_worksheets:
                print(f"@@@@@@@@@@@@@@@@@@@@@@@gsheet_id: {gsheet_id}")
                gdrive_service = GoogleDriveHelper(credentials_json)
                sheet_names = gdrive_service.get_worksheets(gsheet_id)
                spreadsheet_name = gdrive_service.get_filename(gsheet_id)
                for sheet in sheet_names:
                    RANGE_NAME = sheet
                    values = gdrive_service.get_worksheet_values(gsheet_id, RANGE_NAME)
                    if not values:
                        raise ValueError("No data found in the Google Sheet.")

                    # Extract the header and sample data
                    data_header = values[0] if len(values) > 0 else []
                    sample_data = values[1:3] if len(values) > 1 else []

                    user_content += f"""
                        Spreadsheet Name:
                        {spreadsheet_name}

                        Google Worksheet NAME:
                        {RANGE_NAME}
                        
                        Worksheet HEADER:
                        {data_header}

                        Worksheet row SAMPLE:
                        {sample_data}
                    """
        """ extension = os.path.splitext(file_path)[1].lower()
        code_gen_prompt_text += f"\n\nThis file has an extension of {extension}, so keep this in mind when using Pandas.\n" """


        previous_chat_context = self._fetch_previous_chat_history(thread_id, 7)

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_02)
        response = json.loads(openai_helper.callai_json(
            system_content=code_gen_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        code = response.get('code', '')
        logger.info(f"\n{code}")
        if not code:
            raise ValueError("Received empty code response")

        #if code is an empty string, try once more
        if (code == ''):
            response = json.loads(openai_helper.callai_json(
                system_content=code_gen_prompt_text,
                user_content=user_content,
                user_id=str(self.user_id) or 'admin',
                extra_context=previous_chat_context
            ))
            code = response.get('code', '')
            logger.info(f"\n{code}")
            if not code:
                raise ValueError("Received empty code response")

        return code.replace("echo(", "print(")

    def _improve_code(self, thread_id, code, error):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')

        code_gen_prompt_text = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_IMPROVE_CODE)

        user_content = f"Code execution resulted in this error:\n{error}\nPlease rewrite the code to fix the error.\n\n"

        previous_chat_context = self._fetch_previous_chat_history(thread_id, 7)

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_02)
        response = json.loads(openai_helper.callai_json(
            system_content=code_gen_prompt_text,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        code = response.get('code', '')
        logger.info(f"\n{code}")
        if not code:
            raise ValueError("Received empty code response")

        #if code is an empty string, try once more
        if (code == ''):
            response = json.loads(openai_helper.callai_json(
                system_content=code_gen_prompt_text,
                user_content=user_content,
                user_id=str(self.user_id) or 'admin',
                extra_context=previous_chat_context
            ))
            code = response.get('code', '')
            logger.info(f"\n{code}")
            if not code:
                raise ValueError("Received empty code response")

        return code.replace("echo(", "print(")

    def _explain_code(self, code):
        user_content = f"Code:\n{code}"
        previous_chat_context = []

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_01)
        response = json.loads(openai_helper.callai_json(
            system_content=f"""
                Explain what is being done by the code using 2 paras. In the first short para of 20-25 words Explain what is being done by the code, without referring to the approach being used as running code etc as it will confuse the user. Start with the phrase 'Here is what I am doing to respond to your query:'. In the 2nd para, list the key files, if any and tables, if any and fields used in the code. If files are there, mention just the file names. Don't mention full filepaths.
                Under no circumstance should you mention anything related to db_uri or how the authentication is done or any other such technical details.
                Give the explanation as a JSON in a field named 'explanation'. Keep it non-technical. 
            """,
            user_content=user_content,
            user_id=str(self.user_id) or 'admin',
            extra_context=previous_chat_context
        ))

        result = response.get('explanation', 'I am processing the input data to respond to your query.')
        return result

    def _execute_code(self, query_code, db_uri=None, gsheets_credentials_file_path=None, spreadsheet_ids=None):
        print(f"@@@@@@@@@@@@@@@@@@@@@@@@db_uri, gsheets_credentials_file_path, spreadsheet_ids: {db_uri}, {gsheets_credentials_file_path}, {spreadsheet_ids}")
        user_path = os.path.join('docanalysis', str(self.user_id))
        os.makedirs(user_path, exist_ok=True)
        temp_script_path = os.path.join(user_path, 'scripts', 'temp_script.py')
        os.makedirs(os.path.dirname(temp_script_path), exist_ok=True)

        with open(temp_script_path, "w", encoding="utf-8") as f:
            f.write(query_code)

        #logger.info(f"Temp script path: {temp_script_path}\nFile path: {file_path}")
        logger.info(f"Temp script path: {temp_script_path}")

        #delete old chart.png if it exists
        chart_folder_path = os.path.join(user_path, 'charts')
        os.makedirs(chart_folder_path, exist_ok=True)
        chart_path = os.path.join(chart_folder_path, 'chart.png')
        if os.path.exists(chart_path):
            os.remove(chart_path)

        try:
            # Prepare command arguments
            cmd_args = [sys.executable, temp_script_path, chart_path]

            # Handle database URI if provided
            if db_uri is not None:
                # For PostgreSQL, remove schema name from URI
                if db_uri is not None:
                    db_uri_parts = db_uri.split('/')
                    db_uri = '/'.join(db_uri_parts[:-1])
                cmd_args.insert(2, db_uri)
            else:
                cmd_args.insert(2, 'NA')

            # Handle Google Sheets credentials if provided
            if gsheets_credentials_file_path is not None and spreadsheet_ids is not None:
                cmd_args.extend([gsheets_credentials_file_path, spreadsheet_ids])

            # Execute the code in a subprocess with timeout
            result = subprocess.run(
                cmd_args,
                check=True,
                capture_output=True,
                text=True,
                timeout=180  # 3 minutes timeout
            )

            logger.info(f"Script execution completed. Stderr: {result.stderr}")

            logger.info(f"Result from code execution: {result}")

            # Check if the script generated a Matplotlib chart
            image_data = ''
            if os.path.exists(chart_path):
                logger.info(f"Chart generated at: {chart_path}")
                with open(chart_path, "rb") as image_file:
                    image_data = base64.b64encode(image_file.read()).decode('utf-8')
            return result.stdout, result.stderr, result.returncode, image_data

        except subprocess.TimeoutExpired:
            logger.error("Script execution timed out after 3 minutes")
            return "", "Script execution timed out after 3 minutes", 1, ""
        except subprocess.CalledProcessError as e:
            logger.error(f"Script execution failed with exit code {e.returncode}: {e.stderr}")
            #return e.stdout, e.stderr, e.returncode, ""
            raise e
        except Exception as e:
            logger.error(f"Error executing code: {str(e)}", exc_info=True)
            #return "", str(e), 1, ""
            raise e

    def _process_qualitative_output(self, stdout, query, thread_id, code):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        output_format_prompt = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_OUTPUT_FORMAT)

        total_char_count = len(stdout)
        print(f"Total char count: {total_char_count}")
        lines = stdout.splitlines()
        header = lines[0]
        previous_result = ""
        max_char_count = config.DOCANALYSIS_MAX_CHAR_COUNT
        print(f"Max char count: {max_char_count}")
        current_index = 1

        msg = f"Since the data volume is high, I need to process this in chunks.\nRough number of times I need to loop: {max(round(total_char_count / max_char_count), 1)}"
        yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)

        cumulative_chunk_str_length = 0
        while current_index <= len(lines):
            chunk_str, last_index = self._get_chunk_with_header(lines, max_char_count, current_index)
            cumulative_chunk_str_length += len(chunk_str)
            print(f"Current index: {current_index}, Last index: {last_index}, Cumulative chunk str length: {cumulative_chunk_str_length}")
            current_index = last_index + 1

            format_user_content = f"\nUSER QUESTION:\n{query}\n\nCODE OUTPUT:\n{chunk_str} \n\nPREVIOUS RESULT:\n{previous_result}"

            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_03)
            response = openai_helper.callai_json(output_format_prompt, format_user_content, self.user_id or "admin")

            format_response = json.loads(response)
            formatted_answer = format_response.get('output', '')
            previous_result = formatted_answer

            progress_percentage = int(round((cumulative_chunk_str_length / total_char_count) * 100))
            print(f"Progress percentage: {progress_percentage}")
            msg = f"Progress: {str(progress_percentage)}%"
            yield self._sse_response(StreamEvent.PROGRESS_EVENT, msg, False, thread_id)

            if current_index == len(lines):
                break

        if not formatted_answer:
            raise ValueError("Received empty output response")

        self._add_assistant_chat_history(query, formatted_answer, thread_id, code)
        yield self._sse_response(StreamEvent.FINAL_OUTPUT, formatted_answer, False, thread_id)

    def _process_quantitative_output(self, stdout, query, thread_id, code):
        docanalysis_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docanalysis')
        output_format_prompt = self._get_prompt_text(docanalysis_prompts, Prompts.DOCANALYSIS_CODE_GEN_PROCESSING_OUTPUT_FORMATTING)

        lines = stdout.splitlines()
        header = lines[0]
        previous_result = ""
        max_char_count = config.DOCANALYSIS_MAX_CHAR_COUNT
        current_index = 1

        while current_index <= len(lines):
            chunk_str, last_index = self._get_chunk_with_header(lines, max_char_count, current_index)
            current_index = last_index + 1

            format_user_content = f"\nUSER QUESTION:\n{query}\n\nCODE OUTPUT:\n{chunk_str} \n\nPREVIOUS RESULT:\n{previous_result}"

            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_ANALYSIS_03)
            response = openai_helper.callai_json(output_format_prompt, format_user_content, self.user_id or "admin")

            format_response = json.loads(response)
            formatted_answer = format_response.get('output', '')
            previous_result = formatted_answer

            progress_percentage = int(round((current_index / len(lines)) * 100))
            yield self._sse_response(StreamEvent.PROGRESS_OUTPUT, str(progress_percentage), False, thread_id)

            if current_index == len(lines):
                break

        if not formatted_answer:
            raise ValueError("Received empty output response")

        self._add_assistant_chat_history(query, formatted_answer, thread_id, code)
        yield self._sse_response(StreamEvent.FINAL_OUTPUT, formatted_answer, False, thread_id)

    def _delete_file_associations(self, file_ids):
        db_helper.execute(queries.DELETE_FROM_FILES_COLLECTION_BY_FILE_ID, file_ids)

    def _delete_file_records(self, file_ids):
        db_helper.execute(queries.DELETE_FILES_BY_FILE_ID, file_ids)
        db_helper.execute(queries.DELETE_FILES_METADATA_BY_FILE_ID, file_ids)
        db_helper.execute(queries.DELETE_FILES_METADATA_PLUS_BY_FILE_ID, file_ids)

    def _delete_files_from_disk(self, files):
        deleted_files = []
        for file in files:
            file_id = file.get('file_id')
            file_name = file.get('file_name')
            file_path = os.path.join(config.ORGDIR_PATH, self.organization_name, file_name)

            if not os.path.exists(file_path):
                logger.warning(f"File not found on disk: {file_path}")
                continue

            try:
                os.remove(file_path)
                logger.info(f"File successfully deleted from disk: {file_path}")
                deleted_files.append(file_id)
            except OSError as e:
                logger.error(f"Error deleting file {file_path}: {e}")

        return deleted_files

    def _fetch_previous_chat_history(self, thread_id, history_count=7):
        chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(thread_id, self.user_id)
        if not chat_thread:
            logger.warning(f"No chat history found for thread_id: {thread_id}")
            return []

        chat_history = chat_thread.get('messages')
        filtered_chat_history = list(filter(lambda chat: chat.get('role') != 'action', chat_history))
        previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                 filtered_chat_history[-history_count:] if len(filtered_chat_history) > 1]
        return previous_chat_context

    def _get_prompt_text(self, prompts, prompt_name):
        prompt = next((p for p in prompts if p.get('prompt_name') == prompt_name), None)
        if not prompt:
            raise ValueError(f"{prompt_name} prompt not found")
        return prompt.get('prompt_text', '')

    def _get_full_prompt_text(self, prompts, prompt_names, file_path):
        prompt_names.append(self._get_input_file_prompt(prompts, file_path))
        return ''.join(self._get_prompt_text(prompts, name) for name in prompt_names)

    def _get_input_file_prompt(self, prompts, file_path):
        file_extension = os.path.splitext(file_path)[1].lower()
        logger.info(f"File extension: {file_extension}")
        if file_extension == '.csv':
            return Prompts.DOCANALYSIS_CODE_GEN_INPUT_FILE_CSV
        elif file_extension in ['.xls', '.xlsx']:
            return Prompts.DOCANALYSIS_CODE_GEN_INPUT_FILE_XLSX
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def _get_chunk_with_header(self, lines, max_char_count, start_index=1):
        header = lines[0]
        chunk = [header] if header else []
        total_char_count = len(header) + 1 if header else 0
        last_line_index = start_index - 1

        for index in range(start_index, len(lines)):
            line = lines[index]
            line_length = len(line) + 1

            if line_length > max_char_count:
                fields = line.split(',')
                for i, field in enumerate(fields):
                    if len(field) > 10000:
                        fields[i] = field[:10000]
                        break
                line = ','.join(fields)
                line_length = len(line) + 1

            if total_char_count + line_length > max_char_count:
                break

            chunk.append(line)
            total_char_count += line_length
            last_line_index = index

        if last_line_index == start_index - 1 and len(lines) > 1:
            last_line_index = start_index

        chunk_str = "\n".join(chunk)
        return chunk_str, last_line_index

    def _add_assistant_chat_history(self, query, message, thread_id, code):
        try:
            self._add_user_chat_history(query, thread_id)

            assistant_chat_payload = dict(role='assistant',generated_code=True, content=code)
            chats_helper.add_chat_history(thread_id, assistant_chat_payload)

            assistant_chat_payload = dict(role='assistant', content=message)
            chats_helper.add_chat_history(thread_id, assistant_chat_payload)
        except Exception as e:
            logger.error(f"Error adding assistant chat history: {e}")
            raise e

    def _add_user_chat_history(self, query, thread_id):
        try:
            user_chat_payload = dict(role='user', content=query)
            chats_helper.add_chat_history(thread_id, user_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    @staticmethod
    def _sse_response(event, message, retry, thread_id, image_data=None, faq_id=None):
        data = {'message': message}
        if event == StreamEvent.FINAL_OUTPUT:
            data = {'message': message, 'retry': retry, 'thread_id': thread_id}
            data['table'] = True if message.find("<table") != -1 else False
            if faq_id is not None and faq_id != '':
                data['faq_id'] = faq_id
            else:
                data['faq_id'] = 0

        if image_data:
            data['image_data'] = image_data

        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"
