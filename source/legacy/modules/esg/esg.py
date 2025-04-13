import os, json, subprocess, sys
from flask import Blueprint, render_template, session, jsonify, request
from flask_login import login_required
from source.legacy.utilities.helper_functions import docx_to_html, load_prompts_from_db, userdocs_path
from docx import Document

esg = Blueprint('esg', __name__, template_folder='templates')


@esg.route('/templateedit', methods=['POST'])
@login_required
def template_edit():
    return render_template('template_index.html', active_page='/templateedit',
        modules=session.get('modules', []))

@esg.route('/templateupload', methods=['POST'])
@login_required
def template_upload_file():
    module = 'templateedit'
    orgname = session.get('orgname', '')
    if 'file' not in request.files:
        return jsonify(error="No file part"), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify(error="No selected file"), 400
    if not file.filename.endswith('.docx'):
        return jsonify(error="Invalid file type"), 400

    # Save and read the DOCX file
    saved_file_path_name =  os.path.join(userdocs_path, orgname, 'files', module, file.filename)
    os.makedirs(os.path.join(userdocs_path, orgname), exist_ok=True)
    os.makedirs(os.path.join(userdocs_path, orgname, 'files', module), exist_ok=True)
    file.save(saved_file_path_name)

    html_content = docx_to_html(saved_file_path_name,'')
    return ''.join(html_content)

@esg.route("/templateupdate", methods=['POST'])
@login_required
def template_update():
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

    #cur_dir = os.path.dirname(os.path.realpath(__file__))
    venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
    venv_python = os.path.join(os.getcwd(), 'venv', venv_dir, 'python')


    #updating the prompt to work for editing docx section
    prompts = load_prompts_from_db('esg')
    user_text = str(prompts["template_editor_update"]["value"]) + user_text
    result = subprocess.run(
        [venv_python, os.path.join(os.getcwd(),'docchat.py'), user_text, user_files_selected, orgname, userdocs_path, username, '', module, collection, username],
        stdout=subprocess.PIPE
    )
    encoding = 'UTF-8' #'windows-1252' if sys.platform == 'win32' else 'utf-8'
    output = result.stdout.decode(encoding, errors="ignore")
    return jsonify(output)

@esg.route('/templatesave', methods=['POST'])
@login_required
def template_save():
    content = request.json.get('content')
    # Define the path to save the DOCX file
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    DOCX_FILE_PATH = os.path.join('data', 'user_docs', orgname,'users', username, 'savedtemplatefiles', request.json.get('filename'))
    os.makedirs(os.path.join('data', 'user_docs', orgname,'users', username, 'savedtemplatefiles'), exist_ok=True)

    # Create a new Document
    doc = Document()

    # Add the content to the Document
    doc.add_paragraph(content)

    # Save the Document as a DOCX file
    doc.save(DOCX_FILE_PATH)

    return jsonify(success=True), 200

@esg.route('/templatefilelist')
@login_required
def template_file_list():
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    directory = os.path.join('data', 'user_docs', orgname, 'users', username, 'savedtemplatefiles')
    if not os.path.exists(directory):
        return jsonify([])

    files = [f for f in os.listdir(directory) if os.path.isfile(os.path.join(directory, f))]
    return jsonify(files)

@esg.route('/gettemplatecontent/<string:filename>')
@login_required
def get_template_content(filename):
    orgname = session.get('orgname', '')
    username = session.get('username', '')
    directory = os.path.join('data', 'user_docs', orgname, 'users', username, 'savedtemplatefiles')
    file_path = os.path.join(directory, filename)

    if not os.path.exists(file_path):
        return jsonify({"error": "File not found"}), 404

    html_content = docx_to_html(file_path,'')
    return ''.join(html_content)
