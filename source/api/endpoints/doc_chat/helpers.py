import asyncio
import json
import logging
from io import StringIO
from typing import List

import pandas as pd
import tiktoken
from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, Prompts, DocChatSearchType, StreamEvent
from source.api.utilities.externalapi_helpers import chats_helper
from source.api.utilities.externalapi_helpers.openai_helper import LLMCallException, OpenAIHelper
from source.api.utilities.prompts import StaticPrompts
from source.common import config

logger = logging.getLogger('app')

def get_latest_chat_thread_id():
    try:
        db = db_helper.get_mongodb()
        users_collection = db.get_collection('users')
        user_id = request.context.get("user_id")
        organization_name = request.context.get("organization_name")
        user = db_helper.find_one(queries.FIND_USER_BY_USER_ID, user_id)

        username = user.get('username')

        # Define the filter criteria
        filter_criteria = {'username': username, 'orgname': organization_name}

        user_document = users_collection.find_one(filter_criteria)

        # Check if the document was found and return the latestchatthreadid
        if user_document and 'latestchatthreadid' in user_document:
            print(f"inside get_latestchatthreadid: {user_document['latestchatthreadid']}")
            return user_document['latestchatthreadid']
    except Exception as e:
        print(e)
        return "new_chat"


def docchat_query():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context.get('organization_id')
        user_id = request.context.get('user_id')

        thread_id = request.json.get('thread_id')
        user_query = request.json.get("user_query")
        collection_id = request.json.get("collection_id")

        # creating thread if not already exist
        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='DOC_CHAT')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread.get('thread_id')

        logger.info(
            f"Getting docchat request with query [{user_query}], collection id [{collection_id}], thread id [{thread_id}]")

        docchat_manager = DocChatManager()
        docchat_manager.user_id = user_id
        docchat_manager.collection_id = collection_id
        docchat_manager.organization_id = organization_id
        docchat_manager.user_query = user_query
        docchat_manager.thread_id = thread_id
        return docchat_manager.initiate_docchat()

    except Exception as e:
        logger.error(f"Error occurred during docchat query, Error: [{str(e)}]")


def update_faq_response():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context.get('organization_id')
        user_id = request.context.get('user_id')

        # thread_id = request.json.get('thread_id')
        faq_id = request.json.get("faq_id")
        collection_id = request.json.get("collection_id")

        if faq_id is None or collection_id is None:
            raise RuntimeError("FAQ ID and Collection ID are required!")

        faq = db_helper.find_one(queries.FIND_DOCCHAT_FAQ_BY_FAQ_IDS, [faq_id])
        if not faq:
            raise RuntimeError("FAQ not found!")

        logger.info(
            f"Getting docchat faq improve request with query [{faq.get('faq_question')}], collection id [{collection_id}], faq id [{faq_id}]")

        docchat_manager = DocChatManager()
        docchat_manager.find_prompts()
        docchat_manager.user_id = user_id
        docchat_manager.collection_id = collection_id
        docchat_manager.organization_id = organization_id
        docchat_manager.faq_item = faq
        docchat_manager.user_query = faq.get('faq_question')
        docchat_manager.find_prompts()
        docchat_manager.find_collection()
        docchat_manager.fetch_previous_chat_history()
        if docchat_manager.contains_noun():
            docchat_manager.filter_metadata_by_NER()
        else:
            docchat_manager.find_metadata_csv()
        return docchat_manager.metadata_search(update_faq=True)
    except Exception as e:
        logger.error(f"Error in improve_chat_response: {str(e)}")
        raise e


