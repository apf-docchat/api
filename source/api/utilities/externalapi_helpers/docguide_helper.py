from dataclasses import dataclass
import json
import logging
from typing import List, Optional
from urllib.parse import quote

from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, SectionStage
from source.api.utilities.externalapi_helpers import chats_helper, collections_helper
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.api.utilities.vector_search import VectorSearch
from source.common import config

logger = logging.getLogger('app')

def get_docguide_files():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        organization_name = request.context['organization_name']
        files = db_helper.find_many(queries.FIND_DOCGUIDE_FILES_BY_ORGANIZATION_ID, organization_id)
        files_response = [dict(file_id=file.get('file_id'), file_name=file.get('file_name'),
                               file_url=f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file.get("file_name"))}', collection_id=file.get('collection_id'))
                          for file in files]
        return files_response
    except Exception as e:
        logger.error(e)
        raise e


def get_docguide_collection_files():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_name = request.context['organization_name']
        organization_id = request.context['organization_id']
        user_id = request.context['user_id']
        # files = find_docguide_files_by_organization_id(organization_id)
        docguide_files = db_helper.find_many(queries.FIND_DOCGUIDE_FILES_BY_ORGANIZATION_ID, organization_id)
        docguide_file_ids = [dfile['doc_file_id'] for dfile in docguide_files]
        # collections = find_collections_by_organization_id(request.context['organization_id'])
        # collections = db_helper.find_many(queries.FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id)
        collection_ids = collections_helper.get_collection_ids_for_user(user_id, organization_id)
        collections = db_helper.find_many(queries.V2_FIND_COLLECTIONS_BY_ORGANIZATION_ID, organization_id, collection_ids)

        if len(collections) == 0:
            return []
        for collection in collections:
            collection['files'] = []
        collection_ids = [collection['collection_id'] for collection in collections]

        # files = find_files_by_collection_ids(collection_ids)
        #files = db_helper.find_many(queries.FIND_FILES_BY_COLLECTION_IDS, collection_ids)
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_IDS, collection_ids)

        for file_entry in files:
            collection = list(filter(lambda x: x["collection_id"] == file_entry['collection_id'], collections))[0]
            is_file_exist_in_docguide_files = file_entry['file_id'] in docguide_file_ids
            collection['files'].append({'file_id': file_entry['file_id'],
                                        'file_name': file_entry['file_name'],
                                        'file_url': f'{config.STATIC_FILES_PREFIX}/{organization_name}/{quote(file_entry["file_name"])}',
                                        'is_processed': is_file_exist_in_docguide_files})
        result = collections
        return result
        # return files
    except Exception as e:
        logger.error(e)
        raise e


def get_docguide_sections():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context.get("user_id")
        file_id = request.args.get('file_id')
        sections = db_helper.find_many(queries.FIND_DOCGUIDE_SECTIONS_BY_ORGANIZATION_ID_AND_FILE_ID, organization_id,
                                       file_id)
        section_ids = [section.get('section_id') for section in sections]
        section_users = db_helper.find_many(
            queries.FIND_DOCGUIDE_SECTIONS_LEARNED_STATUS_BY_ORGANIZATION_ID_AND_USER_ID_AND_SECTION_IDS,
            organization_id, user_id, section_ids)
        section_chat_filter = dict(user_id=user_id, organization_id=organization_id, module='DOC_GUIDE',
                                   type='SECTIONS', file_id=int(file_id))
        sections_threads = chats_helper.get_threads_by_filter(section_chat_filter)
        sections_response = []
        for section in sections:
            learned_section = next((section_user for section_user in section_users if
                                    section_user.get('section_id') == section.get('section_id')), {})
            section_threads = list(
                filter(lambda thread: thread.get('section_id') == section.get('section_id'), sections_threads))
            latest_thread = section_threads[-1] if section_threads else None
            latest_thread_id = latest_thread.get("thread_id") if latest_thread and learned_section else None
            # if len(section_users) == 0 and section.get('order_number') == 0:

            #     learned_section['is_enabled'] = True
            sections_response.append(dict(file_id=section.get('file_id'), section_id=section.get('section_id'),
                                          section_title=section.get('section_title'),
                                          section_status=learned_section.get('learned_status', None),
                                          section_assessment_score=learned_section.get('assessment_score', None),
                                          # is_enabled=True if learned_section else False,
                                          latest_thread_id=latest_thread_id,
                                          is_enabled=True))
        return sections_response
    except Exception as e:
        logger.error(e)
        raise e


