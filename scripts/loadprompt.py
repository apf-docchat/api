import os,sys, json

#from flask import request

# Add the utilities folder to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.api.utilities.helper_functions import load_prompts_from_db

prompt_name = sys.argv[3]
prompts = load_prompts_from_db(prompt_name)
print(json.dumps(prompts))
