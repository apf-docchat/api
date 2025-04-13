import json
import logging
import os
import re
from datetime import datetime

from flask import Blueprint, session, request, jsonify, Response
from flask_login import login_required
from openai import OpenAI

from source.legacy.utilities.helper_functions import generic_query, get_collection_id_by_name, get_custom_instructions, \
    get_old_chat_logs_new, get_latestchatthreadid, load_prompts_from_db
from source.legacy.utilities.openai_calls import callai, callai_streaming, metadata_search
from source.legacy.utilities.openai_calls import process_chatlog
from source.common import config

docchat = Blueprint('docchat', __name__)

logger = logging.getLogger('app')

def generate(response_data):
   yield f"event: finalOutput\ndata: {response_data}\n\n"


#@docchat.route('/', methods=['POST'])
@docchat.route('/docchat', methods=['GET'])
@login_required
def docchat_get_ai_response():
    logger.debug(f"Stage 1: Inside docchat_get_ai_response. TIME: {datetime.now().strftime('%H:%M:%S')}")
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    """ data = request.get_json()
    query = data["user_text"]
    module = data["type"]
    search_type = data["search_type"]
    new_chat = data["new_chat"] 
    collection = data["collection"] """
    query = request.args.get("user_text")
    module = request.args.get("type")
    search_type = request.args.get("search_type")
    new_chat = request.args.get("new_chat")
    collection = request.args.get("collection")

    metadata_json = []

    latest_chat_thread_id = None
    if (new_chat == 'no'):
      latest_chat_thread_id = get_latestchatthreadid()
    if (new_chat == 'no'):
      old_chat_logs, old_chat_ids, module_temp, collection_temp, metadata_array_str = get_old_chat_logs_new(latest_chat_thread_id)
    else:
      old_chat_logs = []
      old_chat_ids = []
      module_temp = ''
      collection_temp = ''
      metadata_array_str = ''
    if module_temp != "":
        module = module_temp
    if collection_temp != '':
        collection = collection_temp
    #old_chat_logs_string = json.dumps(old_chat_logs)

    prompts = load_prompts_from_db('docchat')
    new_chat_value = 0

    #get custom instructions to pad to the prompt
    custom_instructions = get_custom_instructions(orgname, collection)

    #query_type = categorise_query(query, username) #old code used to categorise and do different things. for later reference in case this needs to be brought back

    try:
      #docchat has 2 modes: default and metadata search. following is to handle default.
      #first retrieve relevant vectors from pinecone and then send to llm
      if (search_type == "default"):
        logger.debug(f"Stage 2: Starting default search. API Base Url: {os.getenv('LLM_BASE_URL')} and model: {os.getenv('LLM_MODEL')}  TIME: {datetime.now().strftime('%H:%M:%S')}")
        os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
        client = OpenAI(
          api_key=config.OPENAI_API_KEY,
        )
        previous_messages = old_chat_logs[-2:] #old_chat_logs #process_chat_log(chat_logs_str)
        MODEL = config.EMBEDDING_MODEL
        from pinecone import Pinecone
        # initialize connection to pinecone (get API key at app.pinecone.io)
        # pinecone.init(
        #     api_key=config.pinecone_api_key,
        #     environment=config.pinecone_environment  # find next to API key in console
        # )
        pc = Pinecone(api_key=config.PINECONE_API_KEY)

        # check if index already exists (only create index if not)
        if config.PINECONE_INDEX_NAME not in pc.list_indexes():
            pc.create_index(config.PINECONE_INDEX_NAME, dimension=1536) #old - len(embeds[0])
        # connect to index and get query embeddings
        pinecone_index = pc.Index(config.PINECONE_INDEX_NAME)
        xq = client.embeddings.create(input=query, model=MODEL).data[0].embedding

        topk = 100
        res = pinecone_index.query(vector=[xq], filter={"orgname": {"$eq":orgname}, "collection": {"$in":[collection]}}, top_k=topk, include_metadata=True)

        #if (len(res['matches'])>0):
        if res['matches']:
            logger.debug(f"Stage 3: vector db matches found. TIME: {datetime.now().strftime('%H:%M:%S')}")
            context_prompt = ''

            for i in range(len(res['matches'])):
                potential_prompt = context_prompt + res['matches'][i]['metadata']['_node_content']
                if len(potential_prompt) < 80000:
                    #context_prompt = potential_prompt

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

                    context_prompt += json.dumps(metadata)
                else:
                    break
        else:
            context_prompt = ''

        logger.debug(f"Stage 4: context prompt created. ready to call ai. TIME: {datetime.now().strftime('%H:%M:%S')}")
        system_content = str(prompts["respond_to_search_user_query"]["value"]) + f"\n{custom_instructions}\n" + "\nContext:\n" + context_prompt
        user_content = query
        #repeat_count = 2
        """ [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
        answer = clean_response_for_html(response.choices[0].message.content) """
        print("just before calling SSE Response")
        return Response(callai_streaming(system_content, previous_messages, user_content, new_chat, latest_chat_thread_id, prompts["give_title_new_chat"]["value"], module, collection, metadata_json, username, orgname), content_type='text/event-stream')

        """ else:
          print("stage 5")
          answer = "Insufficient data to respond to this question." """

      #docchat has 2 modes: default and metadata search. following is to handle metadata search
      #no pinecone vectors used. take metadata from mysql and send to llm

      #following is the code for async calls for the same. the old sync calls for this is commented out below
      else:
        #answer = asyncio.run(metadata_search(collection, query, old_chat_logs, username))
        answer = metadata_search(collection, orgname, query, old_chat_logs, username)
        print("Completed async_metadata_search")

      #sync implementation of the metadata search. replaced by async above
      """ else:
        print("stage 6")
        collection_id = find_collection_id(collection)
        file_ids = find_file_ids(collection_id)
        metadata_list = get_metadata_for_files(file_ids)
        concatenated_metadata = ''
        answer_array = []
        previous_messages = old_chat_logs[-2:]
        user_content = query + "\nPlease don't give JSON response. Please don't give a numbered list."
        repeat_count = 1

        for i in range(0, len(metadata_list), 5):
          concatenated_metadata = '\n'.join(metadata_list[i:i+5]) + '\n'
          #metadata_prompt = get_metadata_prompt(collection_id, False)
          #system_content =  f"You have to use the data in the Context and answer the User query. Only respond based on the data in the Context. DO NOT use any other source of data.\n{custom_instructions}\n Refer the below for details on what each field in the Context means:\n{metadata_prompt}\nContext:\n{concatenated_metadata}"
          system_content =  f"You have to use the data in the Context and answer the User query. Only respond based on the data in the Context. DO NOT use any other source of data.\nContext:\n{concatenated_metadata}"
          [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
          answer_array.append(clean_response_for_html(response.choices[0].message.content))
        answer = '\n'.join(answer_array)
        system_content =  f"\nRephrase the text given by User to form one combined list instead of separate lists."
        previous_messages = []
        user_content = answer
        repeat_count = 1
        [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
        answer = clean_response_for_html(response.choices[0].message.content)
        print("stage 7")
        #when byepassing AI for testing purposes, comment out code above and use the statement below
        #answer = "sending response byepassing AI for testing"
        #logger.debug(answer) """


      #chatlog processing follows...
      logger.debug(f"Stage 8: answer obtained. ready to process chatlog. TIME: {datetime.now().strftime('%H:%M:%S')}")
      response_data = process_chatlog(new_chat, latest_chat_thread_id, prompts["give_title_new_chat"]["value"], module, collection, query, answer, metadata_json, username, orgname)

      return jsonify(response_data)
      #return Response(generate(response_data), content_type='text/event-stream')
      #return Response(callai_streaming(system_content, previous_messages, user_content, new_chat, latest_chat_thread_id, prompts["give_title_new_chat"]["value"], module, collection, metadata_json, username, orgname), content_type='text/event-stream')


    except Exception as e:
      #print(f"An error occurred: {e}")
      logger.error(f"Stage 9: Error occurred: {e}")
      answer = "Sorry unable to respond at the moment. Please try again."
      new_chat_value = 0
      response_data = {
        "id": "",
        "response": answer,
        "new_chat": str(new_chat_value),
        "metadata": "[]"  # Assuming metadata_json is a dictionary or list
      }
      # Serialize the dictionary to a JSON-formatted string
      response_data = json.dumps(response_data)
      if search_type == "default":
        return Response(generate(response_data), content_type='text/event-stream')
      else:
        return jsonify(response_data)

