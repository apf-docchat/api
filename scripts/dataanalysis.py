import os, sys, re
import subprocess
import json
from source.common.utils.debug_logger import set_debug_logger
from source.api.utilities.openai_calls import callai
#import simplejson as json

""" from flask import Blueprint
from flask_login import login_required

dataanalysis = Blueprint('dataanalysis', __name__)


@dataanalysis.route('/dataanalysis', methods=['POST'])
@login_required
def dataanalysis_get_ai_response():
 """
logger = set_debug_logger()
logger.debug(f"inside dataanalysis.py")
orgname = sys.argv[3]
type = sys.argv[7]
dataanalysis_filename = sys.argv[8]
dataanalysis_file_path = os.path.join('../data', 'user_docs', orgname, 'files', 'dataanalysis', dataanalysis_filename)

chat_logs_str = sys.argv[6]  # Assuming it's the 8th argument



cur_dir = os.path.dirname(os.path.realpath(__file__))
venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
#venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
venv_python = sys.executable  # Use the current Python interpreter

# Define paths and variables
base_path = sys.argv[4]
username = sys.argv[5]
#logging.debug("username: " + username)
if not username:
    username = 'default'

current_chat_path = os.path.join(base_path, orgname, 'users', username, 'currentchat')
folder_path = os.path.join(base_path, orgname, 'users', username)

temp_script_file_path = os.path.join('../data', 'user_docs', orgname, 'users', username, 'scripts', 'temp_script.py')
os.makedirs(os.path.join('../data', 'user_docs', orgname, 'users', username, 'scripts'), exist_ok=True)

#empty the file to avoid it being executed again
with open(temp_script_file_path, 'w') as file:
  pass


query = sys.argv[1]

# Parse the JSON string from sys.argv[2] into a list of filenames
filenames = json.loads(sys.argv[2])

def process_chat_log(json_string):
    previous_messages = []
    try:
      chat_array = json.loads(json_string)
      previous_messages = []

      for chat in chat_array:
          question = chat[1] #bad approach - anyways 0 is id, 1 is question, 2 is answer
          response = chat[2]
          previous_messages.append({"role": "user", "content": question})
          previous_messages.append({"role": "assistant", "content": response})
    except:
      pass

    return previous_messages

def clean_response_for_html(response):
  response = response.replace('\u20b9', 'INR')
  response =  re.sub(r'```python', '<pre><code>', response, count=1)
  response =  re.sub(r'```', '</code></pre>', response, count=1)
  return response



previous_messages = process_chat_log(chat_logs_str)


