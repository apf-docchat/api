import os

# Main DB (MySQL)
DATABASE_URI = os.getenv('DATABASE_URI')

# NoSQL DB (MongoDB)
MONGO_URI = os.getenv('MONGO_URI')

FRONTEND_URL = os.getenv('FRONTEND_URL')

# Uploads dir
ORGDIR_PATH = os.getenv('UPLOADS_BASE_DIR', os.path.join(os.getcwd(), 'data'))
ORGDIR_SUB_PATH = ''
ORGFILES_BASE_DIR = os.getenv('ORG_TEMP_BASE_DIR', os.path.join(os.getcwd(), 'data', 'tempfiles'))

# OpenAI Keys (record the account in .env file for reference)
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
OPENAI_ORG = os.getenv('OPENAI_ORGANIZATION')

# Pinecone Keys (record the account in .env file for reference)
PINECONE_API_KEY = os.getenv('PINECONE_API_KEY')
PINECONE_INDEX_NAME = os.getenv('PINECONE_INDEX_NAME')
PINECONE_ENVIRONMENT = os.getenv('PINECONE_ENVIRONMENT')

# Internal Communication
INTERNAL_API_KEY = os.getenv('INTERNAL_API_KEY')

VECTORIZER_QUEUE_URI = os.getenv('VECTORIZER_QUEUE_URI')

# Pinecone Viewer Token
PINECONE_VIEWER_TOKEN = os.getenv('PINECONE_VIEWER_TOKEN')

# Allowed auth methods
AUTH_METHODS_ALLOWED = ['ms365', 'username-pwd']

# Microsoft 365 Auth
MSAUTH_CLIENT_ID = os.getenv('MSAUTH_CLIENT_ID')
MSAUTH_CLIENT_SECRET = os.getenv('MSAUTH_CLIENT_SECRET')
MSAUTH_REDIRECT_URI = os.getenv('MSAUTH_REDIRECT_URI')
MSAUTH_AUTHORITY = os.getenv('MSAUTH_AUTHORITY')

# Max tokens for OpenAI (Assuming gpt4-turbo. Max tokens is used for Summarize files token size)
MAX_TOKENS = 200000

EMBEDDING_BASE_URL = os.getenv('EMBEDDING_BASE_URL')
EMBEDDING_MODEL = os.getenv('EMBEDDING_MODEL')
LLM_BASE_URL = os.getenv('LLM_BASE_URL')
LLM_API_KEY = os.getenv('LLM_API_KEY')
LLM_MODEL = os.getenv('LLM_MODEL')

JWT_SECRET = os.getenv('JWT_SECRET')
JWT_ISS = os.getenv('JWT_ISS')
STATIC_FILES_PREFIX = f"{os.getenv('STATIC_FILES_HOST')}/static-files"

PORTKEY_API_KEY = os.getenv('PORTKEY_API_KEY')
USE_DEFAULT_PORTKEY = os.getenv('USE_DEFAULT_PORTKEY', 'False')
USE_PORTKEY = os.getenv('USE_PORTKEY', 'True')

METASEARCH_BATCH_SIZE = int(os.getenv('METASEARCH_BATCH_SIZE', 3))
METASEARCH_NER_FILTER_BATCH_SIZE = int(os.getenv('METASEARCH_NER_FILTER_BATCH_SIZE', 100))
CALLAI_STREAMING_TEMPERATURE = float(os.getenv('CALLAI_STREAMING_TEMPERATURE', 0))
CALLAI_TEMPERATURE = float(os.getenv('CALLAI_TEMPERATURE', 0))
CALLAI_JSON_TEMPERATURE = float(os.getenv('CALLAI_JSON_TEMPERATURE', 0))
CALLAI_ASYNC_TEMPERATURE = float(os.getenv('CALLAI_ASYNC_TEMPERATURE', 0.4))
MAX_ALLOWED_TOKENS = int(os.getenv('MAX_ALLOWED_TOKENS', 1000))
ALLOWED_TOKENS_FOR_CHUNK = int(os.getenv('ALLOWED_TOKENS_FOR_CHUNK', 1000))
SINGLE_MERGE_DURATION = int(os.getenv('SINGLE_MERGE_DURATION', 10))

DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_1 = os.getenv('DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_1',
                                                            'Processing files')
DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_2 = os.getenv('DOCCHAT_METDATA_SEARCH_PROGRESS_EVENT_MESSAGE_2',
                                                            'Finding relevant information')

DOCANALYSIS_MAX_CHAR_COUNT = int(os.getenv('DOCANALYSIS_MAX_CHAR_COUNT', 80000))
DOCANALYSIS_TEMP_FILE_PATH = os.getenv('DOCANALYSIS_TEMP_FILE_PATH', 'docanalysis/temp')

WHATSAPP_VERIFY_TOKEN = os.getenv('WHATSAPP_VERIFY_TOKEN')
WHATSAPP_REPLY_URL = os.getenv('WHATSAPP_REPLY_URL')
WHATSAPP_ACCESS_TOKEN = os.getenv('WHATSAPP_ACCESS_TOKEN')

STATIC_FILES_HOST = os.getenv('STATIC_FILES_HOST')
