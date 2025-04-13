import json
import logging
from typing import Dict, Any, List, Optional
from dataclasses import dataclass

from flask import request
import requests
from source.api.utilities.constants import SectionStage
from source.api.utilities.externalapi_helpers import chats_helper
from source.api.utilities.externalapi_helpers.docguide_helper import SectionChatManager
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.common import config
from source.api.utilities import db_helper, queries

logger = logging.getLogger('app')
class WebhookError(Exception):
    pass


class WebhookHelper:
    def __init__(self):
        self.whatsapp_token = config.WHATSAPP_VERIFY_TOKEN
        self.whatsapp_url = config.WHATSAPP_REPLY_URL
        self.whatsapp_access_token = config.WHATSAPP_ACCESS_TOKEN
        self.org_id = None
        self.user_id = None
        self.file_id = None
        self.section_id = None
        self.phone_number = None
        self.message = None

    def verify_whatsapp(self):
        try:
            mode = request.args.get('hub.mode')
            token = request.args.get('hub.verify_token')
            challenge = request.args.get('hub.challenge')
            
            logger.info(f"Verifying WhatsApp webhook - mode: {mode}, token: {token}")
            
            if not (mode and token):
                raise WebhookError('Missing mode or token')
                
            if mode != 'subscribe' or token != self.whatsapp_token:
                raise WebhookError('Invalid mode or token')
                
            return challenge
        except WebhookError as e:
            logger.error(f"WEBHOOK ERROR: {e}")
            raise
        except Exception as e:
            logger.error(f"WhatsApp verification failed: {e}")
            raise
        
        
    def handle_whatsapp(self):
        
        def _extract_messages(data):
            for entry in data.get('entry', []):
                for change in entry.get('changes', []):
                    yield from change.get('value', {}).get('messages', [])
        
        try:
            data = request.get_json()
            logger.info("Received WhatsApp webhook data")
            
            for message_data in _extract_messages(data):
                logger.info(f"PROCESSING MESSAGE:\n{message_data}")
                self.phone_number = message_data.get('from')
                self.get_user_and_session()
                
                message_handlers = {
                    'text': self.handle_text_message,
                    'interactive': self.handle_interactive_message
                }
                
                message_type = message_data.get('type')
                handler = message_handlers.get(message_type)
                
                if handler:
                    handler(message_data)
                else:
                    logger.warning(f"Unsupported message type: {message_type}")
                    self.send_whatsapp_message(message_type='text', body="Unsupported message type")
                    
            return 'OK'
        except WebhookError as e:
            logger.error(f"WEBHOOK ERROR: {e}")
            raise   
        except Exception as e:
            logger.error(f"Error handling WhatsApp webhook: {e}")
            raise
    
    ################################################################################
    # Message Handlers
    ###############################################################################
    
    def handle_text_message(self, message_data):
        self.message = message_data.get('text', {}).get('body', '')
        logger.info(f"Processing text message: {self.message}")

        command_type = self.check_for_commands()
        if command_type:
            command_handlers = {
                'file': self.send_file_list,
                'section': self.send_section_list,
                'progress': self.send_progress_message
            }
            return command_handlers.get(command_type)()

        # If not a command, check if the user has selected a file or section
        if not self.file_id:
            return self.send_file_list()
        
        if not self.section_id:
            return self.send_section_list()
        
        return self.chat_with_docguide()

    '''
    - Recieve a message which has an id.
    - The id looks like this: file_1, section_2, next_3, chat_ASSESS_ME, etc
    - The function parses the type and id and calls the corresponding handler.
    '''
    def handle_interactive_message(self, message_data):
        self.message = message_data.get('interactive', {}).get('list_reply', {})
        logger.info(f"PROCESSING INTERACTIVE MESSAGE: {self.message}")
        
        selection_type, selection_id = self.message.get('id').split('_', 1)
        
        logger.info(f"SELECTION TYPE: {selection_type}, ID: {selection_id}")
        
        selection_handlers = {
            'file': lambda: (
                self.update_docguide_session_section_id(None, reset=True),
                self.update_docguide_session_file_id(int(selection_id)),
                self.send_section_list()
            ),
            'section': lambda: (
                self.update_docguide_session_section_id(int(selection_id)),
                
                # After section is selected, send a summary to the user
                self.send_whatsapp_message(body=f"Generating summary for the selected section."),
                self.chat_with_docguide()
            ),
            
            # Used to send more pages of sections or files
            # Here the selection_id is the page number
            'next': lambda: self.process_next_command(int(selection_id)),
            
            
            # When a option clicked with 'chat' type, update the stage_id in the session table. 
            # The selection_id is the stage_id in this case.
            'chat': lambda: (
                db_helper.execute(queries.UPDATE_STAGE_ID_OF_DOCGUIDE_SESSION, selection_id, self.user_id),
                self.chat_with_docguide()
            )
        }
        
        handler = selection_handlers.get(selection_type, lambda: self.send_whatsapp_message(body=WebhookReplies.INVALID_CHOICE))
        handler()
        
    ########################################################################
    # Send Message Helpers
    ########################################################################
    
    def send_whatsapp_message(self, message_type='text', **kwargs):
        logger.info(f"Sending {message_type} message to {self.phone_number}")
        
        # Retrieve the message content based on the message type
        message_content = {"text": {"type": "text", "text": {"body": kwargs.get('body')}}, "interactive": {"type": "interactive","interactive": kwargs.get('body')}}.get(message_type)
        if not message_content:
            raise WebhookError(f"Unsupported message type: {message_type}")

        payload = { "messaging_product": "whatsapp", "to": self.phone_number, **message_content }
        try:
            logger.info(f"******** REPLY ********")
            logger.info(f"{payload}")
            logger.info(f"***********************")
            response = requests.post(
                url=self.whatsapp_url,
                headers={ 'Authorization': f'Bearer {self.whatsapp_access_token}', 'Content-Type': 'application/json'},
                json=payload
            )
            logger.info(f"Response from WhatsApp: {response.json()}")
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send WhatsApp message: {e}")
            raise

    def send_section_list(self, page=1):
        
        if self.file_id is None:
            self.send_whatsapp_message(body="You haven't selected a file yet. Please select a file first.")
            return self.send_file_list()
        
        logger.info(f"Searching for sections with file id: {self.file_id} and org id: {self.org_id}")
        
        if not (sections := db_helper.find_many(queries.FIND_DOCGUIDE_SECTIONS_BY_ORGANIZATION_ID_AND_FILE_ID, self.org_id, self.file_id)):
            logger.error(f"No sections found for file FILE_ID: {self.file_id}, ORG_ID: {self.org_id}")
            self.send_whatsapp_message(body=WebhookReplies.NO_SECTIONS_FOUND)
            return
        
        rows, total_pages = self.prepare_paginated_list(
            items=[{'id': s['section_id'], 'title': s['section_title']} for s in sections],
            current_page=page,
            id_prefix='section'
        )
        
        self.send_whatsapp_message(
            message_type='interactive',
            body={
                "type": "list",
                "header": {"type": "text", "text": "Select a Section"},
                "body": {"text": "Start chatting after selecting a section"},
                "footer": {"text": f"Page {page} of {total_pages}"},
                "action": {
                    "button": "Choose option",
                    "sections": [{"title": "Available Sections", "rows": rows}]
                }
            }
        )

    def send_file_list(self, page=1):
        if not (files := db_helper.find_many(queries.FIND_DOCGUIDE_FILES_BY_ORGANIZATION_ID, self.org_id)):
            logger.error(f"No files found for organization ORG_ID: {self.org_id}")
            self.send_whatsapp_message(body=WebhookReplies.NO_FILES_FOUND)
            return
        
        rows, total_pages = self.prepare_paginated_list(
            items=[{'id': f['file_id'], 'title': f['file_name']} for f in files],
            current_page=page,
            id_prefix='file'
        )
        
        self.send_whatsapp_message(
            message_type='interactive',
            body={
                "type": "list",
                "header": {"type": "text", "text": "Select a File"},
                "body": {"text": "Start chatting after selecting a file"},
                "footer": {"text": f"Page {page} of {total_pages}"},
                "action": {
                    "button": "Choose option",
                    "sections": [{"title": "Available Files", "rows": rows}]
                }
            }
        )
        
    def send_progress_message(self):
        if self.section_id is None:
            self.send_whatsapp_message(body="No Section selected. Please select a section.")
            return
        
        section_learned_status_obj = db_helper.find_one(
            queries.FIND_DOCGUIDE_SECTIONS_LEARNED_STATUS_BY_ORGANIZATION_ID_AND_USER_ID_AND_SECTION_IDS,
            self.org_id, self.user_id, [self.section_id])
        
        learned_status = section_learned_status_obj.get('learned_status', 'INITIAL')
        assessment_score = section_learned_status_obj.get('assessment_score', 0)
        
        self.send_whatsapp_message(body=f"Section learned status: {learned_status}, Assessment score: {assessment_score}")
        
    def process_next_command(self, selection_id):
        if self.file_id:
            return self.send_section_list(page=selection_id)
        
        return self.send_file_list(page=selection_id)
    
        
    ########################################################################
    # Chat Helpers
    ########################################################################
    
    def chat_with_docguide(self):
        section_chat_manager = SectionChatManager()
        section_chat_manager.organization_id = self.org_id
        section_chat_manager.user_id = self.user_id
        section_chat_manager.file_id = self.file_id
        section_chat_manager.section_id = self.section_id
        section_chat_manager.user_query = self.message
        section_chat_manager.platform = 'WHATSAPP'
        
        docguide_session_obj = db_helper.find_one(queries.FIND_DOCGUIDE_SESSION_BY_USER_ID, self.user_id)
        logger.info(f"Docguide session object: {docguide_session_obj}")
        section_chat_manager.thread_id = docguide_session_obj.get('thread_id', None)
        logger.info(f"`chat_with_docguide` thread_id: {section_chat_manager.thread_id}")
        
        
        if not section_chat_manager.thread_id:
            thread = chats_helper.create_thread({'user_id': self.user_id, 'organization_id': self.org_id, 'module': 'DOC_GUIDE', 'type': 'SECTIONS', 'section_id': self.section_id, 'file_id': self.file_id })
            section_chat_manager.thread_id = thread.get('thread_id')
            section_chat_manager.stage_id = SectionStage.INITIAL_CHAT
        else:
            section_chat_manager.stage_id = docguide_session_obj.get('stage_id', SectionStage.INITIAL_CHAT)
            
            
        logger.info(f"section_chat_manager.stage_id: {section_chat_manager.stage_id}")
        
            
        docguide_response = section_chat_manager.fetch_stage_data()
        
        if section_chat_manager.stage_id == SectionStage.COMPLETED:
            # In this case, the docguide_response.message is the next section id
            next_section_id = docguide_response.message
            
            if not next_section_id:
                self.send_whatsapp_message(body="This was the last section. You can select a different file.")
                return
            
            self.update_docguide_session_section_id(next_section_id) 
            self.send_whatsapp_message(body=f"You've now selected the next section. Send a message to continue.")
            return
        
        
        self.send_whatsapp_message(body=docguide_response.message)
        
        # If Assessment Score is greater than 90 send action items too
        if docguide_response.options:
            self.send_whatsapp_message(
                message_type='interactive',
                body={
                    "type": "list",
                    "header": {"type": "text", "text": "Choose an Option"},
                    "body": {"text": "It looks like you've mastered this chapter. Do you have any more questions, or would you like to move on to the next chapter?"},
                    "footer": {"text": f""},
                    "action": {
                        "button": "Choose option",
                        "sections": [{"title": "Available Files", "rows": docguide_response.options}]
                    }
                }
            )
        
        # Condition required to change from INITIAL_CHAT to CONVERSATION stage
        # For all other cases no change in stage is required, only need to save the current stage_id in DB
        # Also adds the thread_id to the session table
        if section_chat_manager.stage_id == SectionStage.INITIAL_CHAT:   
            db_helper.execute(queries.UPDATE_THREAD_ID_AND_STAGE_ID_OF_DOCGUIDE_SESSION, section_chat_manager.thread_id, SectionStage.CONVERSATION, self.user_id)
        else:
            db_helper.execute(queries.UPDATE_THREAD_ID_AND_STAGE_ID_OF_DOCGUIDE_SESSION, section_chat_manager.thread_id, section_chat_manager.stage_id, self.user_id)
        
    def check_for_commands(self):        
        if self.message.startswith('/'):
            command = self.message[1:].lower().strip()
            
            if command in ['file', 'section', 'progress']:
                return command
                
            logger.warning(f"Unsupported slash command: {command}")
            self.send_whatsapp_message(body=WebhookReplies.INVALID_COMMAND)
            return None
        
        system_content = '''
        Your task is to **strictly analyze** whether a message explicitly mentions or requests selecting/changing a file or section. If it does, respond with a structured JSON output.  

        **Key Rules:**  
        1. Detect **explicit** mentions or requests involving file or section selection/change.  
        2. Single-word mentions of "file" or "section" must also be considered commands.  
        3. Do not infer or assume the user's intent if the message is ambiguous or lacks direct language about selecting/changing a file or section (except for single words as specified above).  
        4. For all other messages, including unrelated or vague content, return `None`.  

        **Response format:**  
        ```json  
        {  
            "command": None,  
            "type": None  
        }  
        '''
        
        openai_helper = OpenAIHelper()
        response = json.loads(openai_helper.callai_json(system_content, self.message, "admin"))
        logger.info(f"OpenAI command detection: {response}")
        
        return response.get('type')
        
    ########################################################################
    # Helpers
    ########################################################################
    
    def get_user_and_session(self):
        if not (user_obj := db_helper.find_one(queries.FIND_USER_BY_PHONE_NUMBER, self.phone_number)):
            logger.error(f"User with phone number {self.phone_number} not found!")
            self.send_whatsapp_message(body=WebhookReplies.PHONE_NUMBER_NOT_FOUND)
            return
        self.user_id = user_obj['id']
        
        if not (org_obj := db_helper.find_one(queries.FIND_ORG_ID_BY_USER_ID, self.user_id)) or not org_obj.get('org_id'):
            logger.error(f"Organization not found for user {self.user_id}!")
            self.send_whatsapp_message(body=WebhookReplies.ORGANIZATION_NOT_FOUND)
            return
        self.org_id = org_obj['org_id']
        
        session = db_helper.find_one(queries.FIND_DOCGUIDE_SESSION_BY_USER_ID, self.user_id)
        if not session:
            session = db_helper.execute(queries.INSERT_DOCGUIDE_SESSION, self.user_id, None, "WHATSAPP")
            logger.info(f"Created new session for user: {self.user_id}")
        
        self.file_id = session.get('file_id')
        self.section_id = session.get('section_id')
        
        logger.info(f"User: {self.user_id}, Org: {self.org_id}, File: {self.file_id}, Section: {self.section_id}")
        
    def prepare_paginated_list(self, items, current_page=1, id_prefix=''):
        PAGE_SIZE = 9
        start_idx = (current_page - 1) * PAGE_SIZE
        end_idx = start_idx + PAGE_SIZE
        total_pages = (len(items) + PAGE_SIZE - 1) // PAGE_SIZE
        
        current_items = items[start_idx:end_idx]
        rows = [{
            "id": f"{id_prefix}_{item.get('id')}",
            "title": item.get('title', '')[:24],
            "description": item.get('title', '')[:72]
        } for item in current_items]
        
        if current_page < total_pages:
            rows.append({
                "id": f"next_{current_page + 1}",
                "title": "Show More",
                "description": f"Go to Page {current_page + 1} of {total_pages}"
            })
            
        return rows, total_pages
    
    def update_docguide_session_file_id(self, file_id):
        if not (file_obj := db_helper.find_one(queries.FIND_DOCGUIDE_FILES_BY_FILE_IDS, file_id)) or file_obj.get('org_id') != self.org_id:
            logger.error(f"Invalid file access FILE_ID: {file_id}, ORG_ID: {self.org_id}")
            self.send_whatsapp_message(body=WebhookReplies.FILE_NOT_FOUND)
            return
            
        db_helper.execute(queries.UPDATE_FILE_ID_OF_DOCGUIDE_SESSION, file_id, "WHATSAPP", self.user_id)
        self.file_id = file_id
        logger.info(f"Updated session file_id to {file_id} for user {self.user_id}")

    def update_docguide_session_section_id(self, section_id, reset=False):
        
        # Any change in section will reset the thread_id and stage_id
        db_helper.execute(queries.UPDATE_THREAD_ID_AND_STAGE_ID_OF_DOCGUIDE_SESSION, None, 'INITIAL_CHAT', self.user_id)

        if reset:
            # Reset Section ID
            db_helper.execute(queries.UPDATE_SECTION_ID_OF_DOCGUIDE_SESSION, None, self.user_id)
            self.section_id = None
            return
            
        if not (section_obj := db_helper.find_one(queries.FIND_DOCGUIDE_SECTIONS_BY_SECTION_ID, section_id)) or section_obj.get('file_id') != self.file_id:
            
            logger.error(f"Wrong section choice, section not associated with file FILE_ID: {self.file_id}, SECTION_ID: {section_id}")
            self.send_whatsapp_message(body=WebhookReplies.INVALID_SECTION)
            return
        
        db_helper.execute(queries.UPDATE_SECTION_ID_OF_DOCGUIDE_SESSION, section_id, self.user_id)
        self.section_id = section_id
        logger.info(f"Updated session section_id to {self.section_id} for user {self.user_id}")
        

@dataclass(frozen=True)
class WebhookReplies:
    PHONE_NUMBER_NOT_FOUND = "It seems like you have not registered with us. Please register with us to use this service"
    ORGANIZATION_NOT_FOUND = "Organization not found. Please contact your organization admin to register with us"
    FILE_NOT_FOUND = "It seems like you have selected a file that no longer exists or is not associated with your organization"
    INVALID_SECTION = "It seems like you've not selected a File or the Section you have selected is not associated with the File you have selected"
    OPTION_DISABLED = "Option is currenly disabled"
    INVALID_CHOICE = "It seems like you've selected an invalid option."
    NO_SECTIONS_FOUND = "There are no sections associated with this file. Please select a different file."
    NO_FILES_FOUND = "There are no files associated with this organization. Please contact your organization admin to upload files."
    INVALID_COMMAND = "It seems like you've entered an invalid command. Please try again."
