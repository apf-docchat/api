from dataclasses import dataclass
from typing import Dict, Set


@dataclass(frozen=True)
class Prompts:
    CUMULATIVE_PROMPT = "CUMULATIVE_PROMPT"
    CUMULATIVE_PROMPT_SYNC = "CUMULATIVE_PROMPT_SYNC"
    CUMULATIVE_MERGE = "CUMULATIVE_MERGE"
    SINGLE_MERGE = "SINGLE_MERGE"
    FAQ_IMPROVE_ANSWER = "FAQ_IMPROVE_ANSWER"
    QUERY_CATEGORIZATION = "QUERY_CATEGORIZATION"
    FAQ_INSTRUCTION = "faq_instruction"
    GENERATE_TITLE = "give_title_new_chat"
    RESPOND_TO_SEARCH_USER_QUERY = "respond_to_search_user_query"
    DOCANALYSIS_CATEGORISE_QUAL_NEEDED = 'CATEGORISE_QUAL_NEEDED'
    DOCANALYSIS_CODE_GEN_FILTERING = 'CODE_GEN_FILTERING'
    DOCANALYSIS_CODE_GEN_PROCESSING_PART1 = 'CODE_GEN_PROCESSING_PART1'
    DOCANALYSIS_CODE_GEN_INPUT_FILE_CSV = 'CODE_GEN_INPUT_FILE_CSV'
    DOCANALYSIS_CODE_GEN_INPUT_FILE_XLSX = 'CODE_GEN_INPUT_FILE_XLSX'
    DOCANALYSIS_CODE_GEN_PROCESSING_CODE_SPECS = 'CODE_GEN_PROCESSING_CODE_SPECS'
    DOCANALYSIS_CODE_GEN_PROCESSING_OUTPUT_FORMATTING = 'CODE_GEN_PROCESSING_OUTPUT_FORMATTING'
    DOCANALYSIS_CODE_GEN_FUZZY_INSTRUCTIONS = 'CODE_GEN_FUZZY_INSTRUCTIONS'
    DOCANALYSIS_OUTPUT_FORMAT = 'OUTPUT_FORMAT'
    DOCANALYSIS_CODE_GEN_PROCESSING_OUTPUT_FORMATTING = 'CODE_GEN_PROCESSING_OUTPUT_FORMATTING'
    DOCANALYSIS_VALIDATE_COLUMN = 'VALIDATE_COLUMN'
    DOCANALYSIS_BEAUTIFY_ERRORS = 'BEAUTIFY_ERRORS'
    NER_FILTER = "NER_FILTER"
    NOUN_CHECK = "NOUN_CHECK_PROMPT"
    DOCANALYSIS_IMPROVE_CODE = "IMPROVE_CODE"
    DOCANALYSIS_FIND_CODE_FROM_FAQ = "FIND_CODE_FROM_FAQ"


@dataclass(frozen=True)
class SectionStage:
    INITIAL_CHAT = "INITIAL_CHAT"
    CONVERSATION = "CONVERSATION"
    TIMED_OUT = "TIMED_OUT"
    COMPLETED = "COMPLETED"
    CONTINUE_SECTION = "CONTINUE_SECTION"
    ASSESS_ME = "ASSESS_ME"


@dataclass(frozen=True)
class DocChatSearchType:
    FAQ_SEARCH = "FAQ_SEARCH"
    METADATA_SEARCH = "METADATA_SEARCH"


@dataclass(frozen=True)
class StreamEvent:
    FINAL_OUTPUT = "finalOutput"
    PROGRESS_EVENT = "progressEvent"
    PROGRESS_OUTPUT = "progressOutput"
    COLUMN_ERROR = "columnError"
    CHUNK = "chunk"
    