class DocChatManager:

    def __init__(self):
        self.collection_id = None
        self.user_query = None
        self.organization_id = None
        self.user_id = None
        self.user = None
        self.collection = None
        self.collection_name = None
        self.collection_custom_instruction = None
        self.metadata_header = None
        self.metadata_list = None
        self.metadata_batch_size = config.METASEARCH_BATCH_SIZE
        self.metadata_ner_filter_batch_size = config.METASEARCH_NER_FILTER_BATCH_SIZE
        self.docchat_prompts = None
        self.previous_chat_context = None
        self.thread_id = None
        self.chat_thread = None
        self.final_message = None
        self.final_message_extra_metadata = dict()
        self.faq_item = None

    def find_prompts(self):
        try:
            logger.info(f"Finding prompts by prompt type [docchat]")
            self.docchat_prompts = db_helper.find_many(queries.FIND_PROMPT_BY_PROMPT_TYPE, 'docchat')
        except Exception as e:
            logger.error(f"Error occurred during finding prompts, Error: [{str(e)}]")

    def find_metadata(self):
        try:
            logger.info(f"Finding metadata for collection [{self.collection_id}]")
            metadata = db_helper.find_many(
                queries.FIND_DOCCHAT_METADATA_WITH_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                self.organization_id, self.collection_id)
            df = pd.DataFrame(metadata)

            # Extract the order_number and field
            field_order_df = df[['field', 'order_number']].drop_duplicates().set_index('field')

            pivot_df = df.pivot(index='file_id', columns='field', values='value')
            pivot_df.columns.name = None

            sorted_fields = field_order_df.sort_values(by='order_number').index.tolist()
            pivot_df = pivot_df[sorted_fields]

            self.metadata_list = pivot_df.to_dict(orient='records')
            logger.info(f"Found [{len(self.metadata_list)}] metadata in collection [{self.collection_id}]")
        except Exception as e:
            logger.error(f"Error occurred during finding metadata, Error: [{str(e)}]")

    def find_metadata_csv(self):
        try:
            logger.info(f"Finding metadata for collection [{self.collection_id}]")
            metadata = db_helper.find_many(
                queries.FIND_DOCCHAT_METADATA_WITH_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                self.organization_id, self.collection_id)

            if metadata is None or len(metadata) == 0:
                self.metadata_list = []
                return

            df = pd.DataFrame(metadata)

            # Extract the order_number and field
            field_order_df = df[['field', 'order_number']].drop_duplicates().set_index('field')

            pivot_df = df.pivot(index='file_id', columns='field', values='value')
            pivot_df.columns.name = None

            # Sort columns based on order_number
            sorted_fields = field_order_df.sort_values(by='order_number').index.tolist()
            pivot_df = pivot_df[sorted_fields]

            csv_buffer = StringIO()
            pivot_df.head(0).to_csv(csv_buffer, index=True)
            self.metadata_header = csv_buffer.getvalue().strip()

            csv_row_list = []
            for _, row in pivot_df.iterrows():
                csv_buffer = StringIO()
                row.to_frame().T.to_csv(csv_buffer, header=False, index=True)
                csv_row_list.append(csv_buffer.getvalue().strip())

            self.metadata_list = csv_row_list
            logger.info(f"Found [{len(self.metadata_list)}] metadata in collection [{self.collection_id}]")
        except Exception as e:
            logger.error(f"Error occurred during finding metadata, Error: [{str(e)}]")
            raise f'Error in find_metadata_csv: {str(e)}'

    def filter_metadata_by_NER(self):
        try:
            logger.info(f"Finding metadata for collection [{self.collection_id}]")
            metadata = db_helper.find_many(
                queries.FIND_DOCCHAT_METADATA_WITH_SCHEMA_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                self.organization_id, self.collection_id)
            if metadata is None or len(metadata) == 0:
                self.metadata_list = []
                return

            df = pd.DataFrame(metadata)

            field_order_df = df[['field', 'order_number']].drop_duplicates().set_index('field')
            pivot_df = df.pivot(index='file_id', columns='field', values='value').reset_index()
            pivot_df.columns.name = None

            sorted_fields = ['file_id'] + field_order_df.sort_values(by='order_number').index.tolist()
            pivot_df = pivot_df[sorted_fields]

            csv_buffer = StringIO()
            pivot_df.head(0).to_csv(csv_buffer, index=False)
            self.metadata_header = csv_buffer.getvalue().strip()

            self.metadata_list = pivot_df.to_dict(orient='records')

            filtered_metadata = [
                {k: v for k, v in metadata.items() if k in ('NER', 'file_id')}
                for metadata in self.metadata_list
            ]

            ner_filter_prompt = self.get_prompt(Prompts.NER_FILTER)
            result_file_ids: List[int] = []
            logger.info(
                f"Starting NER-based filtering with batch size of [{self.metadata_ner_filter_batch_size}] of total items [{len(filtered_metadata)}]")
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_07)

            for i in range(0, len(filtered_metadata), self.metadata_ner_filter_batch_size):
                chunk = filtered_metadata[i:i + self.metadata_ner_filter_batch_size]
                logger.info(f"Chunk range [{i}-{i + len(chunk)}], current results size [{len(result_file_ids)}]")

                context = '\n'.join(f"{item['file_id']},{item['NER']}" for item in chunk)

                system_content = ner_filter_prompt
                user_content = f"{self.user_query}\n{context}"

                chunk_results = openai_helper.callai_json(system_content, user_content, self.user_id or "admin")
                result_file_ids.extend(json.loads(chunk_results)['file_ids'])

            logger.info(f"NER-based filtering completed with [{len(result_file_ids)}] results")
            if len(result_file_ids) != 0:
                result_file_ids_set = set(result_file_ids)
                self.metadata_list = [metadata for metadata in self.metadata_list if metadata['file_id'] in result_file_ids_set]

            pivot_df = pd.DataFrame(self.metadata_list)
            csv_row_list = []
            for _, row in pivot_df.iterrows():
                csv_buffer = StringIO()
                row.to_frame().T.to_csv(csv_buffer, header=False, index=False)
                csv_row_list.append(csv_buffer.getvalue().strip())

            self.metadata_list = csv_row_list
            # self.metadata_header = pivot_df.to_csv(index=False).strip() # this line have some issue, its taking values as well along with header
            # self.metadata_list = [row.to_csv(index=False, header=False).strip() for _, row in pivot_df.iterrows()]

            logger.info(f"Found [{len(self.metadata_list)}] metadata in collection [{self.collection_id}]")

        except Exception as e:
            logger.error(f"Error occurred during filtering metadata: {str(e)}", exc_info=True)
            raise f'Error in filter_metadata_by_NER: {str(e)}'

    def find_user(self):
        try:
            logger.info(f"Finding user by user id [{self.user_id}]")
            self.user = db_helper.find_one(queries.FIND_USER_BY_USER_ID,
                                           self.user_id)
        except Exception as e:
            logger.error(f"Error occurred during finding user, Error: [{str(e)}]")

    def find_collection(self):
        try:
            logger.info(f"Finding collection by collection id [{self.collection_id}]")
            self.collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_COLLECTION_ID,
                                                 self.collection_id)
            self.collection_name = self.collection.get('collection_name')
            self.collection_custom_instruction = self.collection.get('custom_instructions')
        except Exception as e:
            logger.error(f"Error occurred during finding collection, Error: [{str(e)}]")

    def metadata_search(self, update_faq=False):
        try:
            # Send progress event and 0% progress output
            yield self.generate_single_message(event=StreamEvent.PROGRESS_EVENT, payload=dict(message=f'<p>{config.DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_1}...</p>'))
            yield self.generate_single_message(event=StreamEvent.PROGRESS_OUTPUT, payload=dict(progress_percentage=1))

            # Check if the query contains a noun, if it does, proceed with NER filtering else proceed with normal metadata search
            if self.contains_noun():
                self.filter_metadata_by_NER()
            else:
                self.find_metadata_csv()

            if len(self.metadata_list) == 0:
                self.final_message = "The Collection hasn't been setup by the Data Admin yet. Please contact Data Admin with the Collection name."
                yield self.generate_single_message(payload=dict(message=self.final_message, thread_id=self.thread_id))
                return

            # Start the async cumulative search operation
            logger.info("Starting metasearch async operation")
            async_generator = self.async_cumulative_search()

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                while True:
                    try:
                        response = loop.run_until_complete(async_generator.__anext__())
                        logger.info(f"Cumulative loop response : ", response)

                        if response.get('event') == StreamEvent.PROGRESS_OUTPUT:
                            yield self.generate_single_message(event=StreamEvent.PROGRESS_OUTPUT,
                                                               payload=dict(progress_percentage=response.get('payload')))
                        elif response.get('event') == StreamEvent.PROGRESS_EVENT:
                            yield self.generate_single_message(event=StreamEvent.PROGRESS_EVENT,
                                                               payload=dict(message=response.get('payload')))
                        elif response.get('event') == StreamEvent.FINAL_OUTPUT:
                            if update_faq:
                                db_helper.execute(queries.UPDATE_DOCCHAT_FAQ_ANSWER, response.get('payload'), self.faq_item.get('faq_id'))
                                yield self.generate_single_message(payload=dict(message=response.get('payload')))
                            else:
                                logger.info(f"Sending final response for cumulative merge")
                                if self.final_message == "":
                                    self.final_message = "No relevant information found in the collection."
                                yield self.generate_single_message(event=StreamEvent.FINAL_OUTPUT, payload=dict(message=response.get('payload')))

                    except StopAsyncIteration:
                        break
            finally:
                loop.close()
        except Exception as e:
            logger.error(f"Error occurred during metadata search: {str(e)}", exc_info=True)
            self.final_message = "An error occurred while processing your request. Please try again later."
            yield self.generate_single_message(payload=dict(message=self.final_message, thread_id=self.thread_id))

    async def async_cumulative_search(self):
        try:
            async def task_wrapper(index):
                start_index = index
                end_index = min(index + self.metadata_batch_size, len(self.metadata_list))
                logger.info(
                    f"Chunk range [{str(start_index)}-{str(end_index)}], current results size [{str(len(results))}]")
                chunks = self.metadata_list[start_index:end_index]
                concatenated_metadata = f'{self.metadata_header}\n'
                concatenated_metadata += '\n'.join(chunks)
                await self.perform_task(concatenated_metadata, results)

            async def perform_cumulative_merge():
                cumulative_merge_prompt = self.get_prompt(Prompts.CUMULATIVE_MERGE)
                cumulative_merge_prompt += f"\nCUSTOM INSTRUCTION:\n{self.collection_custom_instruction}"
                cumulative_merge_user_content = f"\nUSER QUERY:\n{self.user_query}"

                # Parse the results_json string into a list of JSON objects
                results_list = json.loads(results_json)
                logger.info(f"Results list: {results_list}")

                results_with_tokens = [
                    {"result": result, "tokens": self.get_tokens(result)}
                    for result in results_list
                ]

                chunks = []
                current_chunk = []
                current_chunk_tokens = 0
                allowed_tokens_for_chunk = config.ALLOWED_TOKENS_FOR_CHUNK

                for item in sorted(results_with_tokens, key=lambda x: x["tokens"], reverse=True):
                    if current_chunk_tokens + item["tokens"] <= allowed_tokens_for_chunk:
                        current_chunk.append(item["result"])
                        current_chunk_tokens += item["tokens"]
                    else:
                        if current_chunk:
                            chunks.append(current_chunk)
                        current_chunk = [item["result"]]
                        current_chunk_tokens = item["tokens"]

                if current_chunk:
                    chunks.append(current_chunk)

                logger.info(f"Created {len(chunks)} chunks")

                final_result = ""
                logger.info(f"Processing {len(chunks)} chunks for cumulative merge")
                for i, chunk in enumerate(chunks):
                    logger.info(f"Processing chunk {i+1} of {len(chunks)}")
                    logger.info(f"Current chunk: {chunk}, tokens: {self.get_tokens(json.dumps(chunk))}")
                    if i == 0:
                        cumulative_merge_user_content += f"\nCUMULATIVE RESULT:\nNEXT RESULT:\n{chunk}"
                    else:
                        cumulative_merge_user_content = f"\nUSER QUERY:\n{self.user_query}"
                        cumulative_merge_user_content += f"\nCUMULATIVE RESULT:\n{final_result}"
                        cumulative_merge_user_content += f"\nNEXT RESULT:\n{chunk}"

                    openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_03, async_client=True)
                    cumulative_merge_response = await openai_helper.callai_async(
                        cumulative_merge_prompt,
                        cumulative_merge_user_content,
                        self.user_id or "admin",
                        extra_context=self.previous_chat_context
                    )
                    logger.info(f"Cumulative merge response received for chunk {i+1}: {cumulative_merge_response}")
                    final_result = cumulative_merge_response
                    yield int((i + 1) / len(chunks) * 100)

                self.final_message = final_result
                merge_complete.set()

            async def perform_merge():
                cumulative_merge_prompt = self.get_prompt(Prompts.SINGLE_MERGE)
                cumulative_merge_prompt += f"\nCUSTOM INSTRUCTION:\n{self.collection_custom_instruction}"
                cumulative_merge_user_content = f"\nUSER QUERY:\n{self.user_query}"
                cumulative_merge_user_content += f"\nSEPARATE RESULTS:\n{results_json}"

                openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_09, async_client=True)
                cumulative_merge_response = await openai_helper.callai_async(
                    cumulative_merge_prompt,
                    cumulative_merge_user_content,
                    self.user_id or "admin",
                    extra_context=self.previous_chat_context
                )
                logger.info(f"Cumulative merge response received: {cumulative_merge_response}")
                self.final_message = cumulative_merge_response
                merge_complete.set()


            ############################################################
            ############################################################

            results = []
            tasks = [task_wrapper(index) for index in range(0, len(self.metadata_list), self.metadata_batch_size)]

            logger.info(f"Sending async tasks to task queue. Total tasks [{len(tasks)}]")

            completed_tasks = 1
            for task in asyncio.as_completed(tasks):
                progress = int((completed_tasks / len(tasks)) * 100)
                completed_tasks += 1
                yield {'event': StreamEvent.PROGRESS_OUTPUT, 'payload': progress}
                await task

            logger.info(f"All async cumulative tasks are completed! Now doing cumulative merge.")
            yield {'event': StreamEvent.PROGRESS_EVENT,
                   'payload': f'<p>{config.DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_1} [COMPLETED]</p> <p>{config.DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_2}...</p>'} # Send progress event
            yield {'event': StreamEvent.PROGRESS_OUTPUT, 'payload': 1}

            merge_complete = asyncio.Event()

            max_allowed_tokens = config.MAX_ALLOWED_TOKENS
            results_json = json.dumps(results)
            logger.info(f"Results json: {results_json}, type: {type(results_json)}")

            # Find the number of tokens in the results_json
            no_of_tokens = self.get_tokens(results_json)
            logger.info(f"Number of tokens in results_json: {no_of_tokens}, max_allowed_tokens: {max_allowed_tokens}")

            if no_of_tokens > max_allowed_tokens:  # if the results_json is too large, we need to perform a cumulative merge
                logger.info(f"Performing cumulative merge as no_of_tokens [{no_of_tokens}] is greater than max_allowed_tokens [{max_allowed_tokens}]")
                merge_generator = perform_cumulative_merge()
                async for progress in merge_generator:
                    yield {'event': StreamEvent.PROGRESS_OUTPUT, 'payload': progress}
            else:
                logger.info(f"Performing single merge as no_of_tokens [{no_of_tokens}] is less than max_allowed_tokens [{max_allowed_tokens}]")
                asyncio.create_task(perform_merge())
                progress = 0
                while not merge_complete.is_set() and progress < 100:
                    yield {'event': StreamEvent.PROGRESS_OUTPUT, 'payload': progress}
                    await asyncio.sleep(config.SINGLE_MERGE_DURATION / 100)
                    progress += 1
                yield {'event': StreamEvent.PROGRESS_OUTPUT, 'payload': 100}

            await merge_complete.wait()
        except LLMCallException as e: # LLMCallException is a custom exception that is raised when the LLM call fails
            self.final_message = e.message
        except Exception as e:
            logger.error(str(e))
            self.final_message = "An error occurred while processing your request. Please try again later."
        finally:
            yield {'event': StreamEvent.FINAL_OUTPUT, 'payload': self.final_message}

    def cumulative_search(self):
        try:
            results = []

            logger.info(
                f"Starting cumulative search with chunk size of [{self.metadata_batch_size}] of total items [{len(self.metadata_list)}]")
            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_06)
            for i in range(0, len(self.metadata_list), self.metadata_batch_size):
                start_index = i
                end_index = i + self.metadata_batch_size
                logger.info(
                    f"Chunk range [{str(start_index)}-{str(end_index)}], current results size [{str(len(results))}]")
                chunks = self.metadata_list[start_index:end_index]
                concatenated_metadata = f'{self.metadata_header}\n'
                concatenated_metadata += '\n'.join(chunks)
                # concatenated_metadata = json.dumps(chunks)
                cumulative_prompt = self.get_prompt(Prompts.CUMULATIVE_PROMPT)
                cumulative_prompt += f"\nCUSTOM_INSTRUCTION:\n{self.collection_custom_instruction}"

                cumulative_user_content = f"\nUSER_QUERY:\n{self.user_query}"
                cumulative_user_content += f"\nCONTEXT:\n{concatenated_metadata}"

                cumulative_response = openai_helper.callai(cumulative_prompt, cumulative_user_content,
                                                           self.user_id or "admin",
                                                           extra_context=self.previous_chat_context)
                results.append(cumulative_response)

            cumulative_merge_prompt = self.get_prompt(Prompts.CUMULATIVE_MERGE)
            cumulative_merge_prompt += f"\nCUSTOM_INSTRUCTION:\n{self.collection_custom_instruction}"
            cumulative_merge_user_content = f"\nUSER_QUERY:\n{self.user_query}"
            cumulative_merge_user_content += f"\nCUMULATED_RESULT:\n{json.dumps(results)}"

            logger.info(f"Finding final response for cumulative search")
            cumulative_merge_response = openai_helper.callai_json(cumulative_merge_prompt,
                                                                  cumulative_merge_user_content,
                                                                  self.user_id or "admin",
                                                                  extra_context=self.previous_chat_context)
            cumulative_merge_response = json.loads(cumulative_merge_response)
            self.final_message = cumulative_merge_response.get('result', '')
            logger.info(f"Cumulative search completed with final response [{self.final_message}]")
            return self.final_message
        except Exception as e:
            logger.error(str(e))
            raise e

    async def perform_task(self, context, results):
        try:
            logger.info(f"Performing single task in cumulative async function")

            cumulative_prompt = self.get_prompt(Prompts.CUMULATIVE_PROMPT)
            cumulative_prompt += f"\nCUSTOM INSTRUCTION:\n{self.collection_custom_instruction}"
            cumulative_user_content = f"\nUSER QUERY:\n{self.user_query}"
            cumulative_user_content += f"\nCONTEXT:\n{context}"

            openai_client = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_02, async_client=True)
            cumulative_response = await openai_client.callai_async(cumulative_prompt, cumulative_user_content,
                                                                   self.user_id or "admin",
                                                                   extra_context=self.previous_chat_context)
            results.append(cumulative_response)
            return cumulative_response
        except Exception as e:
            logger.error(str(e))

    def initiate_docchat(self):
        try:
            self.find_prompts()
            self.find_chat_thread()
            if not self.chat_thread.get('title'):
                self.generate_title()
            self.add_user_chat_history()
            self.faq_search()
            if self.final_message:
                self.add_assistant_chat_history(extra_payload=dict(search_type=DocChatSearchType.FAQ_SEARCH))
                return self.generate_single_message(payload=dict(message=self.final_message,
                                                                 faq_id=self.faq_item.get('faq_id'),
                                                                 thread_id=self.thread_id))
            self.find_collection()
            self.fetch_previous_chat_history()
            return self.metadata_search()
        except Exception as e:
            logger.error(f"Error occurred during docchat initiating, Error: [{str(e)}]")
            self.final_message = "An error occurred while processing your request. Please try again later."
            return self.generate_single_message(payload=dict(message=self.final_message, thread_id=self.thread_id))


    def faq_search(self):
        try:
            logger.info(f'Getting FAQ informations')
            docchat_faqs = db_helper.find_many(queries.FIND_DOCCHAT_FAQ_BY_ORGANIZATION_ID_AND_COLLECTION_ID,
                                               self.organization_id, self.collection_id)
            logger.info(f'Found [{len(docchat_faqs)}] FAQ entries for this collection')
            faq_context = [
                dict(faq_id=faq.get('faq_id'), faq_question=faq.get('faq_question'))
                for
                faq in docchat_faqs]
            faq_context = json.dumps(faq_context)
            faq_prompt = self.get_prompt(Prompts.FAQ_INSTRUCTION)
            faq_system_content = faq_prompt + '\nContext: \n' + faq_context

            logger.info(f'Searching for FAQ match')

            openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DOC_CHAT_04)
            faq_response = openai_helper.callai_json(faq_system_content, self.user_query, self.user_id)
            faq_response = json.loads(faq_response)

            if faq_response.get('faq_id') != 0:
                logger.info(f'Found FAQ match for faq_id [{faq_response.get("faq_id")}]')
                self.faq_item = [faq for faq in docchat_faqs if faq.get('faq_id') == faq_response.get('faq_id')][0]
                docchat_faq_content = self.faq_item.get('faq_answer')
                self.final_message = docchat_faq_content
                return self.final_message
        except Exception as e:
            logger.error(f"Error occurred during FAQ search, Error: [{str(e)}]")

    def find_chat_thread(self):
        try:
            logger.info(f"Finding chat thread for thread id [{self.thread_id}]")
            self.chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(self.thread_id, self.user_id)
        except Exception as e:
            logger.error(f"Error occurred during finding chat thread, Error: [{str(e)}]")

    def fetch_previous_chat_history(self, history_count=7):
        try:
            # fetching last n chats
            if self.thread_id:
                chat_thread = chats_helper.get_chat_history_by_thread_id_and_user_id(self.thread_id, self.user_id)
                chat_history = chat_thread.get('messages')
                filtered_chat_history = list(filter(lambda chat: chat.get('role') != 'action', chat_history))
                self.previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                              filtered_chat_history[-history_count:] if len(filtered_chat_history) > 1]
        except Exception as e:
            logger.error(e)
            raise e

    def add_user_chat_history(self, extra_payload=None):
        try:
            # adding user chat history
            user_chat_payload = dict(role='user', content=self.user_query)
            if extra_payload:
                user_chat_payload.update(extra_payload)
            chats_helper.add_chat_history(self.thread_id, user_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def add_assistant_chat_history(self, extra_payload=None):
        try:
            logger.info('Adding assistant chat history')
            # adding assistant chat history
            assistant_chat_payload = dict(role='assistant', content=self.final_message)
            if extra_payload:
                assistant_chat_payload.update(extra_payload)
            chats_helper.add_chat_history(self.thread_id, assistant_chat_payload)
        except Exception as e:
            logger.error(e)
            raise e

    def generate_single_message(self, event=StreamEvent.FINAL_OUTPUT, payload=None):
        try:
            logger.info(f"Generating docchat single message with event [{event}] -- payload: {payload}")
            final_message = dict()
            final_message.update(payload)
            final_message.update(self.final_message_extra_metadata)
            final_message = json.dumps(final_message)
            return f"event: {event}\ndata: {final_message}\n\n"
        except Exception as e:
            logger.error(e)
            final_message = dict(
                message="Sorry, I am having some trouble to respond at the moment. Please try again later!",
                thread_id=self.thread_id)
            final_message = json.dumps(final_message)
            return f"event: {event}\ndata: {final_message}\n\n"

    def get_prompt(self, prompt_type):
        try:
            prompt = next(
                (prompt for prompt in self.docchat_prompts if prompt.get('prompt_name') == prompt_type))
            return prompt.get('prompt_text')
        except Exception as e:
            logger.error(f"Error occurred during getting prompt from docchat prompts, Error: [{str(e)}]")

    def generate_title(self):
        try:
            generate_title_prompt = self.get_prompt(Prompts.GENERATE_TITLE)
            openai_client = OpenAIHelper(portkey_config="pc-03docc-e74f4b")
            title = openai_client.callai(generate_title_prompt, self.user_query, self.user_id)
            payload = dict(title=title)
            chats_helper.update_thread(self.thread_id, payload)
            return title
        except Exception as e:
            logger.error(f"Error occurred during getting prompt from docchat prompts, Error: [{str(e)}]")

    def contains_noun(self) -> bool:
        try:
            logger.info(f"Checking for nouns in query: '{self.user_query}'")

            noun_check_prompt = self.get_prompt(Prompts.NOUN_CHECK)
            system_content = f'{noun_check_prompt}\n\n{StaticPrompts.NOUN_CHECK_RETURN_FORMAT}'
            user_content = f"Identify nouns in this query: '{self.user_query}'"

            openai_helper = OpenAIHelper(PortKeyConfigs.DOC_CHAT_08)
            response = openai_helper.callai_json(
                system_content=system_content,
                user_content=user_content,
                user_id=self.user_id or "admin"
            )
            logger.debug(f"AI response received: {response}")
            response = json.loads(response)
            response = response.get('nouns', "")

            logger.info(f"Nouns found: '{response}', String length: {len(response)}")
            return False if len(response) == 0 else True
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            return False

    def get_tokens(self, text : str) -> int:
        enc = tiktoken.get_encoding("o200k_base")
        return len(enc.encode(text))