def get_docguide_section(section_id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context.get("user_id")
        section = db_helper.find_one(queries.FIND_DOCGUIDE_SECTIONS_BY_SECTION_ID, section_id)
        section_id = section.get('section_id')
        section_users = db_helper.find_many(
            queries.FIND_DOCGUIDE_SECTIONS_LEARNED_STATUS_BY_ORGANIZATION_ID_AND_USER_ID_AND_SECTION_IDS,
            organization_id, user_id, [section_id])
        section_chat_filter = dict(user_id=user_id, organization_id=organization_id, module='DOC_GUIDE',
                                   type='SECTIONS', section_id=int(section_id))
        sections_threads = chats_helper.get_threads_by_filter(section_chat_filter)
        sections_response = []
        learned_section = next((section_user for section_user in section_users if
                                section_user.get('section_id') == section.get('section_id')), {})
        # section_threads = list(
        #     filter(lambda thread: thread.get('section_id') == section.get('section_id'), sections_threads))
        # latest_thread = section_threads[-1] if section_threads else None
        # latest_thread_id = latest_thread.get("thread_id") if latest_thread and learned_section else None

        section_threads = []
        for section_thread in sections_threads:
            thread_messages = section_thread.get('messages')
            user_messages = list(
                filter(lambda message: message.get('role') == 'user', thread_messages))
            last_user_message = user_messages[-1] if user_messages else {}
            thread_title = last_user_message.get('content', None)
            thread_messages_count = len(thread_messages)
            thread_created_datetime = section_thread.get('thread_created_datetime', None)
            if thread_created_datetime:
                thread_created_datetime = thread_created_datetime.replace(microsecond=0)
            section_threads.append(dict(thread_id=section_thread.get('thread_id'),
                                        thread_title=thread_title,
                                        thread_created_datetime=thread_created_datetime.isoformat(),
                                        thread_messages_count=thread_messages_count))
        sections_response.append(dict(file_id=section.get('file_id'), section_id=section.get('section_id'),
                                      section_title=section.get('section_title'),
                                      section_status=learned_section.get('learned_status', None),
                                      section_assessment_score=learned_section.get('assessment_score', None),
                                      # is_enabled=True if learned_section else False,
                                      section_threads=section_threads,
                                      is_enabled=True))
        return sections_response
    except Exception as e:
        logger.error(e)
        raise e


def file_process():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        file_ids = request.json.get('file_ids')
        files = db_helper.find_many(queries.FIND_FILES_BY_FILES_IDS, file_ids)
        for file in files:
            file_name = file['file_name']
            file_id = file['file_id']
            db_helper.execute(queries.INSERT_DOCGUIDE_FILES, file_name, organization_id, file_id)
    except Exception as e:
        logger.error(e)
        raise e


def docguide_delete_files():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        file_ids = request.json.get('file_ids')
        db_helper.execute(queries.DELETE_DOCGUIDE_FAQ_BY_FILE_IDS_AND_ORGANIZATION_ID, file_ids, organization_id)
        db_helper.execute(queries.DELETE_DOCGUIDE_SECTIONS_BY_FILE_IDS_AND_ORGANIZATION_ID, file_ids, organization_id)
        db_helper.execute(queries.DELETE_DOCGUIDE_FILES_BY_FILE_IDS_AND_ORGANIZATION_ID, file_ids, organization_id)
    except Exception as e:
        logger.error(e)
        raise e


def docguide_sections_chat_summary():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context['user_id']
        file_id = request.json.get('file_id')
        section_id = request.json.get('section_id')
        section = db_helper.find_one(queries.FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_SECTION_ID,
                                     organization_id, file_id, section_id)
        section_content = section['section_content']
        default_query = 'Generate a summary of this chapter'

        thread_payload = dict(user_id=user_id, organization_id=organization_id, module='DOC_GUIDE')
        thread = chats_helper.create_thread(thread_payload)
        thread_id = thread['thread_id']

        user_chat_payload = dict(role='user', content=default_query, type='SYSTEM_GENERATED')
        chats_helper.add_chat_history(thread_id, user_chat_payload)

        def get_streamed_message():
            try:
                openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_04)
                stream_data = openai_helper.callai_streaming(section_content, default_query, user_id)
                for event, message in stream_data:
                    if event == 'CHUNK':
                        message = message.replace('\n', '<br>')
                        yield f"data:{message}\n\n"
                    if event == 'FINAL_MESSAGE':
                        # storing assistant chat history
                        assistant_chat_payload = dict(role='assistant', content=message)
                        chats_helper.add_chat_history(thread_id, assistant_chat_payload)
                        final_message = dict(message=message, thread_id=thread_id)
                        final_message = json.dumps(final_message)
                        yield f"event: finalOutput\ndata:{final_message}\n\n"
            except Exception as ee:
                print(ee)
                raise ee

        return get_streamed_message()
    except Exception as e:
        logger.error(e)
        raise e


