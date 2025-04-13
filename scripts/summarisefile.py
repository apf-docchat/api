import os, sys
# Add the utilities folder to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.api.utilities.openai_calls import callai

username = sys.argv[1]
file = sys.argv[3]
folder_path = sys.argv[4]
prompt = sys.argv[5]

name, ext = os.path.splitext(file)
with open(os.path.join(folder_path,"structured_text-" + name + ".txt"), 'r') as file_content:
    content = file_content.read()
    system_content = str(prompt) + "\n" + content
    previous_messages = []
    user_content = ""
    repeat_count = 2
    [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
    answer = "Summary of " + file + ":\n" + response.choices[0].message.content + "\n"
print(answer.replace('\u20b9', 'INR'))
