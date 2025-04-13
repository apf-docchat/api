import os, sys, json

# Add the utilities folder to the sys.path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from source.api.utilities.helper_functions import get_files_from_category

file_path = sys.argv[3]
folder = sys.argv[4]
#print(f"{file_path} {folder}")
# Read the file content
with open(file_path, 'r') as file:
    json_filelist = file.read()
filelist = get_files_from_category(json_filelist, folder)
print(json.dumps(filelist))