def docguide_sections_chat():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        user_id = request.context['user_id']
        file_id = request.json.get('file_id')
        section_id = request.json.get('section_id')
        query = request.json.get('user_query')
        thread_id = request.json.get('thread_id')
        stage_id = request.json.get('stage_id')
        metadata = request.json.get('metadata')

        # creating thread if not already exist
        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='DOC_GUIDE', type='SECTIONS',
                                  section_id=section_id, file_id=file_id)
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread.get('thread_id')

        section_chat_manager = SectionChatManager()
        section_chat_manager.organization_id = organization_id
        section_chat_manager.user_id = user_id
        section_chat_manager.file_id = file_id
        section_chat_manager.section_id = section_id
        section_chat_manager.user_query = query
        section_chat_manager.thread_id = thread_id
        section_chat_manager.stage_id = stage_id
        if metadata:
            section_chat_manager.metadata = metadata
        return section_chat_manager.fetch_stage_data()

    except Exception as e:
        logger.error(e)
        final_message = dict(
            message="Sorry, I am having some trouble to respond at the moment. Please try again later!", )
        final_message = json.dumps(final_message)
        return f"event: finalOutput\ndata:{final_message}\n\n"


class SectionChatManager:

    def __init__(self):
        self.section_content = ''
        self.user_query = ''
        self.user_id = None
        self.thread_id = None
        self.stage_id = None
        self.previous_chat_context = None
        self.organization_id = None
        self.file_id = None
        self.section = None
        self.section_id = None
        self.assistant_message = ''
        self.system_content = ''
        self.final_message_extra_metadata = dict()
        self.assessment_score = 0
        self.metadata = dict()
        self.platform = 'WEB'

    def fetch_stage_data(self):
        try:
            if self.stage_id == SectionStage.INITIAL_CHAT or self.stage_id == '' or self.stage_id is None:
                self.fetch_section_content()
                prompts = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docguide',
                                             'INITIAL_CHAT')
                prompt = prompts.get('prompt_text')
                self.system_content = prompt + '\n\nCONTEXT:\n' + self.section_content

                self.add_action_chat_history('Summarising chapter ' + self.section.get('section_title'))
                self.user_query = ""
                db_helper.execute(queries.REPLACE_DOCGUIDE_SECTIONS_LEARNED_STATUS,
                                  self.organization_id, self.section_id, self.user_id, 'INITIAL')
                if self.platform == 'WHATSAPP':
                    return self.generate_message()
                return self.generate_streamed_message()

            if self.stage_id == SectionStage.CONVERSATION:
                self.fetch_section_content()
                self.fetch_previous_chat_history()
                self.fetch_assessment_score()
                if self.assessment_score > 90:
                    self.final_message_extra_metadata.update(dict(
                        extra_query='''It looks like you've mastered this chapter. Do you have any more questions, or would you like to move on to the next chapter?''',
                        call_to_actions=[dict(label="Next Section", action="STAGE_ACTION", type="BUTTON",
                                              metadata=dict(stage_id="COMPLETED")),
                                         dict(label="Continue this Section", action="STAGE_ACTION", type="BUTTON",
                                              metadata=dict(stage_id="CONTINUE_SECTION",
                                                            tooltip="Continue with the untouched part of the section.")),
                                         dict(label="Assess Me", action="STAGE_ACTION", type="BUTTON",
                                              metadata=dict(stage_id="ASSESS_ME",
                                                            tooltip="Answer a question to test your knowledge.", ))
                                         ]))

                conversation_prompt = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME,
                                                         'docguide',
                                                         'CONVERSATION')
                conversation_prompt = conversation_prompt.get('prompt_text')

                self.system_content = conversation_prompt + '\n\nCONTEXT:\n' + self.section_content

                self.add_user_chat_history()
                if self.platform == 'WHATSAPP':
                    return self.generate_message()
                return self.generate_streamed_message()

            if self.stage_id == SectionStage.TIMED_OUT:
                self.user_query = ""
                self.fetch_section_content()
                self.fetch_previous_chat_history()
                self.fetch_assessment_score()
                call_to_actions = [dict(label="Continue this Section", action="STAGE_ACTION", type="BUTTON",
                                        metadata=dict(stage_id="CONTINUE_SECTION",
                                                      tooltip="Continue with the untouched part of the section.")),
                                   dict(label="Assess Me", action="STAGE_ACTION", type="BUTTON",
                                        metadata=dict(stage_id="ASSESS_ME",
                                                      tooltip="Answer a question to test your knowledge.", ))]
                if self.assessment_score > 90:
                    call_to_actions.append(dict(label="Next Section", action="STAGE_ACTION", type="BUTTON",
                                                metadata=dict(stage_id="COMPLETED")))

                    response_payload = dict(
                        message='''Hey, are you still there? <br/>It looks like you've already covered most of the chapter. Do you have any more questions, or would you like to move on to the next chapter?''',
                        call_to_actions=call_to_actions)
                    if self.platform == 'WHATSAPP':
                        return response_payload.message
                    return self.generate_single_message(response_payload)
                else:
                    response_payload = dict(
                        message='''Hey, are you still there? <br/>Do you have any more questions?''',
                        call_to_actions=call_to_actions)
                    if self.platform == 'WHATSAPP':
                        return response_payload.message
                    return self.generate_single_message(response_payload)

            if self.stage_id == SectionStage.COMPLETED:
                self.fetch_section_content()
                response_payload = dict(action="GOTO_NEXT_SECTION",
                                        metadata=dict(section_id=self.fetch_next_section()))
                
                if self.platform == 'WHATSAPP':
                    return DocguideResponse(self.fetch_next_section()) 
                return self.generate_single_message(response_payload)

            if self.stage_id == SectionStage.CONTINUE_SECTION:
                self.user_query = ""
                self.fetch_section_content()
                self.fetch_previous_chat_history()
                self.fetch_assessment_score()
                conversation_prompt = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME,
                                                         'docguide',
                                                         'CONTINUE_SECTION')
                conversation_prompt = conversation_prompt.get('prompt_text')

                self.system_content = conversation_prompt + '\n\nCONTEXT:\n' + self.section_content
                self.add_action_chat_history('Chose to continue this section.')
                init_output = dict(stage_id=self.stage_id, thread_id=self.thread_id,
                                   message='Chose to continue this section.', role='action')
                
                if self.platform == 'WHATSAPP':
                    return self.generate_message()
                
                return self.generate_streamed_message(init_output=init_output)

            if self.stage_id == SectionStage.ASSESS_ME:
                self.user_query = ""
                self.fetch_section_content()
                self.fetch_previous_chat_history()
                self.fetch_assessment_score()
                
                conversation_prompt = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docguide', 'ASSESS_ME')
                conversation_prompt = conversation_prompt.get('prompt_text')

                self.system_content = conversation_prompt + '\n\nCONTEXT:\n' + self.section_content
                self.add_action_chat_history('Chose to assess me.')
                init_output = dict(stage_id=self.stage_id, thread_id=self.thread_id, message='Chose to assess me.',
                                   role='action')
                
                if self.platform == 'WHATSAPP':
                    return self.generate_message()
                
                return self.generate_streamed_message(init_output=init_output)
        except Exception as e:
            logger.error(e)
            response_payload = dict(
                message="Sorry, I am having some trouble to respond at the moment. Please try again later!")
            
            if self.platform =='WHATSAPP':
                return DocguideResponse(response_payload.get('message'))
            
            return self.generate_single_message(response_payload)

    def fetch_assessment_score(self):
        try:
            section_user = db_helper.find_one(queries.FIND_DOCGUIDE_SECTIONS_LEARNED_STATUS_BY_ORGANIZATION_ID_AND_USER_ID_AND_SECTION_IDS, self.organization_id, self.user_id, [self.section_id])
            
            current_assessment_score = section_user.get('assessment_score', 0)
            
            assessment_prompt = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docguide', 'ASSESSMENT')
            assessment_prompt = assessment_prompt.get('prompt_text')
            assessment_system_content = assessment_prompt + '\n\nASSESSMENT_SCORE:' + str(current_assessment_score) + '\n\nCONTEXT:\n' + self.section_content
            
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_01)
            assessment_response = openai_helper.callai_json(assessment_system_content, '', self.user_id, extra_context=self.previous_chat_context)
            assessment_response = json.loads(assessment_response)
            
            logger.info(assessment_response)
            
            self.assessment_score = assessment_response.get('assessment_score')
            self.final_message_extra_metadata.update(dict(assessment_score=self.assessment_score))
            
            if 40 < self.assessment_score < 90:
                db_helper.execute(queries.UPDATE_STATUS_OF_DOCGUIDE_SECTIONS_LEARNED_STATUS, 'PARTIAL', self.assessment_score, self.organization_id, self.user_id, self.section_id)
            if self.assessment_score > 90:
                db_helper.execute(queries.UPDATE_STATUS_OF_DOCGUIDE_SECTIONS_LEARNED_STATUS, 'FULL', 100, self.organization_id, self.user_id, self.section_id)
        except Exception as e:
            logger.error(e)
            raise e

    def fetch_section_content(self):
        try:
            self.section = db_helper.find_one(
                queries.FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_SECTION_ID,
                self.organization_id, self.file_id, self.section_id)
            self.section_content = self.section.get('section_content')
        except Exception as e:
            logger.error(e)
            raise e

    def fetch_next_section(self):
        try:
            next_section_by_order_number = self.section.get('order_number') + 1
            section = db_helper.find_one(
                queries.FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_ORDER_NUMBER,
                self.organization_id, self.file_id, next_section_by_order_number)
            if section:
                return section.get('section_id')
            else:
                return None
        except Exception as e:
            logger.error(e)
            raise e

    def fetch_previous_chat_history(self, history_count=7):
        try:
            # fetching last n chats
            chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(self.thread_id, self.user_id)
            chat_history = chat_thread.get('messages')
            filtered_chat_history = list(filter(lambda chat: chat.get('role') != 'action', chat_history))
            self.previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                          filtered_chat_history[-history_count:] if len(filtered_chat_history) > 1]
        except Exception as e:
            logger.error(e)
            raise e

    def add_action_chat_history(self, content=''):
        try:
            # adding user chat history
            user_chat_payload = dict(role='action', content=content, stage_id=self.stage_id)
            chats_helper.add_chat_history(self.thread_id, user_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def add_user_chat_history(self):
        try:
            # adding user chat history
            user_chat_payload = dict(role='user', content=self.user_query, stage_id=self.stage_id)
            chats_helper.add_chat_history(self.thread_id, user_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def add_assistant_chat_history(self):
        try:
            # adding assistant chat history
            assistant_chat_payload = dict(role='assistant', content=self.assistant_message, stage_id=self.stage_id)
            chats_helper.add_chat_history(self.thread_id, assistant_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e
        
    def generate_message(self):
        try:
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_04)
            message = openai_helper.callai(self.system_content, self.user_query, self.user_id, extra_context=self.previous_chat_context)
            
            docguide_response = DocguideResponse(message)
            
            logger.info(f"Assessment score: {self.assessment_score}")
            if self.assessment_score > 90 and self.stage_id == SectionStage.CONVERSATION:
                docguide_response.options = []
                docguide_response.options.append(DocguideResponse.OptionTypes.CONTINUE_SECTION)
                docguide_response.options.append(DocguideResponse.OptionTypes.ASSESS_ME)
                docguide_response.options.append(DocguideResponse.OptionTypes.COMPLETED)
            
            return docguide_response
        except Exception as e:
            logger.error(e)
            raise e

    def generate_streamed_message(self, init_output=None):
        try:
            if init_output:
                init_output_message = json.dumps(init_output)
                yield f"event: initOutput\ndata: {init_output_message}\n\n"
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_04)
            stream_data = openai_helper.callai_streaming(self.system_content, self.user_query, self.user_id,
                                                         extra_context=self.previous_chat_context)
            for event, message in stream_data:
                if event == 'CHUNK':
                    message = message.replace('\n', '<br>')
                    yield f"data: {message}\n\n"
                if event == 'FINAL_MESSAGE':
                    # storing assistant chat history
                    self.assistant_message = message
                    self.add_assistant_chat_history()

                    final_message = dict(message=message, thread_id=self.thread_id)
                    final_message.update(self.final_message_extra_metadata)
                    final_message = json.dumps(final_message)
                    yield f"event: finalOutput\ndata: {final_message}\n\n"
        except Exception as ee:
            logger.error(ee)
            final_message = dict(
                message="Sorry, I am having some trouble to respond at the moment. Please try again later!",
                thread_id=self.thread_id, stage_id=self.stage_id)
            final_message = json.dumps(final_message)
            return f"event: finalOutput\ndata: {final_message}\n\n"
        
    def generate_single_message(self, payload):
        try:
            final_message = dict(thread_id=self.thread_id)
            final_message.update(payload)
            final_message.update(self.final_message_extra_metadata)
            final_message = json.dumps(final_message)
            yield f"event: finalOutput\ndata: {final_message}\n\n"
        except Exception as e:
            logger.error(e)
            final_message = dict(
                message="Sorry, I am having some trouble to respond at the moment. Please try again later!",
                thread_id=self.thread_id, stage_id=self.stage_id)
            final_message = json.dumps(final_message)
            return f"event: finalOutput\ndata: {final_message}\n\n"


def get_interactive_event_message(organization_id, file_id, section_id, user_id, thread_id):
    try:
        section = db_helper.find_one(queries.FIND_DOCGUIDE_SECTION_BY_ORGANIZATION_ID_AND_FILE_ID_AND_SECTION_ID,
                                     organization_id, file_id, section_id)
        section_content = section['section_content']
        chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(thread_id, user_id)
        chat_history = chat_thread.get('messages')

        # fetching last 7 chats
        previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                 chat_history[-7:] if len(chat_history) > 1]

        prompts = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docguide',
                                     'interactive_message_instruction')
        prompt = prompts['prompt_text']
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_03)
        interactive_message = openai_helper.callai(section_content,
                                                   prompt,
                                                   user_id,
                                                   extra_context=previous_chat_context)
        assistant_chat_payload = dict(role='assistant', content=interactive_message)
        chats_helper.add_chat_history(thread_id, assistant_chat_payload)
        payload = dict(message=interactive_message, thread_id=thread_id)
        return payload
    except Exception as e:
        print(e)
        raise e


