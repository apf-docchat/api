import os, json, subprocess, sys, requests
from flask import Blueprint, render_template, session, jsonify, request, Response, stream_with_context
from flask_login import login_required
from source.legacy.utilities.helper_functions import load_prompts_from_db, get_files_from_category, userdocs_path
from source.legacy.utilities.openai_calls import callai


procurement = Blueprint('procurement', __name__, template_folder='templates')

@procurement.route('/procurement', methods=['POST'])
@login_required
def procurement_script():
    return render_template('procurement.html', active_page='/procurement',
        modules=session.get('modules', []))

@procurement.route("/procurementupdate", methods=['POST'])
@login_required
def procurementupdate():
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    data = request.get_json()
    user_text = data["user_text"]
    module = data["type"]
    if module == 'dataanalysis':
        dataanalysis_filename = data["dataanalysis_filename"]
    else:
        collection = data["collection"]
    #user_fileselected = data["file_selected"]
    user_files_selected = json.dumps(data["file_selected"])
    # now 'user_text' holds the user input

    cur_dir = os.path.dirname(os.path.realpath(__file__))
    venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
    venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')


    #updating the prompt to work for editing docx section
    prompts = load_prompts_from_db('procurement')
    user_text = str(prompts["procurement_editor_update"]["value"]) + user_text
    result = subprocess.run(
        [venv_python, 'docchat.py', user_text, user_files_selected, orgname, userdocs_path, username, '', module, collection, username],
        stdout=subprocess.PIPE
    )
    encoding = 'UTF-8' #'windows-1252' if sys.platform == 'win32' else 'utf-8'
    output = result.stdout.decode(encoding, errors="ignore")
    return jsonify(output)

@procurement.route("/freshreportgen", methods=['GET'])
@login_required
def freshreportgen():
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    """ data = request.get_json()
    collection = data["collection"] """
    collection = request.args.get('collection')

    def generate():
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
        user_files_selected = json.dumps(["all"])
        module = 'procurement'

        # Construct the full path using os.path.join
        folder_path = os.path.join(userdocs_path, orgname, "files", "docchat")
        file_path = os.path.join(folder_path,"filelist.txt")

        #get the prompt from the prompt admin files
        prompts = load_prompts_from_db('procurement')

        # Read the file content
        with open(file_path, 'r') as file:
            json_filelist = file.read()
        #print(f"File list: {str(json_filelist)}\n")
        filelist = get_files_from_category(json_filelist, collection)
        #print(f"File list: {str(filelist)}\nFolder: {collection}\n")
        answer = ''
        for file in filelist:
            #print(f"File being processed: {file}\n")
            yield f"data: File '{file}' being summarised...\n\n"
            name, ext = os.path.splitext(file)
            with open(os.path.join(folder_path,"structured_text-" + name + ".txt"), 'r') as file_content:
                content = file_content.read()
                system_content = str(prompts["procurement_single_bid_summarise"]["value"]) + "\n" + content
                previous_messages = []
                user_content = ""
                repeat_count = 2
                [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
                answer = answer + "Summary of " + file + ":\n" + response.choices[0].message.content + "\n"
                #print(f"File summarisation completed: {file}\n")
                #yield f"data: Summarisation completed: {file}\n\n"

        yield f"data: Bid Eval Report being generated...\n\n"
        system_content = str(prompts["procurement_evaluate_bids"]["value"]) + "\n" + answer
        previous_messages = []
        user_content = ""
        repeat_count = 2
        [response, error] = callai(system_content, previous_messages, user_content, repeat_count, username)
        report = json.dumps("Bid Evaluation Report:\n" + response.choices[0].message.content)
        yield f"event: finalOutput\ndata: {report}\n\n"
    return Response(stream_with_context(generate()), mimetype='text/event-stream')
    #return report

    #updating the prompt to work for editing docx section
    """ user_text = "Compare all the quotes received and prepare a Bid Evaluation Report."
    result = subprocess.run(
        [venv_python, 'docchat.py', user_text, user_files_selected, orgname, userdocs_path, username, '', module, collection, username],
        stdout=subprocess.PIPE
    )
    encoding = 'UTF-8' #'windows-1252' if sys.platform == 'win32' else 'utf-8'
    output = result.stdout.decode(encoding)      
    return jsonify(output) """

@procurement.route("/freshreportgen2", methods=['POST'])
@login_required
def freshreportgen2():
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    data = request.get_json()
    collection = data["collection"]
    #collection = request.args.get('collection')
    cur_dir = os.path.dirname(os.path.realpath(__file__))
    venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
    venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
    user_files_selected = json.dumps(["all"])
    module = 'procurement'

    # Construct the full path using os.path.join
    folder_path = os.path.join(userdocs_path, orgname, "files", "docchat")
    file_path = os.path.join(folder_path,"filelist.txt")

    try:

        # Perform a GET request to the specified URL
        response = requests.get('http://127.0.0.1:1880/getbidevalreport?file_path='+str(file_path)+'&collection='+str(collection)+'&folder_path='+str(folder_path))

        # Check if the request was successful
        if response.status_code == 200:
            # Extract JSON data from the response
            data = response.json()
            return jsonify(data), 200
        else:
            return jsonify({"error": "Failed to fetch data"}), response.status_code
    except requests.exceptions.RequestException as e:
        # Handle any exceptions that occur during the request
        return jsonify({"error": str(e)}), 500