@dataclass(frozen=True)
class PortKeyConfigs:
    # DEFAULT
    DEFAULT = "pc-gpt4fi-2f6d41"
    DEFAULT_GPT4o = "pc-defaul-c22d28"
    
    # Doc Chat
    DOC_CHAT_01 = "pc-01docc-b3c28e" # DOCCHAT - Improve FAQ Async Loop
    DOC_CHAT_02 = "pc-02docc-86658d" # DOCCHAT - Docchat Query if no FAQ is found
    DOC_CHAT_03 = "pc-03docc-e74f4b" # DOCCHAT - Async Cumulative Search in Docchat if no FAQ is found
    DOC_CHAT_04 = "pc-04docc-fdeab2" # DOCCHAT - Search for FAQ match
    DOC_CHAT_05 = "pc-05docc-9ca86c" # DOCCHAT - Generate title (Docchat)
    DOC_CHAT_06 = "pc-06docc-870fbf" # DOCCHAT - Cumulative Search
    DOC_CHAT_07 = "pc-07docc-302ae0" # DOCCHAT - NER Filtering
    DOC_CHAT_08 = "pc-08docc-1683a2" # DOCCHAT - Noun Check
    DOC_CHAT_09 = "pc-09docc-3f8325" # DOCCHAT - Single Merge
    
    # Doc Guide
    DOC_GUIDE_01 = "pc-01docg-c001b7" # DOCGUIDE - Fetch Assessment Score
    DOC_GUIDE_02 = "pc-02docg-921d59" # DOCGUIDE - FAQ search
    DOC_GUIDE_03 = "pc-03docg-cb32bc" # DOCGUIDE - Get interactive Event Message
    DOC_GUIDE_04 = "pc-04docg-67cc31" # DOCGUIDE - Generate Streamed Message
    
    # File Processor
    FILE_PROCESSOR_01 = "pc-01file-02a1d7" # FILEPROCESSOR - Docchat Metadata process for all files (Metadata Update)
    FILE_PROCESSOR_02 = "pc-02file-0b0e59" # FILEPROCESSOR - Processs Docchat Metadata for schema 
    FILE_PROCESSOR_03 = "pc-03file-0d5e3f" # FILEPROCESSOR - Summarize File Processor
    FILE_PROCESSOR_04 = "pc-04file-8d56cb" # FILEPROCESSOR - Fileprocessor Metadata Update
    FILE_PROCESSOR_05 = "pc-05file-aaecdd" # FILEPROCESSOR - Processs Docchat Metadata
    FILE_PROCESSOR_06 = "pc-06file-4fdd0c" # FILEPROCESSOR - Update Docchat FAQ
    FILE_PROCESSOR_07 = "pc-07file-3656b3" # FILEPROCESSOR - Generate Metadata Fields
    
    # Doc Analysis 
    DOC_ANALYSIS_01 = "pc-01doca-4811aa" # DOCANALYSIS - Query categorization
    DOC_ANALYSIS_02 = "pc-02doca-7be3f7" # DOCANALYSIS - Code Generation - OpenAI
    DOC_ANALYSIS_02_CLAUDE ="pc-02doca-f15c1f" # DOCANALYSIS - Code Generation - Claude
    DOC_ANALYSIS_03 = "pc-03doca-da5f61" # DOCANALYSIS - Format the Output
    DOC_ANALYSIS_04 = "pc-o1-pre-14ba0f" # o1 preview

    # New Chat Mod
    NEW_CHAT_01 = "pc-01newc-0f4fb0"
    NEW_CHAT_INSIGHT = "pc-new-ch-e039c4"

    #popupbot
    POPUPBOT_01 = "pc-audio-9a41aa"
    

class FileSupported:
    SUPPORTED_MODULES: Dict[str, Set[str]] = {
        'docchat': {'docx', 'pdf', 'txt', 'doc', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'},
        'dataanalysis': {'csv', 'xlsx'},
        'esgreporting': {'pdf'},
        'procurement': {'pdf'},
        'filewizard': {'pdf', 'docx', 'doc', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'},
        'docguide': {'docx', 'pdf', 'txt', 'doc', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'},
        'newsscraping': {'pdf'},
        'askdoc': {'docx', 'pdf', 'txt', 'doc', 'ppt', 'pptx', 'xls', 'xlsx', 'csv'},
        'docanalysis': {'xls', 'xlsx', 'csv'},
        'chat': {'pdf', 'xls', 'xlsx', 'csv'}
    }

    @classmethod
    def is_extension_supported(cls, module_name: str, file_extension: str) -> bool:
        """
        Check if the given file extension is supported for the specified module.

        Args:
            module_name (str): The name of the module to check.
            file_extension (str): The file extension to verify (without the dot).

        Returns:
            bool: True if the extension is supported, False otherwise.
        """
        if module_name not in cls.SUPPORTED_MODULES:
            raise ValueError(f"Unknown module: {module_name}")
        
        return file_extension.lower() in cls.SUPPORTED_MODULES[module_name]
    
@dataclass(frozen=True)
class ChatFileCategory:
    TEXT_FILES = "TEXT_FILES"
    SPREADSHEET_FILES = "SPREADSHEET_FILES"
    PREVIOUS_OUTPUT = "PREVIOUS_OUTPUT"

@dataclass(frozen=True)
class AGENT_TOOLS:
    Text_Document_Processing = "1"
    Data_Analysis = "2"
    Metadata_Generator = "3"
    Filter_Files = "4"
    Send_Email = "5"
    LLM_call = "6"
    Web_Search = "7"