def docguide_section_chat_events():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        file_id = request.json.get('file_id')
        user_id = request.context['user_id']
        section_id = request.json.get('section_id')
        thread_id = request.json.get('thread_id')
        event_type = request.json.get('event_type')

        # creating thread if not already exist
        if not thread_id:
            raise RuntimeError('Thread id not found!')

        if event_type == "INTERACTIVE_MESSAGE":
            return get_interactive_event_message(organization_id, file_id, section_id, user_id, thread_id)

    except Exception as e:
        print(e)
        logger.error(e)
        raise e


class DocguideResponse:
    
    @dataclass(frozen=True)
    class OptionTypes:
        CONTINUE_SECTION = {'id': 'chat_CONTINUE_SECTION', 'title': 'Continue Section', 'description': 'Continue with the untouched part of the section.'}
        ASSESS_ME = {'id': 'chat_ASSESS_ME', 'title': 'Assess Me', 'description': 'Answer a question to test your knowledge.'}
        COMPLETED = {'id': 'chat_COMPLETED', 'title': 'Next Section', 'description': ''}

            
    def __init__(self, message: str):
        self.message: str = message
        self.options: Optional[List[self.OptionTypes]]  = None

def docguide_general_query():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = request.context['organization_name']
        user_id = request.context['user_id']
        file_id = request.json.get('file_id')
        query = request.json.get('user_query')
        thread_id = request.json.get('thread_id')

        # creating thread if not already exist
        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='DOC_GUIDE', type='GENERAL')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']

        # storing user chat history
        user_chat_payload = dict(role='user', content=query)
        chats_helper.add_chat_history(thread_id, user_chat_payload)

        chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(thread_id, user_id)
        chat_history = chat_thread.get('messages')

        # fetching last 7 chats
        previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                 chat_history[-7:-1] if len(chat_history) > 1]

        docguide_faqs = db_helper.find_many(queries.FIND_DOCGUIDE_FAQ_BY_FILE_ID_AND_ORGANIZATION_ID, file_id,
                                            organization_id)
        faq_context = [dict(faq_id=faq['faq_id'], faq_title=['faq_title'], faq_content=faq['faq_content']) for faq in
                       docguide_faqs]
        faq_context = json.dumps(faq_context)

        prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docguide')
        faq_prompt = [prompt for prompt in prompts if prompt.get('prompt_name') == 'faq_instruction'][0]
        faq_prompt = faq_prompt.get('prompt_text')

        faq_system_content = faq_prompt + '\nContext: \n' + faq_context

        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_GUIDE_02)
        faq_response = openai_helper.callai_json(faq_system_content, query, user_id)
        faq_response = json.loads(faq_response)

        if faq_response.get('faq_id') != 0:
            docguide_faq = [faq for faq in docguide_faqs if faq.get('faq_id') == faq_response.get('faq_id')][0]
            docguide_faq_content = docguide_faq.get('faq_content')
            assistant_chat_payload = dict(role='assistant', content=docguide_faq_content)
            chats_helper.add_chat_history(thread_id, assistant_chat_payload)

            final_message = dict(message=docguide_faq_content, thread_id=thread_id)
            final_message = json.dumps(final_message)
            return f"event: finalOutput\ndata: {final_message}\n\n"

        docguide_file = db_helper.find_one(queries.FIND_DOCGUIDE_FILES_BY_FILE_IDS, [file_id])
        collection_file_id = docguide_file['doc_file_id']
        collection_file = db_helper.find_one(queries.FIND_FILES_BY_FILES_IDS, [collection_file_id])
        collection_filename = collection_file['file_name']

        general_prompt = [prompt for prompt in prompts if prompt.get('prompt_name') == 'respond_only_based_on_context'][
            0]
        general_prompt = general_prompt.get('prompt_text')

        vs = VectorSearch(query)
        vs.embed_query()
        vs.vector_search(search_filter={"orgname": {"$eq": orgname}, "filename": {"$in": [collection_filename]}})
        vs.parse_content(chunk_size=32000)
        context_prompt = vs.context_prompt

        system_content = general_prompt + "\nContext:\n" + context_prompt

        def get_streamed_message():
            try:
                stream_data = openai_helper.callai_streaming(system_content, query, user_id,
                                                             extra_context=previous_chat_context)
                for event, message in stream_data:
                    if event == 'CHUNK':
                        message = message.replace('\n', '<br>')
                        yield f"data: {message}\n\n"
                    if event == 'FINAL_MESSAGE':
                        # storing assistant chat history
                        assistant_chat_payload = dict(role='assistant', content=message)
                        chats_helper.add_chat_history(thread_id, assistant_chat_payload)

                        final_message = dict(message=message, thread_id=thread_id)
                        final_message = json.dumps(final_message)
                        yield f"event: finalOutput\ndata: {final_message}\n\n"
            except Exception as ee:
                print(ee)
                logger.error(ee)
                final_message = dict(
                    message="Sorry, I am having some trouble to respond at the moment. Please try again later!",
                    thread_id=thread_id)
                final_message = json.dumps(final_message)
                return f"event: finalOutput\ndata:{final_message}\n\n"

        return get_streamed_message()

    except Exception as e:
        print(e)
        logger.error(e)
        final_message = dict(
            message="Sorry, I am having some trouble to respond at the moment. Please try again later!", )
        final_message = json.dumps(final_message)
        return f"event: finalOutput\ndata:{final_message}\n\n"
