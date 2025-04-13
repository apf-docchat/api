import os, sys, json
# Add the utilities folder to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.api.utilities.openai_calls import callai

username = sys.argv[1]
# Read the file path from command line arguments
file_path = sys.argv[2]

# Read data from the file
with open(file_path, 'r') as file:
    data = json.load(file)

system_content = json.dumps(data)
previous_messages = []
user_content = sys.argv[4] if len(sys.argv) > 4 else ""
repeat_count = 2
[response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
print(response.choices[0].message.content.replace('\u20b9', 'INR'))