result = subprocess.run(
        [venv_python, 'getdataheader.py', dataanalysis_file_path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
data_header = result.stdout
logger.debug(f"data header: {data_header}")
logger.debug(f"data header error: {result.stderr}")

# Get server and port from environment variables with default values
protocol = os.environ.get('SERVER_PROTOCOL', 'http')
server = os.environ.get('SERVER_HOST', '127.0.0.1')
port = os.environ.get('SERVER_PORT', '5000')
def callai_run_code(data_header, previous_messages, query, venv_python):
  """ messages = [
      {"role": "system", "content": "Provide a strictly formatted JSON response:\n 1. JSON response should have a field named as 'code' which has Python code to answer the User query. \n 2. In the Code string value use \\n to separate lines 3. The user query is for the data in the file at path which is in sys.argv[1]\n 4. Ensure that the sys module is imported corrected in the Python script 5. If data plots are to be shown, save them as png files within the 'extfiles' folder using savefig. Configure xticks using rotation, fontsize and ha so that the x-axis labels are readable. Add a timestamp suffix to the filename to keep the name unique. Print the filenames as separate <img src> tags with the src URL with this template: " + config.extfiles_url + ". Add style='max-width:100%;' to the img tag 6. If the data is to displayed ensured that the print() command is used to print the output 7. The data in the file has the following header.\nHeader:\n"+data_header}
      ] +  previous_messages + [
      {"role": "user", "content": query}
      # You can add more messages here.
  ] """
  # Use OpenAI's Chat API.

  """ response = openai.ChatCompletion.create(
    model=config.LLM_MODEL,  # or "text-davinci-003" for example
    messages=messages
  ) """
  system_content = "Provide a strictly formatted JSON response:\n 1. JSON response should have either a field named as 'code' which has Python code to answer the User query or if the response doesnt have code, then a field named non_code_response\n 2. In the Code string value use \\n to separate lines 3. The user query is for the data in the file at path which is in sys.argv[1]\n 4. Ensure that the sys module is imported corrected in the Python script 5. If data plots are to be shown, save them as png files within the 'extfiles' folder using savefig. Configure xticks using rotation, fontsize and ha so that the x-axis labels are readable. Add a timestamp suffix to the filename to keep the name unique. Print the filenames as separate <img src> tags with the src URL with this template: " + os.getenv('EXT_FILES_URL', 'http://127.0.0.1:5000/extfiles/<filename>') + ". Add style=\"max-width:100%;\" to the img tag 6. If the data is to displayed ensured that the print() command is used to print the output 7. The data in the file has the following header. Do not use any column name not found in the Header. Make sure that the column name used is an exact match including leading and trailing spaces.\nHeader:\n" + data_header
  previous_messages = previous_messages
  user_content = query
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username, { "type": "json_object" })
  code_response = response.choices[0].message.content
  logger.debug(f"Code response: {code_response}")
  code_response =  re.sub(r'```json', '', code_response, count=1)
  code_response =  re.sub(r'```', '', code_response, count=1)
  code_response = code_response.replace('\n', '')
  code_response = code_response.replace("\\'", "'")
  logger.debug(f"Code response: {code_response}")
  code_response = json.loads(code_response)
  code = ''
  non_code_response = ''
  if 'code' in code_response:
    code = code_response['code']
    logger.debug(f"Code: {code}")
  else:
    non_code_response = code_response['non_code_response']
    logger.debug(f"Non code response: {non_code_response}")

  if code != '':
    try:
      """ code_response = json.loads(re.sub(r'\{.*?"', '{"', response.choices[0].message.content.encode('unicode_escape').decode('utf-8')).replace(' :',':').replace("\\",'\\\\'))
      #code_response = json.loads(response.choices[0].message.content.encode('unicode_escape').decode('utf-8'))
      code = code_response['code'].replace("\\n","\n") """

      #code_response = json.loads(response.choices[0].message.content)
      #code_response = json.loads(response.choices[0].message.content)
      #code = code_response['code']
      #logger.debug("Code: " + code)
      # Ensure the variable is a list and it has at least one element
      if isinstance(code, list) and len(code) > 0:
          code = code[0]
      # Write the code to a Python script file
      with open(temp_script_file_path, "w") as f:
          f.write(code)

      # Execute the script
      code_result = subprocess.run(
                  [venv_python, temp_script_file_path, dataanalysis_file_path],
                  stdout=subprocess.PIPE,
                  stderr=subprocess.PIPE,
                  text=True
              )
      # Print the output
      logger.debug(f"Code output: {code_result.stdout}")
      answer = code_result.stdout
      error = code_result.stderr
    except Exception as e:
      logger.debug(f"An error occurred: {str(e)}")
      answer = ""
      error = "error"
  else:
    logger.debug(f"Code output: {non_code_response}")
    answer = non_code_response

  return [code, answer, error]

callai_count = 0
previous_messages = previous_messages[-5:]
while callai_count < 5:
  logger.debug(f"Code creation ROUND {str(callai_count)}")
  [code, answer, error] = callai_run_code(data_header, previous_messages, query, venv_python)
  logger.debug(f"Round {str(callai_count)} answer: {answer} error: {error}")
  if answer != "": #if error == "" and answer != "":
    break
  previous_messages.append({"role": "user", "content": query})
  previous_messages.append({"role": "assistant", "content": "Code:\n"+code+"\nAnswer:"+answer+"\nError:"+error})
  callai_count += 1

#print("OpenAI response received: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "<br>")


# Ensure the directory exists
if not os.path.exists(folder_path):
  logger.debug(f"folder path: {folder_path}")
  os.makedirs(os.path.dirname(current_chat_path), exist_ok=True)
  with open(current_chat_path, 'w') as file:
    file.write("new_chat")

if os.path.exists(current_chat_path):
  with open(current_chat_path, 'r') as file:
      current_chat_name = file.read()


if current_chat_name == 'new_chat':
  """ messages = [
      {"role": "system", "content": "Create a title for a chat based on the User's query in less than 6 words"},
      {"role": "user", "content": query},
      # You can add more messages here.
  ]

  # Use OpenAI's Chat API.
  response = openai.ChatCompletion.create(
    model=config.LLM_MODEL,  # or "text-davinci-003" for example
    messages=messages
  ) """

  system_content = "Create a title for a chat based on the User's query in less than 6 words"
  previous_messages = []
  user_content = query
  repeat_count = 2
  [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)

  #title = response.choices[0].message.content.replace('"', '').replace(' ','_')
  title = response.choices[0].message.content.replace('"', '').replace(' ','_')
  with open(current_chat_path, 'w') as file:
    file.write(title)
  with open(os.path.join(folder_path, title), 'a') as file:  # 'a' mode will create the file if it doesn't exist
      file.write('{"type" : "' + type + '", "file":"'+dataanalysis_filename+'"}' + "\n")  # Convert the dictionary to a JSON string and write it to the file

# Open the 'currentchat' file and read its content
with open(current_chat_path, 'a+') as file:  # 'a+' mode will create the file if it doesn't exist and move the file pointer to the beginning
    file.seek(0)  # Move the file pointer to the beginning of the file
    filename = file.read().strip()

# Now open the file named as filename in the same folder
file_path = os.path.join(folder_path, filename)

# Sample data for the 'question' and 'response' variables
question = query
if answer != "":
  response = answer
else:
  response = "An error occurred. Please try again."

data = {
    "question": question,
    "response": response
}

with open(file_path, 'a') as file:  # 'a' mode will create the file if it doesn't exist
    file.write(json.dumps(data) + "\n")  # Convert the dictionary to a JSON string and write it to the file

# Print the model's reply as a json
new_chat_value = 1 if current_chat_name == 'new_chat' else 0

if new_chat_value == 1:
  response_data = {
      "response": answer,
      "new_chat": new_chat_value,
      "f": title
  }
else:
  response_data = {
      "response": answer,
      "new_chat": new_chat_value
  }

print(json.dumps(response_data))
#print(answer)
