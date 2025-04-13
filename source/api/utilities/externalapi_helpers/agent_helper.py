import json, os
import logging
import re
from urllib.parse import urlparse
import yaml

import pandas as pd

from flask import request
from openai import OpenAI

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, Prompts, StreamEvent, ChatFileCategory, AGENT_TOOLS
from source.api.utilities.externalapi_helpers import chats_helper
from source.api.endpoints.doc_analysis.helpers import DocAnalysis
from source.api.utilities.externalapi_helpers.googledrive_helper import GoogleDriveHelper
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.common import config

from rank_bm25 import BM25Okapi
from collections import Counter
import fitz

from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords

from google.oauth2 import service_account
from googleapiclient.discovery import build

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# NOTE: Do not use, already gets downloaded in the dockerfile
# on local machine, use "python -m nltk.downloader punkt punkt_tab stopwords"

# nltk.data.path.append(os.path.join('data', 'nltk_data'))
# nltk.download('punkt')
# nltk.download('punkt_tab')
# nltk.download('stopwords')

logger = logging.getLogger('app')

def chat_query(query = None, collection_id = None, thread_id = None, selected_file_ids = None):
    try:
        if 'organization_id' not in request.context:
            logger.error("Organization ID is missing in request context")
            raise RuntimeError('Organization ID is required!')

        organization_id = request.context['organization_id']
        orgname = request.context['organization_name']
        if orgname is None:
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']

        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='ASK_DOC')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']

        manager = AgentManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.user_current_role = db_helper.find_one(queries.FIND_USER_ROLE, user_id) or {}
        manager.query = query
        manager.collection_id = collection_id
        manager.thread_id = thread_id
        if selected_file_ids is not None:
            manager.selected_file_ids = selected_file_ids

        #moved these 4 steps from init_chat_query to here
        manager.fetch_query_data()
        manager.fetch_previous_chat_history()
        manager.add_user_chat_history()
        manager.decide_control_flow()
        print(manager.control_sequence)

        return manager.init_chat_query()
    except Exception as e:
        logger.error(f'Error in chat_query: {str(e)}')
        raise e

# query suggestions related functions - BEGIN
def get_suggestions(query, collection_id, thread_id, selected_file_ids):
    try:
        if 'organization_id' not in request.context:
            logger.error("Organization ID is missing in request context")
            raise RuntimeError('Organization ID is required!')

        organization_id = request.context['organization_id']
        orgname = request.context['organization_name']
        if orgname is None:
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']

        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='ASK_DOC')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']

        manager = AgentManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.user_current_role = db_helper.find_one(queries.FIND_USER_ROLE, user_id) or {}
        manager.query = query
        manager.collection_id = collection_id
        manager.thread_id = thread_id
        if selected_file_ids is not None:
            manager.selected_file_ids = selected_file_ids

        manager.fetch_query_data()
        manager.fetch_previous_chat_history()

        previous_messages = manager.previous_chat_context
        existing_insights = db_helper.find_many(queries.FIND_COLLECTION_INSIGHTS_BY_COLLECTION_ID, collection_id)
        existing_queries = [insight['query'] for insight in existing_insights]
        context = {
            "files": manager.file_name,
            "existing_queries": existing_queries,
            "current_user_query": manager.query
        }

        # Convert context to JSON string
        context_json = json.dumps(context)

        # Call AI to identify one new insight query
        response = json.loads(manager.openai_helper.callai_json(
            system_content = f""" Your task is to identify relevant User query suggestions. Use the files list, the past user queries and responses in the Context provided for this.
            Use the past User queries as cues but the new query should be different from these. 
            Return one, or maximum two suggestions.
            Keep the word count of the suggestions to a maximum of 10 words.
            Return the output as a JSON in the following format: 
            {{'query_suggestions': ['<suggestion-1>', '<suggestion-2>']}}.
            {context_json}
            """,
            user_content='',
            extra_context=previous_messages,
            user_id=manager.user_id
        ))
        # Parse the response to get the new insight query
        suggestions = response.get('query_suggestions', [])
        return suggestions

    except Exception as e:
        logger.error(f'Error in ask_doc_query: {str(e)}')
        raise e

# query suggestions related functions - END

