from io import BytesIO
import logging
import time
from typing import List, Dict, Optional

from openai import OpenAI, AsyncOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from source.api.utilities.constants import PortKeyConfigs
from source.common import config

class OpenAIHelper:
    SYSTEM_ROLE = "system"
    USER_ROLE = "user"

    logger = logging.getLogger('app')

    def __init__(self, portkey_config: str = PortKeyConfigs.DEFAULT, async_client: bool = False, use_portkey = None, base_url=None):
        self.portkey_config = portkey_config
        if use_portkey is None:
           use_portkey = config.USE_PORTKEY
        if use_portkey == "True":
            self.logger.info(f"Initializing OpenAIHelper with portkey_config: {portkey_config}, async_client: {async_client}")
        else:
            self.logger.info(f"Initializing OpenAIHelper WITHOUT portkey, async_client: {async_client}")
        if config.USE_DEFAULT_PORTKEY == "True":
            portkey_config = PortKeyConfigs.DEFAULT
            self.logger.info("Using default PortKey configuration")

        if use_portkey == "False":
            self.logger.info("Not using PortKey")
            if base_url is None:
                base_url = config.LLM_BASE_URL

            if async_client:
                self.ai_client = AsyncOpenAI(
                    base_url=base_url,
                    default_headers=createHeaders(provider="openai", api_key=config.OPENAI_API_KEY, config=portkey_config)
                )
            else:
                self.ai_client = OpenAI(
                    base_url=base_url,
                    default_headers=createHeaders(provider="openai", api_key=config.OPENAI_API_KEY, config=portkey_config)
                )
        else:
            self.logger.info("Using PortKey")
            if base_url is None:
                base_url = PORTKEY_GATEWAY_URL

            if async_client:
                self.ai_client = AsyncOpenAI(
                    base_url=base_url,
                    default_headers=createHeaders(provider="openai", api_key=config.PORTKEY_API_KEY, config=portkey_config)
                )
            else:
                self.ai_client = OpenAI(
                    base_url=base_url,
                    default_headers=createHeaders(provider="openai", api_key=config.PORTKEY_API_KEY, config=portkey_config)
                )
        self.logger.info("OpenAIHelper initialized successfully")

    def _prepare_messages(self, system_content: str, user_content: str, extra_context: Optional[List[Dict[str, str]]] = None) -> List[Dict[str, str]]:
        self.logger.debug("Preparing messages")
        messages = [{"role": self.SYSTEM_ROLE, "content": system_content}]
        if extra_context:
            messages.extend(extra_context)
        messages.append({"role": self.USER_ROLE, "content": user_content})
        self.logger.debug(f"Prepared {len(messages)} messages")
        return messages

    def callai_streaming(self, system_content: str, user_content: str, user_id: str, extra_context: Optional[List[Dict[str, str]]] = None):
        self.logger.info(f"Starting streaming call for user {user_id}")
        try:
            messages = self._prepare_messages(system_content, user_content, extra_context)
            full_message = ''
            self.logger.debug(f"Creating stream with model: {config.LLM_MODEL}")
            stream = self.ai_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.CALLAI_STREAMING_TEMPERATURE,
                stream=True,
                user=str(user_id)
            )
            for chunk in stream:
                if chunk.choices[0].delta.content is not None:
                    part_message = chunk.choices[0].delta.content
                    full_message += part_message
                    yield "CHUNK", part_message
            self.logger.info("Streaming completed successfully")
            yield "FINAL_MESSAGE", full_message
        except Exception as e:
            self.logger.error(f"Error in callai_streaming: {e}")
            raise LLMCallException(original_exception=e)

    def callai(self, system_content: str, user_content: str, user_id: str, extra_context: Optional[List[Dict[str, str]]] = None) -> str:
        self.logger.info(f"Starting non-streaming call for user {user_id}")
        try:
            messages = self._prepare_messages(system_content, user_content, extra_context)
            self.logger.debug(f"Creating completion with model: {config.LLM_MODEL}")
            response = self.ai_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.CALLAI_TEMPERATURE,
                user=str(user_id)
            )
            if response.choices[0].message.content is None:
                raise Exception("No Response from LLM")
            self.logger.info("Non-streaming call completed successfully")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.error(f"Error in callai: {e}")
            raise LLMCallException(original_exception=e)

    def callai_json(self, system_content: str, user_content: str, user_id: str, extra_context: Optional[List[Dict[str, str]]] = None) -> str:
        self.logger.info(f"Starting JSON call for user {user_id}")
        MAX_RETRIES = 2
        for i in range(MAX_RETRIES):
            try:
                messages = self._prepare_messages(system_content, user_content, extra_context)
                self.logger.debug(f"Creating JSON completion with Portkey config: {self.portkey_config}")
                """ response = self.ai_client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    temperature=config.CALLAI_JSON_TEMPERATURE,
                    user=str(user_id),
                    response_format={'type': 'json_object'},
                    #max_tokens=8000 # Required field for Anthropic
                ) """
                #removed temperature for o3-mini
                response = self.ai_client.chat.completions.create(
                    model=config.LLM_MODEL,
                    messages=messages,
                    user=str(user_id),
                    response_format={'type': 'json_object'},
                    #max_tokens=8000, # Required field for Anthropic
                )
                if response.choices[0].message.content is None:
                    raise Exception("No Response from LLM")
                self.logger.info("JSON call completed successfully")
                response = response.choices[0].message.content
                return response
                #json_string = response.replace('\n', '\\n')
                #return json_string
            # except self.ai_client.APIError as e:
            #     if e.http_status in [500, 503]:
            #         print(f"Server error. Retrying {i + 1}/{MAX_RETRIES}...")
            #         time.sleep(2 ** i)  # Exponential backoff
            #     else:
            #         raise

            except Exception as e:
                self.logger.error(f"Error in callai_json: {e}")
                raise LLMCallException(original_exception=e)

    async def callai_async(self, system_content: str, user_content: str, user_id: str, extra_context: Optional[List[Dict[str, str]]] = None) -> str:
        self.logger.info(f"Starting async call for user {user_id}")
        try:
            messages = self._prepare_messages(system_content, user_content, extra_context)
            self.logger.debug(f"Creating async completion with model: {config.LLM_MODEL}")
            response = await self.ai_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.CALLAI_ASYNC_TEMPERATURE,
                user=str(user_id)
            )
            if response.choices[0].message.content is None:
                raise Exception("No Response from LLM")
            self.logger.info("Async call completed successfully")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.warning(f"Error with primary model, attempting fallback: {e}")
            try:
                messages = self._prepare_messages(system_content, user_content, extra_context)
                self.logger.debug("Creating async completion with fallback model: mistralai/Mixtral-8x7B-Instruct-v0.1")
                response = await self.ai_client.chat.completions.create(
                    model='mistralai/Mixtral-8x7B-Instruct-v0.1',
                    messages=messages,
                    temperature=config.CALLAI_ASYNC_TEMPERATURE,
                    user=str(user_id),
                )
                if response.choices[0].message.content is None:
                    raise Exception("No Response from LLM")
                self.logger.info("Async call completed successfully with fallback model")
                return response.choices[0].message.content
            except Exception as ee:
                self.logger.error(f"Error in callai_async (including fallback): {ee}")
                raise LLMCallException(original_exception=ee)

    async def callai_async_json(self, system_content: str, user_content: str, user_id: str, extra_context: Optional[List[Dict[str, str]]] = None) -> str:
        self.logger.info(f"Starting async call for user {user_id}")
        try:
            messages = self._prepare_messages(system_content, user_content, extra_context)
            self.logger.debug(f"Creating async completion with model: {config.LLM_MODEL}")
            response = await self.ai_client.chat.completions.create(
                model=config.LLM_MODEL,
                messages=messages,
                temperature=config.CALLAI_ASYNC_TEMPERATURE,
                user=str(user_id),
                response_format={'type': 'json_object'}
            )
            if response.choices[0].message.content is None:
                raise Exception("No Response from LLM")
            self.logger.info("Async call completed successfully")
            return response.choices[0].message.content
        except Exception as e:
            self.logger.warning(f"Error with primary model, attempting fallback: {e}")
            try:
                messages = self._prepare_messages(system_content, user_content, extra_context)
                self.logger.debug("Creating async completion with fallback model: mistralai/Mixtral-8x7B-Instruct-v0.1")
                response = await self.ai_client.chat.completions.create(
                    model='mistralai/Mixtral-8x7B-Instruct-v0.1',
                    messages=messages,
                    temperature=config.CALLAI_ASYNC_TEMPERATURE,
                    user=str(user_id),
                    response_format={'type': 'json_object'}
                )
                if response.choices[0].message.content is None:
                    raise Exception("No Response from LLM")
                self.logger.info("Async call completed successfully with fallback model")
                return response.choices[0].message.content
            except Exception as ee:
                self.logger.error(f"Error in callai_async (including fallback): {ee}")
                raise LLMCallException(original_exception=ee)

    def callai_voice(self, audio_file, user_id: str) -> str:
        """
        Transcribes voice audio to text using OpenAI's Whisper model.
        
        Args:
            audio_file: File-like object containing audio data
            user_id: User identifier for tracking
            
        Returns:
            Transcribed text from the audio
        """
        self.logger.info(f"Starting voice transcription for user {user_id}")
        try:
            # Send the audio directly to the Whisper API
            transcription = self.ai_client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file
            )
            
            if transcription.text:
                self.logger.info("Voice transcription completed successfully")
                return transcription.text
            else:
                raise Exception("No transcription result from Whisper API")
        except Exception as e:
            self.logger.error(f"Error in callai_voice: {e}")
            raise LLMCallException(message="There was a problem transcribing your voice. Please try again.", original_exception=e)

    def voice2text(self, audio_file, user_id):
        """
        Processes audio file from Flask request and converts it to text.
        
        Args:
            audio_file: FileStorage object from Flask request.files
            
        Returns:
            The transcribed text string
        """
        """ try:
            # Read audio data
            audio_data = audio_file.read()
            
            # Convert audio to a format compatible with Whisper API
            audio = AudioSegment.from_file(BytesIO(audio_data), format="webm")
            
            # Convert to MP3
            mp3_buffer = BytesIO()
            audio.export(mp3_buffer, format="mp3")
            mp3_buffer.seek(0)  # Reset buffer position
            
            # Initialize the OpenAI helper
            helper = OpenAIHelper()
            
            # Call the transcription service
            transcription = helper.callai_voice(mp3_buffer, user_id)
            
            return transcription
            
        except Exception as e:
            self.logger.error(f"Error in voice2text: {str(e)}")
            raise e """
        try:
            # Read audio data once and create a file-like object
            audio_data = audio_file.read()
            audio_io = BytesIO(audio_data)
            audio_io.name = "audio.webm"  # Whisper needs a filename with extension
            
            # Call the transcription service directly
            transcription = self.callai_voice(audio_io, user_id)
            return transcription
        except Exception as e:
            self.logger.error(f"Error in voice2text: {str(e)}")
            raise e