@docchat.route('/getleadingquestions', methods=['POST'])
@login_required
def firstresponse():
  username = session.get("username", "")
  orgname = session.get("orgname", "")
  data = request.get_json()
  latest_chat_thread_id = data.get("latestchatthreadid",'')
  collection = data["collection"]

  #get custom instructions to pad to the prompt
  collection_id = get_collection_id_by_name(orgname, collection)
  custom_instructions = generic_query('collections', 'custom_instructions', {"collection_id": collection_id})[0][0]

  system_content =  f"\n{custom_instructions}\n"
  previous_messages = []
  if latest_chat_thread_id != '':
    previous_messages, old_chat_ids, module_temp, collection_temp, metadata_array_str = get_old_chat_logs_new(latest_chat_thread_id)
  user_content = "Return a strictly formatted JSON with the following contents:\nleadingquestion1: Please provide a leading question for the User to ask the AI assistant to continue the discussion. Provide the question in 6-8 words.\nleadingquestion2: provide one more question of the above kind in 6-8 words."
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
  response = response.choices[0].message.content #clean_response_for_html(response.choices[0].message.content)
  response =  re.sub(r'```json', '', response, count=1)
  response =  re.sub(r'```', '', response, count=1)
  print(response)
  return jsonify({"response": response}) #.replace('\n','<br>')})
