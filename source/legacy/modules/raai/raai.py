import json
import logging
import os
import re

from flask import Blueprint, redirect, session, request, jsonify, Response, render_template, send_file, url_for
from flask_login import login_required
from openai import OpenAI

from source.legacy.utilities.helper_functions import api_v1_get_file, load_prompts_from_db, generic_query, \
    add_files_to_db
from source.legacy.utilities.openai_calls import callai, callai_streaming
from source.common import config

raai = Blueprint('raai', __name__, template_folder='templates')

logger = logging.getLogger('app')

def raai_generate(response_data):
   yield f"event: finalOutput\ndata: {response_data}\n\n"

@raai.route("/raai", methods=['GET', 'POST'])
@login_required
def raai_home():
  return render_template(
      'raaihome.html'
  )

@raai.route('/ragetstarted', methods=['GET'])
def rauploadfiles():
    # Your code to generate or retrieve HTML content
    return redirect(url_for('raai.raai_uploadfiles'))

@raai.route("/rauploadfiles", methods=['GET'])
@login_required
def raai_uploadfiles():
  return render_template(
      'rauploadfiles.html'
  )

@raai.route("/raainewchat", methods=['GET', 'POST'])
@login_required
def raai_new_chat():

  return render_template(
      'raai.html',
      active_page='/raainewchat',
      modules=session.get('modules', []),
      imgpathprefix='https://demo.nlightnconsulting.com/static/images/card-header-img'
  )

@raai.route("/radocguidestart", methods=['POST'])
@login_required
def raai_docguide_start():
  return {"redirect": "/radocguide"}

@raai.route("/radocguide", methods=['GET', 'POST'])
@login_required
def raai_docguide():
  filename = request.args.get("filename")
  return render_template(
      'radocguide.html',
      filename=filename
  )

#@raai.route('/', methods=['POST'])
@raai.route('/raairespond', methods=['GET'])
@login_required
def raai_get_ai_response():
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    query = request.args.get("user_text")
    module = request.args.get("type")
    search_type = request.args.get("search_type")
    new_chat = request.args.get("new_chat")
    filename = request.args.get("filename")
    previousMessages = request.args.get("chatlog")

    prompts = load_prompts_from_db('docchat')
    new_chat_value = 0
    latest_chat_thread_id = None

    #query_type = categorise_query(query, username) #old code used to categorise and do different things. for later reference in case this needs to be brought back

    try:
      #retrieve relevant vectors from pinecone and then send to llm
      os.environ["OPENAI_API_KEY"] = config.OPENAI_API_KEY
      client = OpenAI(
        api_key=config.OPENAI_API_KEY,
      )
      previous_messages = []
      metadata_json = []
      MODEL = config.EMBEDDING_MODEL
      from pinecone import Pinecone
      # initialize connection to pinecone (get API key at app.pinecone.io)
      pc = Pinecone(api_key=config.PINECONE_API_KEY)

      # check if index already exists (only create index if not)
      if config.PINECONE_INDEX_NAME not in pc.list_indexes():
          pc.create_index(config.PINECONE_INDEX_NAME, dimension=1536) #old - len(embeds[0])
      # connect to index and get query embeddings
      index = pc.Index(config.PINECONE_INDEX_NAME)
      xq = client.embeddings.create(input=query, model=MODEL).data[0].embedding

      topk = 40
      res = index.query(vector=[xq], filter={"orgname": {"$eq":orgname}, "filename": {"$in":[filename]}}, top_k=topk, include_metadata=True)

      if (len(res['matches'])>0):
        if res['matches']:
            context_prompt = ''

            for i in range(len(res['matches'])):
                potential_prompt = context_prompt + res['matches'][i]['metadata']['_node_content']
                if len(potential_prompt) < 32000:
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

        system_content = str(prompts["raai_basic_query_response"]["value"]) + context_prompt
        user_content = query
        previous_messages = json.loads(previousMessages)
        #repeat_count = 2
        """ [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
        answer = clean_response_for_html(response.choices[0].message.content) """
        print("just before calling SSE Response")
        collection = ""
        metadata_json = []
        return Response(callai_streaming(system_content, previous_messages, user_content, new_chat, latest_chat_thread_id, prompts["give_title_new_chat"]["value"], module, collection, metadata_json, username, orgname), content_type='text/event-stream')

      else:
        answer = "Insufficient data to respond to this question."


      #return jsonify(response_data)
      return Response(raai_generate(response_data), content_type='text/event-stream')


    except Exception as e:
      #print(f"An error occurred: {e}")
      logger.error(f"Error occurred: {e}")
      answer = "Unable to respond due to an error. Please try asking the question with more keywords. If that doesn't work, please try after some time."
      new_chat_value = 0
      response_data = {
        "id": "",
        "response": answer,
        "new_chat": str(new_chat_value),
        "metadata": "[]"  # Assuming metadata_json is a dictionary or list
      }
      # Serialize the dictionary to a JSON-formatted string
      response_data = json.dumps(response_data)
      #return jsonify(response_data)
      return Response(raai_generate(response_data), content_type='text/event-stream')