class LLMCallException(Exception):
    """Custom exception for LLM call errors in OpenAIHelper"""
    def __init__(self, message: str = "The connection to the AI model is temporarily down. Please try again later.", original_exception: Optional[Exception] = None):
        self.message = message
        self.original_exception = original_exception
        super().__init__(self.message)

# open_ai_client = OpenAI(
#     base_url=PORTKEY_GATEWAY_URL,
#     default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-gpt4lo-4ce7c1")
# )

# async_client = AsyncOpenAI(
#     base_url=PORTKEY_GATEWAY_URL,
#     default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-gpt4fi-2f6d41"),
# )

# together_async_client = AsyncOpenAI(
#     base_url=PORTKEY_GATEWAY_URL,
#     default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-mixtra-49de64"),
# )


# async def async_callai_internal(messages, username, model=config.LLM_MODEL):
#     logger.debug(f"stage 6b1a: commencing async_callai_internal. TIME: {datetime.now().strftime('%H:%M:%S')}")
#     error = ''
#     response = None
#     try:
#         response = await async_client.chat.completions.create(model=model,
#                                                               messages=messages,
#                                                               temperature=0.4,
#                                                               user=username)
#
#     except Exception as e:
#         logger.error(f"An error occurred: {e}")
#         try:
#             response = await together_async_client.chat.completions.create(model='mistralai/Mixtral-8x7B-Instruct-v0.1',
#                                                                            messages=messages,
#                                                                            temperature=0.4,
#                                                                            user=username)
#         except Exception as e:
#             logger.error(f"An error occurred: {e}")
#             error = "error"
#     logger.debug(f"stage 6b1b: async_callai_internal response received. TIME: {datetime.now().strftime('%H:%M:%S')}")
#
#     return [response, error]


