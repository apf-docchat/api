import json, os
import logging

from flask import request
from openai import OpenAI

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import Prompts, StreamEvent
from source.api.utilities.externalapi_helpers import chats_helper
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.api.utilities.vector_search import VectorSearch
from source.common import config
from pinecone import Pinecone, ServerlessSpec

from rank_bm25 import BM25Okapi
from collections import Counter
import fitz

import nltk
from nltk.tokenize import word_tokenize
from nltk.corpus import stopwords


logger = logging.getLogger('app')

def askdoc_query():
    try:
        if 'organization_id' not in request.context:
            logger.error("Organization ID is missing in request context")
            raise RuntimeError('Organization ID is required!')

        logger.info("Fetching query data from request")
        organization_id = request.context['organization_id']
        orgname = request.context['organization_name']
        user_id = request.context['user_id']
        query = request.json.get('user_query')
        collection_id = request.json.get('collection_id')
        thread_id = request.json.get('thread_id')

        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=organization_id, module='ASK_DOC')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']

        manager = AskDocManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.query = query
        manager.collection_id = collection_id
        manager.thread_id = thread_id

        return manager.init_askdoc_query()
    except Exception as e:
        logger.error(f'Error in ask_doc_query: {str(e)}')
        raise e

class AskDocManager:
    def __init__(self):
        logger.info("Initializing AskDocManager")
        self.openai_helper = OpenAIHelper()
        self.vector_search = None

        self.organization_id = None
        self.orgname = None
        self.user_id = None
        self.query = None
        self.collection_id = None
        self.file_ids = []
        self.file_name = {}
        self.file_path = {}
        self.collection = None
        self.collection_name = None
        self.user = None
        self.username = None
        self.prompts = None
        self.custom_instructions = None
        self.system_content = None
        self.thread_id = None
        self.final_message = None
        self.previous_chat_context = None
        self.final_message_extra_metadata = {}
        logger.info("AskDocManager initialized")

    def init_askdoc_query(self):
        self.fetch_query_data()
        self.prepare_context()
        self.fetch_previous_chat_history()
        self.add_user_chat_history()
        return self.generate_response()

    def fetch_query_data(self):
        self.collection = self.get_collection()
        self.get_file()
        for file_id in self.file_ids:
            self.file_path[file_id] = os.path.join(config.ORGDIR_PATH, self.orgname, config.ORGDIR_SUB_PATH, self.file_name[file_id])
        #self.file_path = [os.path.join(config.ORGDIR_PATH, self.orgname, config.ORGDIR_SUB_PATH, fname) for fname in self.file_name]
        self.user = self.get_user()
        self.prompts = db_helper.find_one(queries.FIND_PROMPT_BY_PROMPT_TYPE_AND_PROMPT_NAME, 'docchat', Prompts.RESPOND_TO_SEARCH_USER_QUERY)
        self.custom_instructions = self.get_custom_instructions()

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
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_COLLECTION_ID, self.collection_id)
        if not files:
            logger.error(f"File not found for collection ID: {self.collection_id}")
            raise RuntimeError('File not found!')

        # Initialize lists to store file IDs and file names
        self.file_ids = []
        self.file_name = {}
        # Loop through all retrieved files and populate the lists
        for file in files:
            self.file_ids.append(file.get('file_id'))
            self.file_name[file.get('file_id')] = file.get('file_name')
        logger.info(f"Files found: {self.file_ids}")
        return files

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

    def load_bm25_parameters_for_files(self):
        # Retrieve IDF values for the specified file
        #idf_data = db_helper.find_many(queries.FIND_BM25_TERMS_FOR_FILE, self.file_id)
        idf_data = {}

        # Loop through each file_id in self.file_ids and retrieve corresponding data
        for file_id in self.file_ids:
            file_idf_data = db_helper.find_many(queries.FIND_BM25_TERMS_FOR_FILE, file_id)

            idf_data[file_id] = file_idf_data if file_idf_data else []


        #print(f"Raw IDF data: {idf_data}")
        #idf_values = {entry['term']: entry['idf'] for entry in idf_data}
        idf_values = {}
        # Populate idf_values with each file_id's terms and their corresponding idf values
        for file_id, entries in idf_data.items():
            idf_values[file_id] = {entry['term']: entry['idf'] for entry in entries}
        #print(f"First 5 IDF values: {list(idf_values.items())[:5]}")

        # Retrieve average document length
        avg_doc_len = {}
        for file_id in self.file_ids:
            avg_doc_len[file_id] = db_helper.find_one(queries.FIND_BM25_AVG_DOC_LENGTH, file_id)
            avg_doc_len[file_id] = avg_doc_len[file_id]['avg_doc_len']
        #print(f"Average document length: {avg_doc_len}")

        return idf_values, avg_doc_len

    def load_pages_for_files(self):
        pages_data = {}
        preprocessed_pages = {}
        for file_id in self.file_ids:
            pages_data[file_id] = db_helper.find_many(queries.FIND_BM25_TOKENS, file_id)
            #print(f"Pages data: {pages_data}")
            preprocessed_pages[file_id] = []
            for page in pages_data[file_id]:
                tokens = page.get("tokens")
                #print(f"Tokens: {tokens}")

                if tokens:  # Only load if the string is not empty
                    try:
                        preprocessed_pages[file_id].append(json.loads(tokens))
                    except json.JSONDecodeError as e:
                        print(f"Error decoding JSON: {e}, Tokens: {tokens}")
                else:
                    print("Empty tokens found")

        print(f"Preprocessed pages count: {len(preprocessed_pages)}")

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
        idf_values, avg_doc_len = self.load_bm25_parameters_for_files()
        #print(f"Avg doc length: {avg_doc_len}")
        preprocessed_pages, _ = self.load_pages_for_files()
        #print(f"First preprocessed page: {preprocessed_pages[self.file_ids[0]]}")

        bm25 = {}
        print("Initializing BM25 for files")
        for file_id in self.file_ids:
            bm25[file_id] = BM25Okapi(preprocessed_pages[file_id])
            bm25[file_id].idf = idf_values[file_id]
            bm25[file_id].avgdl = avg_doc_len[file_id]
        print(f"BM25 initialized for file: {file_id}")
        return bm25, preprocessed_pages

    def preprocess_text(self, text):
        stop_words = set(stopwords.words("english"))
        tokens = word_tokenize(text.lower())
        tokens = [token for token in tokens if token.isalnum() and token not in stop_words]
        #print(f"Number of Preprocessed tokens: {len(tokens)}")
        return tokens

    def query_bm25_for_file(self, top_n=5):
        bm25, preprocessed_pages = self.initialize_bm25_for_files()
        preprocessed_query = self.preprocess_text(self.query)
        scores = {}
        for file_id in self.file_ids:
            scores[file_id] = bm25[file_id].get_scores(preprocessed_query)
            #scores = self.calculate_bm25_scores(preprocessed_pages, bm25.idf, bm25.avgdl)
            print(f"Scores for file_id {file_id}: {scores[file_id]}")

        # Load page text to show in results
        _, pages_data = self.load_pages_for_files()
        #print(f"First page data: {pages_data[0]}")

        """ # Get top relevant pages
        top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:top_n]
        #print(f"Top indices: {top_indices}")
        #top_pages = [(pages_data[i][0], scores[i]) for i in top_indices]  # page_number, score
        top_pages = [(pages_data[i]['page_number'], scores[i]) for i in top_indices] """

        top_pages = []
        top_n = int(os.getenv('ASKDOC_CONTEXT_NUM_PAGES', 10))

        # Collect all scores with corresponding file_id, page number, and score
        for file_id, scores_list in scores.items():
            for page_num, score in enumerate(scores_list):
                top_pages.append({'file_id': file_id, 'page_num': pages_data[file_id][page_num]['page_number'], 'score': score})

        # Sort the top_pages list by score in descending order and select the top_n entries
        top_pages = sorted(top_pages, key=lambda x: x['score'], reverse=True)[:top_n]

        #print(f"First top page entry: {top_pages[0]}")
        return top_pages

    def get_text_for_pagenum(self, file_id, page_number):
        doc = fitz.open(self.file_path[file_id])
        page = doc.load_page(page_number)
        text = page.get_text()
        return text

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
        print(f"Top pages: {top_pages}")

        # Insert vector retrieved chunks instead of zer-scoring pages. If no zero-scoring pages, insert the first 6 pages and rest can be vector chunks
        index_of_zero = next((index for index, item in enumerate(top_pages) if item['score'] == 0), len(top_pages))
        min_bm25_pages = int(float(os.getenv('ASKDOC_PERCENTAGE_OF_BM25_PAGES', 0.6)) * len(top_pages))
        vector_chunk_start_index = min(index_of_zero, min_bm25_pages)
        #print(f"Index of zero: {index_of_zero}, Min BM25 pages: {min_bm25_pages}, Vector chunk start index: {vector_chunk_start_index}")


        # Use the top_pages to open pdf file in path self.file_path and load the page content into context prompt
        bm25_context_prompt = ''
        i = 0
        for page in top_pages:
            file_id = page['file_id']
            page_number = page['page_num']
            score = page['score']

            print(f"Retrieving text for page: {page_number} in file: {file_id}")
            potential_prompt = bm25_context_prompt + self.get_text_for_pagenum(file_id, page_number)
            if len(potential_prompt) < context_prompt_max_char_count and i < vector_chunk_start_index:
                bm25_context_prompt = potential_prompt
            i += 1
        print(f"Context prompt length: {len(bm25_context_prompt)}")

        context_prompt_max_char_count_remaining = context_prompt_max_char_count-len(bm25_context_prompt)

        if (context_prompt_max_char_count_remaining > 0):
            # now fill the rest of the context prompt with vector chunks
            metadata_json = []
            MODEL = config.EMBEDDING_MODEL
            from pinecone import Pinecone
            from pinecone import ServerlessSpec

            pc = Pinecone(api_key=config.PINECONE_API_KEY)

            print(pc.list_indexes().names())

            # check if index already exists (only create index if not)
            if config.PINECONE_INDEX_NAME not in pc.list_indexes().names():
                pc.create_index(config.PINECONE_INDEX_NAME, dimension=1536, spec=ServerlessSpec(
                    cloud="aws",
                    region="us-east-1"
                ),) #old - len(embeds[0])

            # connect to index and get query embeddings
            pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
            # index = pinecone.Index(config.pinecone_index_name)
            xq = client.embeddings.create(input=self.query, model=MODEL).data[0].embedding

            topk = int(os.getenv('ASKDOC_CONTEXT_PROMPT_TOPK', 40))
            search_filter = {
                'orgname': {'$eq': self.orgname},
                'collection': {'$in': [self.collection_name]}
            }
            res = pinecone_index.query(vector=[xq], filter=search_filter, top_k=topk, include_metadata=True)

            logger.info('\n\nPINECOONE_INDEX_QUERY: ' + str(res) + '\n\n')
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
                            logger.info('\n\nMETADATA_JSON: ' + str(metadata_json) + '\n\n')
                            vector_context_prompt += json.dumps(metadata)
                        else:
                            break

        context_prompt = bm25_context_prompt + vector_context_prompt

        self.system_content = (
            f"{self.prompts['prompt_text']}\n"
            f"{self.custom_instructions['custom_instructions']}\n"
            f"Context:\n{context_prompt}"
        )
        logger.info('\n\nSYSTEM_CONTENT: ' + str(self.system_content) + '\n\n')
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

    def generate_response(self):
        logger.info("Generating response using OpenAI")
        try:
            streamed_data = self.openai_helper.callai_streaming(
                system_content=self.system_content,
                user_content=self.query,
                user_id=self.user_id,
                extra_context=self.previous_chat_context
            )

            for event, message in streamed_data:
                if event == 'CHUNK':
                    message = message.replace('\n', '<br>')
                    yield f"data: {message}\n\n"
                if event == 'FINAL_MESSAGE':
                    self.add_assistant_chat_history(message=message)
                    final_message = dict(message=message, thread_id=self.thread_id)
                    final_message = json.dumps(final_message)
                    yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"

        except Exception as e:
            logger.error(f"Error in generate_response: {e}")
            final_message = json.dumps({
                "message": "Sorry, I am having some trouble to respond at the moment. Please try again later!",
                "thread_id": self.thread_id
            })
            yield f"event: {StreamEvent.FINAL_OUTPUT}\ndata: {final_message}\n\n"

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
                logger.info(f'Chat thread: {chat_thread}')
                if not chat_thread:
                    logger.error('Chat thread not found')
                    return
                chat_history = chat_thread.get('messages')
                filtered_chat_history = list(filter(lambda chat: chat.get('role') != 'action', chat_history))
                self.previous_chat_context = [dict(role=chat.get('role'), content=chat.get('content')) for chat in
                                              filtered_chat_history[-history_count:] if len(filtered_chat_history) > 1]
                logger.info(f'Previous chat context: {self.previous_chat_context}')
        except Exception as e:
            logger.error(e)
            raise e
