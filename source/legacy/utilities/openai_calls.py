import asyncio
import datetime
import json
import logging
import os
import random

from openai import OpenAI, AsyncOpenAI
from portkey_ai import PORTKEY_GATEWAY_URL, createHeaders

from source.legacy.utilities.helper_functions import clean_response_for_html, find_collection_id, find_file_ids, \
    get_custom_instructions, \
    log_to_db, load_prompts_from_db, insert_chatlog, insert_chatthread
from source.common import config

logger = logging.getLogger('app')

_client = OpenAI(
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-gpt4lo-4ce7c1")
)
""" _client = OpenAI(
        base_url=os.getenv('LLM_BASE_URL'),
        api_key=config.LLM_API_KEY
    ) """
""" async_client = AsyncOpenAI(
    base_url=os.getenv('OPENAI_BASE_URL'),
    api_key=config.openai_api_key,
    timeout=10.0,
    max_retries=0,
    http_client=httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=100, max_connections=100)),
)  
together_async_client = AsyncOpenAI(
    base_url=os.getenv('LLM_BASE_URL'),
    api_key=os.getenv('TOGETHER_API_KEY'),
    timeout=40.0,
    max_retries=0,
    http_client=httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=100, max_connections=100)),
) """

async_client = AsyncOpenAI(
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-gpt4fi-2f6d41"),
)
""" http_client=httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=200, max_connections=200)), """
""" async_client = AsyncOpenAI(
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-gpt4lo-4ce7c1")
) """

together_async_client = AsyncOpenAI(
    base_url=PORTKEY_GATEWAY_URL,
    default_headers=createHeaders(provider="openai", api_key=os.getenv("PORTKEY_API_KEY"), config="pc-mixtra-49de64"),
)
""" http_client=httpx.AsyncClient(limits=httpx.Limits(max_keepalive_connections=200, max_connections=200)), """

prompts = load_prompts_from_db('docchat')

def callai_internal(messages, username, response_format={ "type": "text" }):

  error = ''
  response = None
  try:
    """response = openai.ChatCompletion.create(
        model=config.LLM_MODEL,  # or "text-davinci-003" for example
        messages=messages
    )
     except openai.error.OpenAIError as e:
        # Handle API errors here
        print(f"An error occurred: {e}")
        error="error" """
    #system_instr = {"role": "system", "content": "Reply to the user only using the context given here."}
    #print(system_instr)
    response = _client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0, user=username, response_format=response_format)
    #print(response)
  except Exception as e:
    # Handle other types of errors that might occur
    print(f"An unexpected error occurred: {e}")
    error="error"
    #response.choices[0].message.content = "Error, try again..."

  return [response, error]