@raai.route('/raaigetfirstresponse', methods=['POST'])
@login_required
def raai_getfirstresponse():
  username = session.get("username", "")
  orgname = session.get("orgname", "")
  data = request.get_json()
  filename = data["filename"]
  fileids = generic_query("files", "file_id", {"file_name": filename})
  summaries = []
  for fileid in fileids:
    summaries.append(generic_query("files_metadata", "summary_short", {"file_id": fileid}))

  system_content = "Return a strictly formatted JSON with the following contents:\nintrotext: Introduce the Content in 50 words. In the next para, prompt the User to do one of the following:(i) Ask a question OR (ii) Press one of the leading questions button\nContent:\n" + json.dumps(summaries)
  previous_messages = []
  user_content = ""
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
  response = response.choices[0].message.content #clean_response_for_html(response.choices[0].message.content)
  response =  re.sub(r'```json', '', response, count=1)
  response =  re.sub(r'```', '', response, count=1)

  return jsonify({"response": response}) #.replace('\n','<br>')})

@raai.route('/raaigetleadingqns', methods=['POST'])
@login_required
def raai_getleadingqns():
  username = session.get("username", "")
  orgname = session.get("orgname", "")

  data = request.get_json()
  filename = data["filename"]
  previousMessages = json.loads(data["previousmessages"])

  fileids = generic_query("files", "file_id", {"file_name": filename})
  print(fileids)
  summaries = []
  questions = ""
  sections = []
  for fileid in fileids:
    summaries.append(generic_query("files_metadata", "summary_long", {"file_id": fileid}))
    questions += json.dumps(generic_query("files_metadata", "questions", {"file_id": fileid}))
    sections.append(json.dumps(generic_query("files_metadata", "sections", {"file_id": fileid})))

  system_content = "Imagine that you are the User and have already asked some questions to know more about the content of the document. Given below is a Summary of the contents of the documents, the chat log till now, the Questions the document can answer and the Sections of the document.\n After referring to all of that generate what would be the next best questions to ask to know the contents of the document more. Dont generate questions that are generally about the topic. Keep the questions to be about the contents of the document. If the User has not asked many questions till now, then ask opening type questions like 'Tell me a little about this document.', 'Give a summary of the document' etc. Generate the leading questions one Section after another. Follow the sequence of the Sections.\n Return a strictly formatted JSON with the following contents:\nleadingquestion1: most relevant next question the User could ask based on the User and AI messages till now and the Content below. \nquestion1summary: summary of leadingquestion1 as a 10 word question\nleadingquestion2: another  question the User could ask to know more\nquestion2summary: summary of leadingquestion2 as a 10 word question.\nContent:\n" +  json.dumps(summaries) + "\nQuestions the Content can can answer:\n" + questions + "\nSections:\n" + json.dumps(sections)
  previous_messages = previousMessages
  print(json.dumps(previous_messages))
  user_content = ""
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
  response = response.choices[0].message.content #clean_response_for_html(response.choices[0].message.content)
  response =  re.sub(r'```json', '', response, count=1)
  response =  re.sub(r'```', '', response, count=1)

  return jsonify({"response": response}) #.replace('\n','<br>')})

@raai.route('/raaiviewfile', methods=['GET'])
@login_required
def raai_viewfile():
    #orgname = session.get("orgname", "")
    filename = request.args.get("filename")
    #pdf_path = os.path.join(config.ORGDIR_PATH, orgname, config.insideorgfolder_path,filename)
    response = api_v1_get_file(filename)
    print(response)
    return send_file(response['internal_path'], as_attachment=False)

@raai.route('/call_addfiles', methods=['POST'])
def call_addfiles():
    #only needed for dev environment
    environment = os.getenv("ENVIRONMENT")
    if environment is not None and environment == 'dev':
      # This route will call the /addfiles route
      orgname = session.get('orgname','')
      data = request.json
      filename = data["filename"]
      add_files_to_db(orgname, [filename])
    else:
       pass
    return jsonify({"status": "success"})