class AgentManager:
    def __init__(self, portkey_config=PortKeyConfigs.NEW_CHAT_01):
        logger.info("Initializing AgentManager")
        self.openai_helper = OpenAIHelper(portkey_config=portkey_config)
        self.vector_search = None

        self.organization_id = None
        self.orgname = None
        self.user_id = None
        self.query = None
        self.answer = None
        self.current_step_query = None
        self.collection_id = None
        self.selected_file_ids = None
        self.file_ids = []
        self.text_file_ids = []
        self.spreadsheet_file_ids = []
        self.tables = []
        self.file_name = {}
        self.file_path = {}
        self.file_title = {}
        self.file_summary_short = {}
        self.gsheet_ids_and_worksheets = {}
        self.collection = None
        self.collection_name = None
        self.user = None
        self.username = None
        self.user_current_role = {}
        self.prompts = None
        self.custom_instructions = None
        self.system_content = None
        self.thread_id = None
        self.final_message = None
        self.previous_chat_context = None
        self.final_message_extra_metadata = {}
        self.control_sequence = []
        self.previous_step_output = ''
        logger.info("AgentManager initialized")

    def init_chat_query(self):
        #TODO: Jobs dont use SSE. So remove the legacy usage of SSE and that will simplify a lot of the code. SSE was for the chat.
        try:
            generators = []
            for i in range(len(self.control_sequence['steps'])):
                #last_step = i == len(self.control_sequence['steps']) - 1
                file_category = self.control_sequence['steps'][i]['file_category']
                tool_id = self.control_sequence['steps'][i].get('tool_id', '')
                logger.debug(f"Iteration: {i}. File category: {file_category}")
                if (tool_id == AGENT_TOOLS.Text_Document_Processing) or (not tool_id and (file_category == ChatFileCategory.TEXT_FILES or file_category == ChatFileCategory.PREVIOUS_OUTPUT)):
                    def text_generator():
                        self.current_step_query = f"""
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                            Output of Previous Step:
                            {self.previous_step_output}
                        """
                        if file_category == ChatFileCategory.TEXT_FILES:
                            self.prepare_context()
                        elif file_category == ChatFileCategory.PREVIOUS_OUTPUT:
                            self.system_content = ""
                        self.fetch_previous_chat_history()
                        return self.generate_response()
                    generators.append(text_generator)
                elif (tool_id == AGENT_TOOLS.Metadata_Generator):
                    def text_generator():
                        self.current_step_query = f"""
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                            Output of Previous Step:
                            {self.previous_step_output}
                        """
                        return self.build_csv_from_files()
                    generators.append(text_generator)
                elif (tool_id == AGENT_TOOLS.Filter_Files):
                    def text_generator():
                        self.current_step_query = f"""
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                            Output of Previous Step:
                            {self.previous_step_output}
                        """
                        return self.filter_files()
                    generators.append(text_generator)
                elif (tool_id == AGENT_TOOLS.Data_Analysis) or (not tool_id and file_category == ChatFileCategory.SPREADSHEET_FILES):
                    def spreadsheet_generator():
                        doc_analysis = DocAnalysis(self.organization_id, self.orgname, self.user_id)
                        self.current_step_query = f"""
                            Output of Previous Step:
                            {self.previous_step_output}
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                        """
                        return doc_analysis.execute_file_analysis(self.collection_id, self.spreadsheet_file_ids, self.current_step_query, self.thread_id, self.collection['db_uri'], self.collection['gsheets_credentials_file_path'], self.gsheet_ids_and_worksheets, self.custom_instructions)
                    generators.append(spreadsheet_generator)
                    """ elif file_category == ChatFileCategory.PREVIOUS_OUTPUT:
                    #eventually the query to just process previous output and to handle questions on list of files and tables needs a separate branch. currently just keeping it together.
                    print("Previous output generator")
                    def prev_output_generator():
                        " self.current_step_query = f"
                            List of Files:
                            {self.file_name}
                            Details about the files:
                            {self.get_file_details()}
                            List of Tables:
                            {self.tables}
                            More Details about the Files:
                            {self.custom_instructions['custom_instructions']}
                            Output of Previous Step:
                            {self.previous_step_output}
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                        " "
                        self.current_step_query = f"
                            Output of Previous Step:
                            {self.previous_step_output}
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                        "
                        #self.prepare_context()
                        self.system_content = ""
                        self.fetch_previous_chat_history()
                        return self.generate_response()
                    generators.append(prev_output_generator) """
                elif tool_id == AGENT_TOOLS.Send_Email:
                    def email_generator():
                        print(f"@@@@@@@@@@@@@@@@@@@@Self.query: {self.query}")
                        if self.previous_step_output:
                            email_details = self.yaml_to_dict(self.query)
                            subject = email_details.get('email_subject', 'Report')
                            email_list = self.extract_emails(email_details.get('email_to', ''))
                            print(f"@@@@@@@@@@@@@@@ Subject: {subject}")
                            print(f"@@@@@@@@@@@@@@@ Email List: {email_list}")

                            sender_email = 'info@nlightn.in'
                            sender_password = os.getenv('GMAIL_PWD')

                            self.send_html_email(email_list, subject, self.previous_step_output, sender_email, sender_password)
                            return f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {json.dumps({'message': 'Email Sent', 'thread_id': self.thread_id})}\n\n"
                        else:
                            return f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {json.dumps({'message': 'Email not sent as the previous step output is empty.', 'thread_id': self.thread_id})}\n\n"

                    generators.append(email_generator)
                elif file_category.lower() == "none":
                    def none_generator():
                        """ self.current_step_query = f"
                            List of Files:
                            {self.file_name}
                            Details about the files:
                            {self.get_file_details()}
                            List of Tables:
                            {self.tables}
                            More Details about the Files:
                            {self.custom_instructions['custom_instructions']}
                            Output of Previous Step:
                            {self.previous_step_output}
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                        " """
                        self.current_step_query = f"""
                            Output of Previous Step:
                            {self.previous_step_output}
                            User query:
                            {self.control_sequence['steps'][i]['user_query']}
                        """
                        #self.prepare_context()
                        self.system_content = ""
                        self.fetch_previous_chat_history()
                        return self.generate_response()
                    generators.append(none_generator)
                else:
                    def else_generator():
                        return f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {json.dumps({'message': 'Sorry, I am not able to answer this query. Please try again with a different query.', 'thread_id': self.thread_id})}\n\n"
                    generators.append(else_generator)

            # Iterate through the chosen generator
            num_steps = len(self.control_sequence['steps'])
            i = -1
            for generator_function in generators:
                i += 1
                last_step = i == len(generators) - 1
                for response in generator_function():
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
                        logger.info(f"Event: {event}, Num steps: {num_steps}, Last step: {last_step}")
                        print("data: ", data)
                    if (event == StreamEvent.PROGRESS_EVENT):
                        #yield self._sse_response(event,data,False, self.thread_id)
                        yield f"event: {event}\ndata: {data}\n\n"
                    elif (num_steps == 1):
                        yield f"event: {event}\ndata: {data}\n\n"
                    elif (event == StreamEvent.CHUNK):
                        yield f"event: {event}\ndata: {data}\n\n"
                    elif (event == StreamEvent.FINAL_OUTPUT) and last_step:
                            """ system_content = f"
                                Your Task:
                                Look at the output of the different steps and arrive at a coherent response for the User query.
                                
                                Output of previous step:
                                {self.previous_step_output}

                                Output of current step:
                                {data}

                                User query:
                                {self.query}
                            "
                            self.fetch_previous_chat_history()
                            previous_messages = self.previous_chat_context
                            repeat_count = 2
                            username = self.username
                            response = self.openai_helper.callai(system_content=system_content, user_content=self.query, user_id=username, extra_context=previous_messages)
                            
                            data = json.dumps({"message": response}) """
                            print(f"################################# FINAL MESSAGE: \n{data}")
                            yield f"event: {event}\ndata: {data}\n\n"
                            #yield self._sse_response(event,data,False, self.thread_id)
                    else: #(event == StreamEvent.FINAL_OUTPUT) and not last_step:
                        self.previous_step_output = data
                        #now send the temp_output also to the next step and modify those to include the temp output in the context
            if (generators == []):
                if (self.answer):
                    #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {json.dumps({'message': self.answer, 'thread_id': self.thread_id})}\n\n"
                    yield self._sse_response(StreamEvent.FINAL_OUTPUT,self.answer,False, self.thread_id)
                else:
                    #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {json.dumps({'message': 'Sorry, I am not able to answer this query. Please try again with a different query.', 'thread_id': self.thread_id})}\n\n"
                    yield self._sse_response(StreamEvent.FINAL_OUTPUT,'Sorry, I am not able to answer this query. Please try again with a different query.',False, self.thread_id)
        except Exception as e:
            logger.error(f"Error in control flow execution: {e}")
            last_step = True
            #error_msg = json.dumps({"message": e})
            #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {error_msg}\n\n"
            yield self._sse_response(StreamEvent.FINAL_OUTPUT,e,False, self.thread_id)

    def yaml_to_dict(self, yaml_str):
        try:
            result = yaml.safe_load(yaml_str)
            if isinstance(result, dict):
                # Convert all keys to lowercase
                lowercase_result = {k.lower(): v for k, v in result.items()}
                return lowercase_result
            else:
                raise ValueError("YAML does not contain a dictionary at the top level.")
        except yaml.YAMLError as e:
            print("❌ YAML parsing error:", e)
            return {}

    def extract_emails(self, text):
        # Basic regex pattern for matching most email addresses
        pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
        return re.findall(pattern, text)

    def send_html_email(self, email_list, subject, html_content, sender_email, sender_password):
        smtp_server = "smtp.gmail.com"
        smtp_port = 587

        for recipient in email_list:
            # Compose the email
            msg = MIMEMultipart("alternative")
            msg['From'] = sender_email
            msg['To'] = recipient
            msg['Subject'] = subject

            # Attach HTML version
            msg.attach(MIMEText(html_content, 'html'))

            try:
                with smtplib.SMTP(smtp_server, smtp_port) as server:
                    server.starttls()
                    server.login(sender_email, sender_password)
                    server.send_message(msg)
                    print(f"✅ Email sent to {recipient}")
            except Exception as e:
                print(f"❌ Failed to send to {recipient}: {e}")

    def build_csv_from_files(self):
        """
        Build a CSV file row by row by processing multiple files.

        Args:
        - files (list): List of file paths to process
        - user_query (str): Query to send with file contents
        - openai_helper: OpenAI helper object with callai_json method
        - user_id (str): User identifier
        - system_content (str): System instructions for AI

        Returns:
        - list: Completed CSV rows
        """
        try:
            list_of_jsons = []
            # Get header row first
            header_response = json.loads(self.openai_helper.callai_json(
                system_content = f"""
                Look at the User query and from it elicit the key information sought from the files. Return it as a list of field names sought. Ensure that identifying information like Name and email id are included in the field list. 
                
                If there are multiple values for a field, ensure that all are included as a csv list for that field. 
                Example: 'companies worked': ['Acme Limited', 'Pulse consultants'].
                If there is only value it should be mentioned as follows and NOT as a list:
                Example: 'name': Reese Ward

                Respond with the list in JSON format within a field called 'row'.
                """,
                user_content=self.current_step_query,  # Empty content to get header
                user_id=self.user_id
            ))

            # Add header row
            header = header_response.get('row', [])

            # Process each file
            for file_id in self.file_ids:
                # Open and read file contents using fitz (PyMuPDF)
                with fitz.open(self.file_path[file_id]) as doc:
                  file_contents = ' '.join([page.get_text() for page in doc[:20]])
                  file_contents = f"file_id: {file_id}\n{file_contents}"


                self.system_content = f"""
                    Your Task: From the File Contents extract information for each Field in Header provided. Respond in JSON format with field name from header and values. Place the JSON entry in a field called 'row'.
                """
                user_query = f"""
                Header:
                {header}
                File contents:
                {file_contents}
                """
                # Call AI to get a row for this file
                row_response = json.loads(self.openai_helper.callai_json(
                    system_content=self.system_content,
                    user_content=user_query,
                    user_id=self.user_id
                ))

                # Append row to CSV
                row = row_response.get('row', [])
                list_of_jsons.append(row)
                print(f"Row for file {file_id}: {row}")

            # Convert the list of JSONs to HTML string
            html_content = "<table>"
            # Add table headers
            headers = list(list_of_jsons[0].keys())
            html_content += "<tr>"
            for header in headers:
                html_content += f"<th>{header}</th>"
            html_content += "</tr>"

            # Add table rows
            for row in list_of_jsons:
                html_content += "<tr>"
                for header in headers:
                    cell_value = row.get(header, '')
                    html_content += f"<td>{cell_value if cell_value is not None else ''}</td>"
                html_content += "</tr>"
            html_content += "</table>"
            print(f"HTML content: {html_content}")

            yield self._sse_response(StreamEvent.FINAL_OUTPUT, html_content, False, self.thread_id)
        except Exception as e:
            logger.error(f"Error in build_csv_from_files: {e}")
            final_message = json.dumps({
                "message": "Sorry, I am having some trouble in responding at the moment. Please try again later!",
                "thread_id": self.thread_id
            })
            #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"
            yield self._sse_response(StreamEvent.FINAL_OUTPUT,"Sorry, I am having some trouble to respond at the moment. Please try again later!",False, self.thread_id)

    # Example usage
    # csv_data = build_csv_from_files(
    #     files=['/path/to/file1.pdf', '/path/to/file2.pdf'],
    #     user_query='Your specific query',
    #     openai_helper=your_openai_helper,
    #     user_id='your_user_id',
    #     system_content='Your system instructions'
    # )

    def filter_files(self):
        # this approach doesnt work. Need to first elicit metadata fields from query. then values from files. then filter and then decide. straight filtering is error prone.
        """
        Identify list of Filtered files based on criteria

        Args:
        - files (list): List of file paths to process
        - user_query (str): Query to send with file contents
        - openai_helper: OpenAI helper object with callai_json method
        - user_id (str): User identifier
        - system_content (str): System instructions for AI

        Returns:
        - list: Completed file ids
        """
        try:
            filtered_file_ids = []
            # Process each file
            for file_id in self.file_ids:
                # Open and read file contents using fitz (PyMuPDF)
                with fitz.open(self.file_path[file_id]) as doc:
                  file_contents = ' '.join([page.get_text() for page in doc])
                  file_contents = f"file_id: {file_id}\n{file_contents}"

                self.system_content = f"""
                    Your Task: 
                    1. First extract the relevant fields from the User query.
                    2. Identify the value for these fields for File from it's contents.
                    3. Use filtering value from the User query and compare it with the values obtained from the file and decide if this is file is to be selected or not. 
                    Respond in JSON format with file id in file_id field if the file is to be selected.
                    Eg: '25'. 
                    Else return an empty string ''. 
                    Place the JSON entry in a field called 'file_id'.
                """
                user_query = f"""
                Query with filter values:
                {self.query}
                File contents:
                {file_contents}
                """
                # Call AI to get a row for this file
                response = json.loads(self.openai_helper.callai_json(
                    system_content=self.system_content,
                    user_content=user_query,
                    user_id=self.user_id
                ))

                # Append row to CSV
                resp_file_id = response.get('file_id', '')
                if resp_file_id != '':
                  filtered_file_ids.append(resp_file_id)
                print(f"@@@@@@@@@@@@@@Output for {file_id}: {resp_file_id}")

            yield self._sse_response(StreamEvent.FINAL_OUTPUT, str(filtered_file_ids), False, self.thread_id)
        except Exception as e:
            logger.error(f"Error in filter_files: {e}")
            final_message = json.dumps({
                "message": "Sorry, I am having some trouble in responding at the moment. Please try again later!",
                "thread_id": self.thread_id
            })
            #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"
            yield self._sse_response(StreamEvent.FINAL_OUTPUT,"Sorry, I am having some trouble to respond at the moment. Please try again later!",False, self.thread_id)

    #insight gen related functions - BEGIN

    def _read_file(self, file_path, nrows):
        file_extension = os.path.splitext(file_path)[1].lower()
        if file_extension == '.csv':
            return pd.read_csv(file_path, nrows=nrows)
        elif file_extension in ['.xls', '.xlsx']:
            return pd.read_excel(file_path, nrows=nrows)
        else:
            raise ValueError(f"Unsupported file type: {file_extension}")

    def get_column_names(self, file_id):
        file_path = self.file_path.get(file_id)
        if not file_path:
            raise RuntimeError(f"No file path found for file_id {file_id}")

        # Read the file as a CSV, then return the list of column names
        df = self._read_file(file_path, 100)
        return df.columns.tolist()

    def get_file_details(self):
        file_details = []
        # Process text file IDs
        for file_id in self.text_file_ids:
            file_entry = {
                "file_name": self.file_name[file_id],
                "title": self.file_title[file_id],
                "summary_short": self.file_summary_short[file_id]
            }
            file_details.append(file_entry)

        # Process spreadsheet file IDs
        for file_id in self.spreadsheet_file_ids:
            # Assuming `get_column_names(file_id)` is a method that retrieves column names for a file
            column_names = self.get_column_names(file_id)
            file_entry = {
                "file_name": self.file_name[file_id],
                "columns": column_names  # Add column names for spreadsheet files
            }
            file_details.append(file_entry)
        return file_details


    def chat_insight_generate(self, collection_id):
        try:
            # Fetch all files in the given collection_id
            self.collection_id = collection_id
            self.fetch_query_data()

            # Fetch all existing insights in the collection_insights table
            existing_insights = db_helper.find_many(queries.FIND_COLLECTION_INSIGHTS_BY_COLLECTION_ID, self.collection_id)
            existing_queries = [insight['query'] for insight in existing_insights]

            # Combine file names and existing queries to form the context for the AI
            context = {
                "files": self.get_file_details(),
                "tables": self.tables,
                "existing_queries": existing_queries
            }

            # Convert context to JSON string
            context_json = json.dumps(context)

            # Call AI to identify one new insight query
            response = json.loads(self.openai_helper.callai_json(
                system_content = f"""
                User's Role: {self.user_current_role.get('role_name') or "Manager"}
                User's Objectives:  {self.user_current_role.get('objectives') or "To seek information and do research on the data available" }
                
                Based on the Role and Objective use the data provided to identify LLM Prompts for producing a Dashboard item, which is either one KPI or one Analytic Insight from the data in the files and/or tables.
                Respond with an English language LLM Prompt that will elicit one Dashboard item, which could be either a KPI or an Analytic Insight from the data in these files. Use the existing queries as cues but the new query should be different from these. 
                Return the output as a JSON in the following format: 
                {{'choices': [{{'text': 'new_dashboard_query', 'title': <appropriate 2-3 word title for this action item>, 'order_number': <next number after all other order numbers>}}]}}.
                
                Examples of KPI:
                1. Calculate the employee turnover rate by dividing the number of employees who left in the last 12 months by the average number of employees during the same period. Express the result as a percentage and provide insights on trends across departments.
                2. Determine the average time-to-fill by calculating the number of days between job posting and offer acceptance for all filled positions in the last year. Highlight any roles or departments with longer hiring times.
                3. Compute the gender diversity ratio by calculating the percentage of female employees relative to total employees. Provide department-wise breakdowns and trends over the last three years.
                4. Determine the promotion rate by dividing the number of employees promoted in the last year by the total number of employees. Express it as a percentage and highlight any disparities across different demographics.

                Examples of Analytic Insight:
                1. Analyze employee exit data and identify the top three factors that contribute to voluntary turnover. Provide insights on how these factors vary by department, tenure, or job role.
                2. Analyze recruitment data to identify the stage in the hiring process where candidates drop off the most. Provide insights into how this varies by job type or department.
                3. Analyze promotion trends over the last three years to determine if employees from underrepresented groups are being promoted at the same rate as others. Identify any disparities by department or job level.
                """,
                user_content=context_json,
                user_id=self.user_id
            ))
            # Parse the response to get the new insight query
            new_insight_query = response.get('choices', [{}])[0].get('text', '')
            #.strip() + "Summarise 2-3 action items as numbered bullets at the bottom. Give output as HTML."
            new_insight_title = response.get('choices', [{}])[0].get('title', '').strip()
            new_insight_order_number = response.get('choices', [{}])[0].get('order_number', 1)

            # Return the new insight query
            return new_insight_query, new_insight_title, new_insight_order_number

        except Exception as e:
            logger.error(f"Error in chat_insight_generate: {str(e)}")
            raise e



    #insight gen related functions - END


    #decide_control_flow related functions - BEGIN
    #Class properties this function refers to:
    #Input
    #   self.query
    #   self.file_name
    #   self.custom_instructions
    #   self.username
    #   self.previous_chat_context
    #Output
    #   self.control_sequence

    def decide_control_flow(self):
        #TODO: need to rewrite this function to use Tool selection instead of file_category selection
        try:
          system_content = f"""
              Your Task:
              Break down the User query into smaller Steps to execute in sequence.
              For each step, identify the Category of Files to be used and the modified specific User query which is being answered in this Step.

              Input:

              List of Files:
              {self.file_name}
              Details about the files:
              {self.get_file_details()}

              List of Tables:
              {self.tables}

              More Details about the Files and Tables:
              {self.custom_instructions['custom_instructions']}
              
              Provide the response in the JSON format with an array called Steps, each element of which has 2 Fields: user_query and file_category.
              file_category {ChatFileCategory.TEXT_FILES} is pdf and such text files.
              file_category {ChatFileCategory.SPREADSHEET_FILES} is for spreadsheet files.
              file_category {ChatFileCategory.PREVIOUS_OUTPUT} means only use the Output of the previous step as the Context.
              To identify which file_category is needed for a Step, use the details about the Files made available above.
              If pdf and such text files are not there, please do not set file_category to {ChatFileCategory.TEXT_FILES}.
              If spreadsheet files are not there, please do not set file_category to {ChatFileCategory.SPREADSHEET_FILES}.
              Do all the processing needed on {ChatFileCategory.SPREADSHEET_FILES} in one step.
              In general, unless explicitly needed by the logic, do any step required for {ChatFileCategory.SPREADSHEET_FILES} before the step required for {ChatFileCategory.TEXT_FILES}.
              If the user is saying something like "translate that to hindi", then just have one step with the exact same User query and set the file_category to {ChatFileCategory.PREVIOUS_OUTPUT}.

              Examples:
              1. Query: where did xyz study?
              Output: {{"steps": [{{"user_query": "where did xyz study?", "file_category": "{ChatFileCategory.TEXT_FILES}"}}]}}
              
              2. Query: give a table of where all the candidates studied?
              Output: {{"steps": [{{"user_query": "give a table of where all the candidates studied?", "file_category": "{ChatFileCategory.TEXT_FILES}"}}]}}
              
              3. Query: who scored better in the interview?
              Output: {{"steps": [{{"user_query": "who scored better in the interview?", "file_category": "{ChatFileCategory.SPREADSHEET_FILES}"}}]}}
              
              4. Query: look at interview scores and compare one person to another person for developer role?
              Output: {{"steps": [{{"user_query": "give each person's interview score as a table", "file_category": "{ChatFileCategory.SPREADSHEET_FILES}"}}, {{"user_query": "compare one person to another person for developer role?", "file_category": "{ChatFileCategory.TEXT_FILES}"}}]}}
              
              5. Query: Share the score of the candiate who studied in xyz college?
              Output: {{"steps": [{{"user_query": "List the candidates who studied in xyz college", "file_category": "{ChatFileCategory.TEXT_FILES}"}}, {{"user_query": "Share the score of the candidate who studied in xyz college?", "file_category": "{ChatFileCategory.SPREADSHEET_FILES}"}}]}}

              6. Query: translate that to hindi
              Output: {{"steps": [{{"user_query": "translate that to hindi", "file_category": "{ChatFileCategory.PREVIOUS_OUTPUT}"}}]}}

              7. Query: What is the Product description for Product ?
              Input files: ["Product Description.xlsx", "Sales.xlsx"]
              Output: {{"steps": [{{"user_query": "What is the Product description for Product ?", "file_category": "{ChatFileCategory.SPREADSHEET_FILES}"}}]}}

              8. Query: What is the Product description for Product ?
              Input files: ["Product Description.pdf", "Sales.pdf"]
              Output: {{"steps": [{{"user_query": "What is the Product description for Product ?", "file_category": "{ChatFileCategory.TEXT_FILES}"}}]}}

              9. Query: List the file names.
              Input files: ["Product Description.pdf", "Sales.pdf"]
              Output: {{"steps": [{{"user_query": "List the file names.", "file_category": "{ChatFileCategory.PREVIOUS_OUTPUT}"}}]}}
          """

          previous_messages = self.previous_chat_context
          repeat_count = 2
          username = self.username
          response = json.loads(self.openai_helper.callai_json(
              system_content=system_content,
              user_content=self.query,
              user_id=username,
              extra_context=previous_messages
          ))
          logger.debug(f"################Response from control flow query: {response}")

          #load the value from response onto self.control_sequence
          if (not response['steps'] or len(response['steps']) == 0):
              self.control_sequence = {"steps": [{"user_query": self.query, "file_category": f"{ChatFileCategory.TEXT_FILES}"}]}
          else:
              self.control_sequence = response
          logger.info(f"Control sequence loaded: {self.control_sequence}")

        except Exception as e:
            logger.error(f"Control sequence set to default due to error: {e}")
            self.control_sequence = {"steps": [{"user_query": self.query, "file_category": f"{ChatFileCategory.TEXT_FILES}"}]}


    #decide_control_flow related functions - END


    #fetch_query_data related functions - BEGIN
    def fetch_query_data(self):
        self.collection = self.get_collection()
        print(f"Collection: {self.collection}")
        self.get_file()
        for file_id in self.file_ids:
            self.file_path[file_id] = os.path.join(config.ORGDIR_PATH, self.orgname, config.ORGDIR_SUB_PATH, self.file_name[file_id])
        if (self.collection['db_uri']):
            self.get_table()

        self.collection['gsheets_credentials_file_path'] = None
        if (self.collection['type']) == 'googlesheet':
            # Get the list of Google Sheets that are part of this collection
            collection_gsheet_urls = db_helper.find_many(queries.FIND_GSHEETS_BY_COLLECTION_ID, self.collection_id)
            # Extract spreadsheet IDs from URLs
            collection_gsheet_ids = []
            for url in collection_gsheet_urls:
                parsed_url = urlparse(url.get('file_url', ''))
                # Google Sheet URLs have format like: https://docs.google.com/spreadsheets/d/{spreadsheet_id}/edit
                path_parts = parsed_url.path.split('/')
                if len(path_parts) >= 4 and path_parts[1] == 'spreadsheets' and path_parts[2] == 'd':
                    spreadsheet_id = path_parts[3]
                    collection_gsheet_ids.append(spreadsheet_id)
            print(f"@@@@@@@@@@@@@@@@@Gsheet Ids: {collection_gsheet_ids}")

            credential_json = json.loads(db_helper.find_one(queries.FIND_GOOGLE_CREDENTIALS_BY_COLLECTION_ID, self.collection_id).get('credentials_json'))
            if credential_json:
                #write the json to a file and get the credentials_file_path
                os.makedirs(config.DOCANALYSIS_TEMP_FILE_PATH, exist_ok=True)
                gsheets_credentials_file_path = os.path.join(config.DOCANALYSIS_TEMP_FILE_PATH, f"{self.orgname}_{self.collection_id}.json")
                with open(gsheets_credentials_file_path, 'w') as f:
                    json.dump(credential_json, f)
                self.collection['gsheets_credentials_file_path'] = gsheets_credentials_file_path
                
                """ # Load credentials and initialize Sheets API
                SCOPES = [
                    'https://www.googleapis.com/auth/drive.metadata.readonly',
                    'https://www.googleapis.com/auth/spreadsheets',
                ]
                SERVICE_ACCOUNT_FILE = gsheets_credentials_file_path

                credentials = service_account.Credentials.from_service_account_file(
                    SERVICE_ACCOUNT_FILE, scopes=SCOPES
                )

                # Drive API client
                drive_service = build('drive', 'v3', credentials=credentials)
                
                
                
                # Only fetch sheets that are in the collection_gsheet_list
                results = drive_service.files().list(
                        q="mimeType='application/vnd.google-apps.spreadsheet'",
                        pageSize=100,
                        fields="files(id, name)"
                    ).execute() """
                
                gdrive_instance = GoogleDriveHelper(credential_json)
                results = gdrive_instance.get_files()
                # Filter results to only include sheets that are in the collection
                if collection_gsheet_ids:
                    results['files'] = [file for file in results.get('files', []) 
                                       if file.get('id') in collection_gsheet_ids]
                else:
                    results['files'] = []
                gsheet_files = results.get('files', [])

                # Loop through each Google Sheet
                for gsheet in gsheet_files:
                    try:
                        SPREADSHEET_ID = gsheet['id']
                        SPREADSHEET_NAME = gsheet['name']

                        spreadsheet = gdrive_instance.sheets_service.spreadsheets().get(spreadsheetId=SPREADSHEET_ID).execute()

                        # Get all worksheet names
                        sheet_names = [s['properties']['title'] for s in spreadsheet['sheets']]

                        # Store the spreadsheet details in the dictionary
                        self.gsheet_ids_and_worksheets[SPREADSHEET_ID] = {
                            'name': SPREADSHEET_NAME,
                            'worksheets': sheet_names
                        }
                    except Exception as e:
                        logger.error(f"Error processing Google Sheet {gsheet['name']}: {str(e)}", exc_info=True)
        print(f"Gsheet ids and worksheets: {self.gsheet_ids_and_worksheets}")
        #self.file_path = [os.path.join(config.ORGDIR_PATH, self.orgname, config.ORGDIR_SUB_PATH, fname) for fname in self.file_name]
        self.user = self.get_user()
        self.prompts = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docchat', Prompts.RESPOND_TO_SEARCH_USER_QUERY)
        self.custom_instructions = self.get_custom_instructions()
        self.custom_instructions = self.filter_custom_instructions()

    def get_collection(self):
        logger.debug(f"Fetching collection with ID: {self.collection_id}")
        collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID, self.collection_id)
        if not collection:
            logger.error(f"Collection not found for ID: {self.collection_id}")
            raise RuntimeError('Collection not found!')
        self.collection_name = collection.get('collection_name')
        logger.info(f"Collection found: {self.collection_name}")
        return collection

    def get_file(self):
        logger.debug(f"Fetching files from collection with ID: {self.collection_id}")
        if self.selected_file_ids is None:
            files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_ID, self.collection_id)
        else:
            files = db_helper.find_many(queries.V2_FIND_FILES_BY_FILE_IDS, self.selected_file_ids)
        """ if not files:
            logger.error(f"File not found for collection ID: {self.collection_id}")
            raise RuntimeError('File not found!') """

        # Initialize lists to store file IDs and file names
        self.file_ids = []
        self.text_file_ids = []
        self.spreadsheet_file_ids = []
        self.file_name = {}
        # Loop through all retrieved files and populate the lists
        for file in files:
            logger.debug(f"File found: {file.get('file_name')}")
            self.file_ids.append(file.get('file_id'))
            file_name = file.get('file_name')
            if file_name:
              self.file_name[file.get('file_id')] = file_name
              _, file_extension = os.path.splitext(file_name)
              file_extension = file_extension.lower()
              if file_extension == '.pdf':
                  self.text_file_ids.append(file.get('file_id'))
              elif file_extension in ['.xls', '.xlsx', '.csv']:
                  self.spreadsheet_file_ids.append(file.get('file_id'))
              self.file_title[file.get('file_id')] = file.get('title') or ''
              self.file_summary_short[file.get('file_id')] = file.get('summary_short') or ''
        logger.info(f"Files found: {self.file_ids}")
        return files

    """ def get_table(self):
        logger.debug(f"Fetching tables from collection with ID: {self.collection_id}")

        # Extract the database name and schema name from the db_uri
        db_uri_parts = self.collection['db_uri'].split('/')
        schema_name = db_uri_parts[-1]

        get_tables_query = f"SELECT table_name FROM information_schema.tables WHERE table_schema = '{schema_name}'"
        tables = db_helper.find_collection_db_many(get_tables_query, self.collection['db_uri'])
        self.tables = [f"{schema_name}.{','.join(table.values())}" for table in tables]
        logger.info(f"Tables found: {self.tables}")
        return self.tables """

    def get_table(self):
        logger.debug(f"Fetching tables from collection with ID: {self.collection_id}")

        # Extract the database name and schema name from the db_uri
        db_uri_parts = self.collection['db_uri'].split('/')
        if 'postgres' in self.collection['db_uri'] or 'postgresql' in self.collection['db_uri']:
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

        tables_df = db_helper.find_collection_db_many(get_tables_query, self.collection['db_uri'])
        print(tables_df)

        if not tables_df.empty:
            # Process both schema and table name from the query results
            if schema_name:
                self.tables = [f"{row['table_schema']}.\"{row['table_name']}\"" for index, row in tables_df.iterrows()]
            else:
                self.tables = [f"{db_name}.\`{row['table_name']}\`" for index, row in tables_df.iterrows()]

            logger.info(f"Tables found: {self.tables}")
            return self.tables
        else:
            logger.info("No tables found.")
            return []

    def get_user(self):
        logger.debug(f"Fetching user with ID: {self.user_id}")
        user = db_helper.find_one(queries.FIND_USER_BY_USER_ID, self.user_id)
        if not user:
            logger.error(f"User not found for ID: {self.user_id}")
            raise RuntimeError('User not found!')
        self.username = user.get('username')
        logger.info(f"User found: {self.username}")
        return user

    def get_custom_instructions(self):
        logger.debug(f"Fetching custom instructions for collection ID: {self.collection_id}")
        custom_instructions = db_helper.find_one(queries.FIND_CUSTOM_INSTRUCTIONS_BY_COLLECTION_ID, self.collection_id)
        return custom_instructions

    #if custom_instructions is an array, then for remove each object inside if the file_name property is not there in the object self.file_name, then remove that entry.
    # If custom_instructions is not an array, then return it as it is
    def filter_custom_instructions(self):
        print(f"@@@@@@@@@@@@@@@@@@@@@@@@@Custom instructions filtering...")
        filtered_custom_instructions = {}
        if (self.custom_instructions['custom_instructions'] != None and self.custom_instructions['custom_instructions'].strip().startswith('[')):
            custom_instructions = json.loads(self.custom_instructions['custom_instructions'])
            filtered_custom_instructions['custom_instructions'] = [instruction for instruction in custom_instructions if instruction.get('file_name') in self.file_name.values()]
            print(f"@@@@@@@@@@@@@@@@@@@@@@@@@Filtered custom instructions: {filtered_custom_instructions}")
            return filtered_custom_instructions
        else:
            print(f"@@@@@@@@@@@@@@@@@@@@@@@@@Custom instructions: {self.custom_instructions}")
            return self.custom_instructions

    #fetch_query_data related functions - END

    #prepare_context related functions - BEGIN
    def load_bm25_parameters_for_files(self):
        try:
            # Retrieve IDF values for the specified file
            #idf_data = db_helper.find_many(queries.FIND_BM25_TERMS_FOR_FILE, self.file_id)
            idf_data = {}
            idf_values = {}
            avg_doc_len = {}

            # Loop through each file_id in self.text_file_ids and retrieve corresponding data
            for file_id in self.text_file_ids:
                logger.debug(f"Retrieving BM25 parameters for file: {file_id}")
                file_idf_data = db_helper.find_many(queries.FIND_BM25_TERMS_FOR_FILE, file_id)
                if not file_idf_data:
                    logger.error(f"BM25 terms not found in the DB for file: {file_id}")
                    return idf_values, avg_doc_len
                idf_data[file_id] = file_idf_data if file_idf_data else []


            #print(f"Raw IDF data: {idf_data}")
            #idf_values = {entry['term']: entry['idf'] for entry in idf_data}
            # Populate idf_values with each file_id's terms and their corresponding idf values
            for file_id, entries in idf_data.items():
                idf_values[file_id] = {entry['term']: entry['idf'] for entry in entries}
            #print(f"First 5 IDF values: {list(idf_values.items())[:5]}")

            # Retrieve average document length
            for file_id in self.text_file_ids:
                avg_doc_len[file_id] = db_helper.find_one(queries.FIND_BM25_AVG_DOC_LENGTH, file_id)
                avg_doc_len[file_id] = avg_doc_len[file_id]['avg_doc_len']
            #print(f"Average document length: {avg_doc_len}")

            return idf_values, avg_doc_len
        except Exception as e:
            logger.error(f"Error loading BM25 parameters: {e}")
            raise e

    def load_pages_for_files(self):
        pages_data = {}
        preprocessed_pages = {}
        for file_id in self.text_file_ids:
            try:
                pages_data[file_id] = db_helper.find_many(queries.FIND_BM25_TOKENS, file_id)
                #print(f"Pages data: {pages_data}")
            except Exception as e:
                logger.error(f"BM25 tokens not found in the DB for file: {file_id}")
                raise e
            preprocessed_pages[file_id] = []
            for page in pages_data[file_id]:
                tokens = page.get("tokens")
                #print(f"Tokens: {tokens}")

                if tokens:  # Only load if the string is not empty
                    try:
                        preprocessed_pages[file_id].append(json.loads(tokens))
                    except json.JSONDecodeError as e:
                        logger.error(f"Error decoding JSON: {e}, Tokens: {tokens}")
                        raise e
                else:
                    logger.error("Empty tokens found")

        logger.debug(f"Preprocessed pages count: {len(preprocessed_pages)}")

        return preprocessed_pages, pages_data

    #this def is not used. It was a replacement for the bm25 official function, when it was not working
    def bm25_score(self, query, document, doc_len, idf, avgdl, k1=1.5, b=0.75):
        score = 0.0
        doc_counter = Counter(document)

        for term in query:
            if term in idf:  # Only calculate for terms with a non-zero IDF
                #print(f"##################Term: {term}")
                term_freq = doc_counter[term]
                term_idf = idf[term]
                score += term_idf * ((term_freq * (k1 + 1)) / (term_freq + k1 * (1 - b + b * (doc_len / avgdl))))

        return score

    #this def is not used. It was a replacement for the bm25 official function, when it was not working
    def calculate_bm25_scores(self, corpus, idf, avgdl, k1=1.5, b=0.75):
        scores = []
        query_terms = self.query.lower().split()  # Tokenize and preprocess query

        for document in corpus:
            doc_len = len(document)
            score = self.bm25_score(query_terms, document, doc_len, idf, avgdl, k1, b)
            scores.append(score)

        return scores


    def initialize_bm25_for_files(self):
        preprocessed_pages = {}
        bm25 = {}
        try:
            idf_values, avg_doc_len = self.load_bm25_parameters_for_files()
            #print(f"Avg doc length: {avg_doc_len}")
            preprocessed_pages, _ = self.load_pages_for_files()
            #print(f"First preprocessed page: {preprocessed_pages[self.text_file_ids[0]]}")

            logger.debug("Initializing BM25 for files")
            for file_id in self.text_file_ids:
                bm25[file_id] = BM25Okapi(preprocessed_pages[file_id])
                bm25[file_id].idf = idf_values[file_id]
                bm25[file_id].avgdl = avg_doc_len[file_id]
            logger.debug(f"BM25 initialized for file: {file_id}")
            return bm25, preprocessed_pages
        except Exception as e:
            logger.error(f"Error initializing BM25: {e}")
            return bm25, preprocessed_pages

    def preprocess_text(self, text):
        stop_words = set(stopwords.words("english"))
        tokens = word_tokenize(text.lower())
        tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
        #print(f"Number of Preprocessed tokens: {len(tokens)}")
        return tokens

    def query_bm25_for_file(self, top_n=5):
        top_pages = []
        try:
            logger.debug("commencing bm25...")
            bm25, preprocessed_pages = self.initialize_bm25_for_files()
            preprocessed_query = self.preprocess_text(self.current_step_query)
            scores = {}
            for file_id in self.text_file_ids:
                scores[file_id] = bm25[file_id].get_scores(preprocessed_query)
                #scores = self.calculate_bm25_scores(preprocessed_pages, bm25.idf, bm25.avgdl)
                logger.debug(f"Scores for file_id {file_id}: {scores[file_id]}")

            # Load page text to show in results
            _, pages_data = self.load_pages_for_files()
            #print(f"First page data: {pages_data[0]}")

            """ # Get top relevant pages
            top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
            #print(f"Top indices: {top_indices}")
            #top_pages = [(pages_data[i][0], scores[i]) for i in top_indices]  # page_number, score
            top_pages = [(pages_data[i]['page_number'], scores[i]) for i in top_indices] """

            top_n = int(os.getenv('ASKDOC_CONTEXT_NUM_PAGES', 10))

            # Collect all scores with corresponding file_id, page number, and score
            for file_id, scores_list in scores.items():
                for page_num, score in enumerate(scores_list):
                    top_pages.append({'file_id': file_id, 'page_num': pages_data[file_id][page_num]['page_number'], 'score': score})

            # Sort the top_pages list by score in descending order and select the top_n entries
            top_pages = sorted(top_pages, key=lambda x: abs(x['score']), reverse=True)[:top_n]

            #print(f"First top page entry: {top_pages[0]}")
            return top_pages
        except Exception as e:
            logger.error(f"Error in query_bm25_for_file: {e}")
            return top_pages

    def get_text_for_pagenum(self, file_id, page_number):
        try:
            doc = fitz.open(self.file_path[file_id])
            page = doc.load_page(page_number)
            text = page.get_text()
            return text
        except Exception as e:
            logger.error(f"Error in get_text_for_pagenum: {e}")
            raise e

    # Class properties this function refers to:
    #Input
    #   self.current_step_query
    #   self.orgname
    #   self.collection_name
    #   self.prompts
    #   self.custom_instructions
    #Output
    #   self.system_content

    def prepare_context(self):
        # logger.info("Preparing context for vector search")
        # self.vector_search = VectorSearch(self.query)
        # self.vector_search.embed_query()
        # self.vector_search.vector_search(
        #     search_filter={
        #         'orgname': {'$eq': self.orgname},
        #         'collection': {'$in': [self.collection_name]},
        #     }
        # )
        # self.vector_search.parse_content()
        # context_prompt = self.vector_search.context_prompt
        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
        )
        context_prompt_max_char_count = int(os.getenv('ASKDOC_CONTEXT_PROMPT_MAX_CHAR_COUNT', 32000))

        # Get the top pages using BM25
        top_pages = self.query_bm25_for_file()
        logger.debug(f"Top pages: {top_pages}")

        # Insert vector retrieved chunks instead of zer-scoring pages. If no zero-scoring pages, insert the first 6 pages and rest can be vector chunks
        index_of_zero = next((index for index, item in enumerate(top_pages) if item['score'] == 0), len(top_pages))
        num_pages = int(os.getenv('ASKDOC_CONTEXT_NUM_PAGES', 10))
        min_bm25_pages = int(float(os.getenv('ASKDOC_PERCENTAGE_OF_BM25_PAGES', 0.6)) * num_pages)
        vector_chunk_start_index = min(index_of_zero, min_bm25_pages)
        logger.debug(f"Index of zero: {index_of_zero}, Min BM25 pages: {min_bm25_pages}, Vector chunk start index: {vector_chunk_start_index}")


        # Use the top_pages to open pdf file in path self.file_path and load the page content into context prompt
        bm25_context_prompt = ''
        i = 0
        for page in top_pages:
            file_id = page['file_id']
            page_number = page['page_num']
            score = page['score']

            logger.debug(f"Retrieving text for page: {page_number} in file: {file_id}")
            potential_prompt = bm25_context_prompt + self.get_text_for_pagenum(file_id, page_number)
            if len(potential_prompt) < context_prompt_max_char_count and i < vector_chunk_start_index:
                bm25_context_prompt = potential_prompt
            i += 1
        logger.debug(f"Context prompt length: {len(bm25_context_prompt)}")

        context_prompt_max_char_count_remaining = context_prompt_max_char_count-len(bm25_context_prompt)

        if (context_prompt_max_char_count_remaining > 0):
            # now fill the rest of the context prompt with vector chunks
            metadata_json = []
            MODEL = config.EMBEDDING_MODEL
            from pinecone import Pinecone
            from pinecone import ServerlessSpec

            pc = Pinecone(api_key=config.PINECONE_API_KEY)

            #print(pc.list_indexes().names())

            # check if index already exists (only create index if not)
            if config.PINECONE_INDEX_NAME not in pc.list_indexes().names():
                pc.create_index(config.PINECONE_INDEX_NAME, dimension=1536, spec=ServerlessSpec(
                    cloud="aws",
                    region=config.PINECONE_ENVIRONMENT
                ),) #old - len(embeds[0])

            # connect to index and get query embeddings
            pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
            # index = pinecone.Index(config.pinecone_index_name)
            xq = client.embeddings.create(input=self.current_step_query, model=MODEL).data[0].embedding

            topk = int(os.getenv('ASKDOC_CONTEXT_PROMPT_TOPK', 40))
            search_filter = {
                'orgname': {'$eq': self.orgname},
                'collection': {'$in': [self.collection_name]},
                'filename': {'$in': list(self.file_name.values())}
            }
            res = pinecone_index.query(vector=[xq], filter=search_filter, top_k=topk, include_metadata=True)

            #logger.info('\n\nPINECOONE_INDEX_QUERY: ' + str(res) + '\n\n')
            vector_context_prompt = ''

            if len(res['matches']) > 0:
                if res['matches']:
                    vector_context_prompt = ''

                    for i in range(len(res['matches'])):
                        potential_prompt = vector_context_prompt + res['matches'][i]['metadata']['_node_content']
                        if (len(potential_prompt) < context_prompt_max_char_count_remaining):
                            #vector_context_prompt = potential_prompt

                            #Log all metadata fields for debugging
                            metadata = {}
                            metadata = res['matches'][i]['metadata']  # Access metadata dictionary

                            # Convert '_node_content' to JSON/object and access the nested value
                            if '_node_content' in metadata:
                                node_content = json.loads(metadata['_node_content'])
                                metadata['text'] = node_content.get('text', '')

                                # Remove the '_node_content' key
                                del metadata['_node_content']

                            # Define the keys to be removed
                            keys_to_remove = ['collection', 'orgname', '_node_type', 'doc_id', 'document_id', 'ref_doc_id']

                            # Remove the specified keys from metadata
                            metadata = {key: value for key, value in metadata.items() if key not in keys_to_remove}
                            metadata_json.append(metadata)
                            #logger.info('\n\nMETADATA_JSON: ' + str(metadata_json) + '\n\n')
                            vector_context_prompt += json.dumps(metadata)
                        else:
                            break

        context_prompt = bm25_context_prompt + vector_context_prompt

        self.system_content = (
            f"{self.prompts['prompt_text']}\n"
            f"{self.custom_instructions['custom_instructions']}\n"
            f"Context:\n{context_prompt}"
        )
        logger.info("Context preparation completed")

    """ def prepare_context(self):
        client = OpenAI(
            api_key=config.OPENAI_API_KEY,
        )
        metadata_json = []
        MODEL = config.EMBEDDING_MODEL

        pc = Pinecone(api_key=config.PINECONE_API_KEY)
        print(pc.list_indexes().names())

        # check if index already exists (only create index if not)
        if config.PINECONE_INDEX_NAME not in pc.list_indexes().names():
            pc.create_index(config.PINECONE_INDEX_NAME, dimension=1536, spec=ServerlessSpec(
                cloud="aws",
                region="us-east-1"
            ))

        # connect to index and get query embeddings
        pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
        xq = client.embeddings.create(input=self.query, model=MODEL).data[0].embedding

        topk = 40
        search_filter = {
            'orgname': {'$eq': self.orgname},
            'collection': {'$in': [self.collection_name]}
        }
        res = pinecone_index.query(vector=[xq], filter=search_filter, top_k=topk, include_metadata=True)

        logger.info('\n\nPINECONE_INDEX_QUERY: ' + str(res) + '\n\n')
        context_prompt = ''

        if len(res['matches']) > 0:
            if res['matches']:
                context_prompt = ''
                documents = []
                metadata_list = []

                for match in res['matches']:
                    metadata = match['metadata']
                    if '_node_content' in metadata:
                        node_content = json.loads(metadata['_node_content'])
                        text = node_content.get('text', '')
                        documents.append(text)
                        metadata_list.append(metadata)

                # Use BM25 to rerank the documents
                bm25 = BM25Okapi([doc.split() for doc in documents])
                query_tokens = self.query.split()
                doc_scores = bm25.get_scores(query_tokens)
                ranked_indices = sorted(range(len(doc_scores)), key=lambda i: doc_scores[i], reverse=True)

                for idx in ranked_indices:
                    potential_prompt = context_prompt + documents[idx]
                    if len(potential_prompt) < 32000:
                        metadata = metadata_list[idx]

                        # Convert '_node_content' to JSON/object and access the nested value
                        if '_node_content' in metadata:
                            node_content = json.loads(metadata['_node_content'])
                            metadata['text'] = node_content.get('text', '')

                            # Remove the '_node_content' key
                            del metadata['_node_content']

                        # Define the keys to be removed
                        keys_to_remove = ['collection', 'orgname', '_node_type', 'doc_id', 'document_id', 'ref_doc_id']

                        # Remove the specified keys from metadata
                        metadata = {key: value for key, value in metadata.items() if key not in keys_to_remove}
                        metadata_json.append(metadata)
                        logger.info('\n\nMETADATA_JSON: ' + str(metadata_json) + '\n\n')
                        context_prompt += json.dumps(metadata)
                    else:
                        break

        self.system_content = (
            f"{self.prompts['prompt_text']}\n"
            f"{self.custom_instructions['custom_instructions']}\n"
            f"Context:\n{context_prompt}"
        )
        logger.info('\n\nSYSTEM_CONTENT: ' + str(self.system_content) + '\n\n')
        logger.info("Context preparation completed") """
    #prepare_context related functions - END

    #generate_response related functions - BEGIN
    #Class properties this function refers to:
    #   self.system_content
    #   self.current_step_query
    #   self.user_id
    #   self.previous_chat_context
    #   self.thread_id

    def generate_response(self):
        logger.info("Generating response using OpenAI")
        try:
            streamed_data = self.openai_helper.callai_streaming(
                system_content=self.system_content,
                user_content=self.current_step_query,
                user_id=self.user_id,
                extra_context=self.previous_chat_context
            )

            for event, message in streamed_data:
                if event == 'CHUNK':
                    message = message.replace('\n', '<br>')
                    #yield f"data: {message}\n\n"
                    chunk_message = dict(message=message)
                    chunk_message = json.dumps(chunk_message)
                    yield f"event: {StreamEvent.CHUNK}\ndata: {chunk_message}\n\n"
                if event == 'FINAL_MESSAGE':
                    message = message.replace('```html', '').replace('```', '')
                    self.add_assistant_chat_history(message=message)
                    table = True if message.find("<table") != -1 else False
                    print(f"##################################Table: {table}")
                    final_message = dict(message=message, thread_id=self.thread_id, table=table)
                    final_message = json.dumps(final_message)
                    yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"
                    #yield self._sse_response(StreamEvent.FINAL_OUTPUT,message,False, self.thread_id)

        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
            final_message = json.dumps({
                "message": "Sorry, I am having some trouble to respond at the moment. Please try again later!",
                "thread_id": self.thread_id
            })
            #yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"
            yield self._sse_response(StreamEvent.FINAL_OUTPUT,"Sorry, I am having some trouble to respond at the moment. Please try again later!",False, self.thread_id)
    #generate_response related functions - END

    #metadata gen related functions - BEGIN
    #def chat_metadata_generate():
    #Issue to think about. Is this about a common set of metadata for all the files or is it about the metadata for each file?
    #If individual just parse through each and insert into schema table. Else how to identify common metadata that makes sense for all the files as a set?

    #metadata gen related functions - END

    #subsequent housekeeping functions
    def add_user_chat_history(self, extra_payload=None):
        try:
            logger.info('Adding user chat history')
            user_chat_payload = dict(role='user', content=self.query)
            if extra_payload:
                user_chat_payload.update(extra_payload)
            chats_helper.add_chat_history(self.thread_id, user_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def add_assistant_chat_history(self, message , extra_payload=None):
        try:
            logger.info('Adding assistant chat history')
            assistant_chat_payload = dict(role='assistant', content=message)
            if extra_payload:
                assistant_chat_payload.update(extra_payload)
            chats_helper.add_chat_history(self.thread_id, assistant_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def fetch_previous_chat_history(self, history_count=7):
        try:
            logger.info('Fetching previous chat history')
            if self.thread_id:
                chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(self.thread_id, self.user_id)
                if not chat_thread:
                    logger.error('Chat thread not found')
                    return
                chat_history = chat_thread.get('messages')
                filtered_chat_history = list(filter(lambda chat: chat.get('role') != 'action', chat_history))
                self.previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                              filtered_chat_history[-history_count:] if len(filtered_chat_history) > 1]
        except Exception as e:
            logger.error(e)
            raise e

    @staticmethod
    def _sse_response(event, message, retry, thread_id, image_data=None):
        data = {'message': message}
        if event == StreamEvent.FINAL_OUTPUT:
            data = {'message': message, 'retry': retry, 'thread_id': thread_id}
            data['table'] = True if message.find("<table") != -1 else False

        if image_data:
            data['image_data'] = image_data

        json_data = json.dumps(data)
        return f"event: {event}\ndata: {json_data}\n\n"
    #subsequent housekeeping functions - END