async def async_callai_internal(messages, username, model = config.LLM_MODEL):

    logger.debug(f"stage 6b1a: commencing async_callai_internal. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    error = ''
    response = None
    """response = openai.ChatCompletion.create(
        model=config.LLM_MODEL,  # or "text-davinci-003" for example
        messages=messages
    )
        except openai.error.OpenAIError as e:
        # Handle API errors here
        print(f"An error occurred: {e}")
        error="error" """
    #system_instr = {"role": "system", "content": "Reply to the user only using the context given here."}
    #print(system_instr)
    try:
        """ response = await asyncio.wait_for(
            async_client.chat.completions.create(model=model, messages=messages, temperature=0.4),
            timeout=60.0  # Timeout after n seconds
            ) """
        """ response = await async_client.chat.completions.create(model=model, messages=messages, temperature=0.4, user=username) """
        response = await async_client.chat.completions.create(model=model, messages=messages, temperature=0.4, user=username)

        """ except TimeoutError:
        logger.debug(f"stage 6b1a2: async_callai_internal TIMEOUT. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
        response = None
        response = await asyncio.wait_for(
            async_client.chat.completions.create(model=model, messages=messages, temperature=0.4),
            timeout=60.0  # Timeout after n seconds
            ) """

    except Exception as e:
        logger.error(f"An error occurred: {e}")
        response = None
        try:
            """ response = await together_async_client.chat.completions.create(model='mistralai/Mixtral-8x7B-Instruct-v0.1', messages=messages, temperature=0.4, user=username) """
            response = await together_async_client.chat.completions.create(model='mistralai/Mixtral-8x7B-Instruct-v0.1', messages=messages, temperature=0.4, user=username)
        except Exception as e:
            logger.error(f"An error occurred: {e}")
            error="error"
            response = None
    logger.debug(f"stage 6b1b: async_callai_internal response received. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")

    return [response, error]


def callai(system_content, previous_messages, user_content, repeat_count, username, response_format={ "type": "text" }):
    messages = [
    {"role": "system", "content": system_content}] + previous_messages + [{"role": "user", "content": user_content}]
    # Use OpenAI's Chat API.
    error = ""
    count = 0
    response = None
    while count < repeat_count:
        timestamp_start = datetime.datetime.now()  # Log the start time
        [response, error] = callai_internal(messages, username, response_format)
        timestamp_end = datetime.datetime.now()  # Log the end time after getting response

        # Log to the database after each call to callai_internal
        log_to_db(username, user_content, system_content, timestamp_start, timestamp_end, response)

        if error == "":
            break
        count += 1
    return [response, error]

async def async_callai(system_content, previous_messages, user_content, repeat_count, username, model = config.LLM_MODEL):
    messages = [
    {"role": "system", "content": system_content}] + previous_messages + [{"role": "user", "content": user_content}]
    # Use OpenAI's Chat API.
    error = ""
    count = 0
    response = None
    while count < repeat_count:
        timestamp_start = datetime.datetime.now()  # Log the start time
        [response, error] = await async_callai_internal(messages, username, model=model)
        timestamp_end = datetime.datetime.now()  # Log the end time after getting response

        # Log to the database after each call to callai_internal
        log_to_db(username, user_content, system_content, timestamp_start, timestamp_end, response)

        if error == "":
            break
        count += 1
    logger.debug(f"stage 6b2: completed async_callai for {user_content} with error {error} and response {response}. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    return response #[response, error]

def callai_streaming(system_content, previous_messages, user_content, new_chat, latest_chat_thread_id, new_title_prompt, module, collection, metadata_json, username, orgname):
  messages = [
    {"role": "system", "content": system_content}] + previous_messages + [{"role": "user", "content": user_content}]
  full_message = ''
  stream = _client.chat.completions.create(model=config.LLM_MODEL, messages=messages, temperature=0, stream=True, user=username)
  for chunk in stream:
      if chunk.choices[0].delta.content is not None:
          part_message = chunk.choices[0].delta.content.replace('\n','<br>')
          full_message += part_message
          #print(chunk.choices[0].delta.content)
          yield f"data: {part_message}\n\n"
  #chatlog processing follows...
  response_data = process_chatlog(new_chat, latest_chat_thread_id, new_title_prompt, module, collection, user_content, full_message, metadata_json, username, orgname)
  yield f"event: finalOutput\ndata: {response_data}\n\n"

def categorise_query(query, username):
  system_content = str(prompts["categorise_user_query"]["value"])
  previous_messages = []
  user_content = query
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
  #print(type(response))
  return response.choices[0].message.content[0]

def process_chatlog(new_chat, latest_chat_thread_id, new_title_prompt, module, collection, query, answer, metadata_json, username, orgname):
    title = "new chat"
    if new_chat == 'yes':
        system_content = str(new_title_prompt)
        previous_messages = []
        user_content = query
        repeat_count = 2
        [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
        if response is not None:
            title = response.choices[0].message.content.replace('"', '') #.replace(' ','_')
        #title = datetime.datetime.now().strftime("%Y-%m-%d-%H-%M-%S") #set using AI later. Currently date & time for testing

    # Generate a unique id for this round of question and answer for unique ref in the frontend
    unique_id = str(random.randint(1000000, 9999999))
    new_chat_value = 1 if new_chat == 'yes' else 0
    if new_chat_value == 1:
        latest_chat_thread_id = insert_chatthread(title, module, collection, unique_id, "user", query, "", username, orgname)
        result = insert_chatlog(latest_chat_thread_id, unique_id, "assistant", answer, json.dumps(metadata_json))
        response_data = {
            "id": unique_id,
            "response": answer,
            "new_chat": str(new_chat_value),
            "f": str(latest_chat_thread_id),
            "metadata": json.dumps(metadata_json)  # Assuming metadata_json is a dictionary or list
        }
        # Serialize the dictionary to a JSON-formatted string
        response_data = json.dumps(response_data)

    else:
        result = insert_chatlog(latest_chat_thread_id, unique_id, "user", query, "")
        result = insert_chatlog(latest_chat_thread_id, unique_id, "assistant", answer, json.dumps(metadata_json))
        print("assistant msg insert: " + str(result))
        response_data = {
            "id": unique_id,
            "response": answer,
            "new_chat": str(new_chat_value),
            "f": str(latest_chat_thread_id),
            "metadata": json.dumps(metadata_json)  # Assuming metadata_json is a dictionary or list
        }
        # Serialize the dictionary to a JSON-formatted string
        response_data = json.dumps(response_data)
    return response_data

async def async_metadata_search(collection, orgname, query, old_chat_logs, username, organization_id):
    from source.legacy.utilities.externalapi_helpers.docchat_helper import DocChatManager
    collection_id = find_collection_id(collection)
    file_ids = find_file_ids(collection_id)
    docchat_manager = DocChatManager()
    docchat_manager.collection_id = collection_id
    docchat_manager.organization_id = organization_id
    docchat_manager.find_metadata()
    metadata_list = [json.dumps(metadata) for metadata in docchat_manager.metadata_list]
    # metadata_list = get_metadata_for_files(file_ids)
    custom_instructions = get_custom_instructions(orgname, collection)
    concatenated_metadata = ''
    answer_array = []
    previous_messages = old_chat_logs[-2:]
    user_content = query + "\nPlease don't give JSON response."
    repeat_count = 1
    tasks = []
    # for i in range(0, len(metadata_list), 3):
    #     logger.debug(f"stage 6b: processing metadata_list {i} out of {len(metadata_list)}. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    #     concatenated_metadata = '\n'.join(metadata_list[i:i+3]) + '\n'
    #     #concatenated_metadata = '\n'.join(metadata_list[i:len(metadata_list)]) + '\n'
    #     #metadata_prompt = get_metadata_prompt(collection_id, False)
    #     #system_content =  f"You have to use the data in the Context and answer the User query. Only respond based on the data in the Context. DO NOT use any other source of data.\n{custom_instructions}\n Refer the below for details on what each field in the Context means:\n{metadata_prompt}\nContext:\n{concatenated_metadata}"
    #     system_content =  f"You have to use the data in the Context and answer the User query. Only respond based on the data in the Context. DO NOT use any other source of data. \nThis is part of an iterative loop. So in your response please add the context necessary so that when the responses are merged, all context needed for merging is there. \n{custom_instructions}\nContext:\n{concatenated_metadata}"
    #     #[response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
    #     task = asyncio.create_task(async_callai(system_content, previous_messages, user_content, repeat_count, username))
    #     await asyncio.sleep(1)
    #     tasks.append(task)
    #     #break
    # responses = await asyncio.gather(*tasks)

    # logger.debug(f"stage 6c: completed asyncio gather. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    # for response in responses:
    #     if response is not None:
    #         answer_array.append(clean_response_for_html(response.choices[0].message.content))

    # #answer = '\nAnswer: '.join(answer_array)
    # answer = '\nAnswer: ' + '\nAnswer: '.join(answer_array)
    # return answer

    total_task = len(metadata_list) // 3

    responses = []

    async def task_wrapper(index):
        nonlocal concatenated_metadata
        start_index = index * 3
        end_index = min((index + 1) * 3, len(metadata_list))
        concatenated_metadata = '\n'.join(metadata_list[start_index:end_index]) + '\n'
        system_content =  f"You have to use the data in the Context and answer the User query. Only respond based on the data in the Context. DO NOT use any other source of data. \nThis is part of an iterative loop. So in your response please add the context necessary so that when the responses are merged, all context needed for merging is there. \n{custom_instructions}\nContext:\n{concatenated_metadata}"
        response = await async_callai(system_content, previous_messages, user_content, repeat_count, username)
        return response

    tasks = [task_wrapper(i) for i in range(total_task)]

    for task in asyncio.as_completed(tasks):
        progress = int(len(responses) / total_task * 100)
        yield progress
        response = await task
        if response is not None:
            responses.append(response)

    for response in responses:
        if response is not None:
            answer_array.append(clean_response_for_html(response.choices[0].message.content))

    answer = '\nAnswer: ' + '\nAnswer: '.join(answer_array)
    yield answer

def metadata_search(collection_name, orgname, query, old_chat_logs, username, new_chat=None, latest_chat_thread_id=None, new_title_prompt=None, module=None, metadata_json=None, collection=None, organization_id=None):
    #langchain based query approach below
    """ logger.debug(f"stage 6: commencing async_metadata_search. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    collection_id = find_collection_id(collection)
    file_ids = find_file_ids(collection_id)
    metadata_list = get_metadata_for_files(file_ids)
    concatenated_metadata = ''.join(metadata_list)
    #logger.debug(f"{concatenated_metadata}")
    previous_messages = old_chat_logs[-2:]
    user_content = query + "\nPlease don't give JSON response."

    from langchain_core.prompts import ChatPromptTemplate
    from langchain_openai import ChatOpenAI

    prompt = ChatPromptTemplate.from_template("Answer the following question based only on the provided context:

    <context>
    {context}
    </context>

    Question: {input}")

    llm = ChatOpenAI(model="gpt-4-turbo-preview", temperature=0)
    from langchain_core.output_parsers import StrOutputParser

    output_parser = StrOutputParser()
    chain = prompt | llm | output_parser
    logger.debug(f"stage 6a: commencing llm invoke. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    response = chain.invoke({"input": user_content, "context": concatenated_metadata})
    logger.debug(f"stage 6b: completed llm invoke. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    import markdown
    answer = markdown.markdown(response)     """


    #direct query approach below
    # logger.debug(f"stage 6: commencing async_metadata_search. API Base Url: {os.getenv('OPENAI_BASE_URL')} and model: {os.getenv('LLM_MODEL')}  TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    # answer = asyncio.run(async_metadata_search(collection, orgname, query, old_chat_logs, username))

    # #answer = ''.join(answer_array)
    # if (answer == ""):
    #     answer = "Sorry unable to respond at the moment. Please try again."
    # else:
    #     logger.debug(f"stage 6d: answers concatenated. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    #     system_content =  f"Merge the separate Answer texts given below as a single unified, coherent answer to the User query. For list type queries, if any one response has an answer, then remove the parts which say that there is no context etc. Don't add any new information. Only use what is there in the answers. Don't miss out any names mentioned in the Separate answers. \nSeparate Answers:\n {answer}"
    #     previous_messages = [] #old_chat_logs[-2:]
    #     user_content = query

    #     repeat_count = 1
    #     [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
    #     answer = "Sorry unable to respond at the moment. Please try again."
    #     if response is not None:
    #         answer = clean_response_for_html(response.choices[0].message.content)

    #     """ system_content =  f"Separate Answers:\n {answer}"
    #     previous_messages = []
    #     user_content = "Merge the separate Answer texts into a single unified, coherent answer. For list type answers, if any one answer has even one entity, then remove the parts which say that there is no context etc. Don't add any new information. Only use what is there in the answers." """

    # logger.debug(f"stage 7: completed async_metadata_search. TIME: {datetime.datetime.now().strftime('%H:%M:%S')}")
    # return answer

    async_generator = async_metadata_search(collection_name, orgname, query, old_chat_logs, username, organization_id)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        while True:
            try:
                response = loop.run_until_complete(async_generator.__anext__())
                if isinstance(response, float):  # Progress
                    yield f"event: progressOutput\ndata: {response:.2f}%\n\n".encode('utf-8')
                elif isinstance(response, str):  # Answer
                    system_content = f"Merge the separate Answer texts given below as a single unified, coherent answer to the User query. For list type queries, if any one response has an answer, then remove the parts which say that there is no context etc. Don't add any new information. Only use what is there in the answers. Don't miss out any names mentioned in the Separate answers. \nSeparate Answers:\n {response}"
                    previous_messages = []  # old_chat_logs[-2:]
                    user_content = query
                    repeat_count = 1

                    [ai_response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)

                    answer = "Sorry unable to respond at the moment. Please try again."
                    if ai_response is not None:
                        answer = clean_response_for_html(ai_response.choices[0].message.content)
                        answer = process_chatlog(new_chat, latest_chat_thread_id, prompts["give_title_new_chat"]["value"], module, collection['collection_name'], query, answer, metadata_json, username, orgname)
                    yield f"event: finalOutput\ndata: {answer}\n\n".encode('utf-8')
            except StopAsyncIteration:
                break
    finally:
        loop.close()