# def callai_streaming(system_content, user_content, user_id, extra_context=None):
#     try:
#         messages = [dict(role="system", content=system_content)]
#         if extra_context:
#             messages.extend(extra_context)
#         if user_content:
#             messages.append(dict(role="user", content=user_content))
#         full_message = ''
#         stream = open_ai_client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0,
#                                                         stream=True,
#                                                         user=str(user_id))
#         for chunk in stream:
#             if chunk.choices[0].delta.content is not None:
#                 part_message = chunk.choices[0].delta.content
#                 full_message += part_message
#                 yield "CHUNK", part_message
#         yield "FINAL_MESSAGE", full_message
#     except Exception as e:
#         print(e)
#         raise e


# def callai(system_content, user_content, user_id, extra_context=None):
#     try:
#         messages = [dict(role="system", content=system_content)]
#         if extra_context:
#             messages += extra_context
#         messages.append(dict(role="user", content=user_content))
#         response = open_ai_client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0,
#                                                           user=str(user_id))
#         if response.choices[0].message.content is not None:
#             return response.choices[0].message.content
#     except Exception as e:
#         print(e)
#         raise e


# def callai_json(system_content, user_content, user_id, extra_context=None):
#     try:
#         messages = [dict(role="system", content=system_content)]
#         if extra_context:
#             messages += extra_context
#         messages.append(dict(role="user", content=user_content))
#         response = open_ai_client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0,
#                                                           user=str(user_id), response_format={'type': 'json_object'})
#         if response.choices[0].message.content is not None:
#             return response.choices[0].message.content
#     except Exception as e:
#         print(e)
#         raise e


# async def callai_async(system_content, user_content, user_id, extra_context=None):
#     try:
#         messages = [dict(role="system", content=system_content)]
#         if extra_context:
#             messages += extra_context

#         messages.append(dict(role="user", content=user_content))
#         response = await async_client.chat.completions.create(model=config.LLM_MODEL,
#                                                               messages=messages,
#                                                               temperature=0.4,
#                                                               user=str(user_id))
#         if response.choices[0].message.content is None:
#             raise Exception("Error in response")
#         return response.choices[0].message.content
#     except Exception as e:
#         try:
#             messages = [dict(role="system", content=system_content)]
#             if extra_context:
#                 messages += extra_context

#             messages.append(dict(role="user", content=user_content))
#             response = await together_async_client.chat.completions.create(model='mistralai/Mixtral-8x7B-Instruct-v0.1',
#                                                                            messages=messages,
#                                                                            temperature=0.4,
#                                                                            user=str(user_id))
#             if response.choices[0].message.content is None:
#                 raise Exception("Error in response")
#             return response
#         except Exception as ee:
#             logger.error(f"An error occurred: {ee}")
#             print(e)
#             raise e
