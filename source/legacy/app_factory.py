import json
import logging
import os
import subprocess
import sys
import tempfile

import requests
from flask import Flask, request, jsonify, session, render_template, redirect, url_for, send_from_directory, \
    make_response
from flask.logging import default_handler
from flask_login import LoginManager, logout_user, login_user, login_required
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from requests_oauthlib import OAuth2Session

from source.common import config
from source.legacy import flask_config
from source.legacy.modules.docchat.docchat import docchat
from source.legacy.modules.docguide.docguide import docguide
from source.legacy.modules.esg.esg import esg
from source.legacy.modules.filewizard.filewizard import filewizard
from source.legacy.modules.procurement.procurement import procurement
from source.legacy.modules.raai.raai import raai
from source.legacy.utilities.helper_functions import get_user_by_username, User, api_v1_login_for_ssr, \
    api_v1_select_org, get_org_default_module_function, find_org_name, find_org_id, fetch_modules_by_org, \
    check_latest_chat_thread_id, get_old_chats_index, get_old_chat_logs_new, get_old_chats, userdocs_path, \
    chatname_edits, api_v1_get_file_list, get_files_for_collection_and_org, create_new_collection_with_org, \
    get_all_collections_for_org, update_file_collections, update_pinecone_vectors_metadata, get_old_chat_logs, \
    remove_query_string, get_collections_for_org, get_connection


def create_app():
    source_dir = os.path.join(os.getcwd(), 'source', 'api')

    app = Flask(
        __name__,
        template_folder=os.path.join(source_dir, 'templates'),
        static_folder=os.path.join(source_dir, 'static')
    )

    # Custom app logger that uses Flask's handler
    app_log_level = getattr(logging, os.getenv('APP_LOG_LEVEL', 'INFO').upper())

    app_logger = logging.getLogger('app')
    app_logger.setLevel(app_log_level)
    app_logger.addHandler(default_handler)

    # Set Flask's log level to APP_LOG_LEVEL as well
    app.logger.setLevel(app_log_level)

    app.config.from_object(flask_config.Config)

    app.url_map.strict_slashes = False

    app.json.sort_keys = False

    login_manager = LoginManager()
    login_manager.login_view = 'login_get'
    login_manager.init_app(app)

    @login_manager.user_loader
    def user_loader(username):
        if not get_user_by_username(username):
            return
        user = User()
        user.id = username
        return user

    @app.route('/login', methods=['GET'])
    def login_get():
        auth_methods = config.AUTH_METHODS_ALLOWED
        # print(auth_methods)
        if request.method == 'GET':
            session['login_stage'] = 'user_not_validated'
            return render_template('login.html', auth_methods=auth_methods)

    @app.route('/logout')
    def logout():
        logout_user()
        session.clear()
        session['oauth_token'] = ""
        session['username'] = ""
        return redirect(url_for('login_get'))

    app.register_blueprint(docchat)
    # app.register_blueprint(dataanalysis)
    app.register_blueprint(filewizard)
    app.register_blueprint(esg)
    app.register_blueprint(procurement)
    app.register_blueprint(docguide)
    app.register_blueprint(raai)

    # TODO: UNAUTHENTICATED! THIS NEEDS TO BE AUTHENTICATED
    @app.route('/static-files/<path:filename>')
    def serve_static_files(filename):
        try:
            # Use Flask's send_from_directory function to serve the static files
            return send_from_directory(f'{config.ORGDIR_PATH}/', filename)
        except Exception as e:
            print(e)
            return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

    orgfolder_path = config.ORGDIR_PATH
    insideorgfolder_path = config.ORGDIR_SUB_PATH

    # OAuth2 config
    client_id = config.MSAUTH_CLIENT_ID
    client_secret = config.MSAUTH_CLIENT_SECRET
    redirect_uri = config.MSAUTH_REDIRECT_URI
    authority = config.MSAUTH_AUTHORITY
    authorize_url = f"{authority}/oauth2/v2.0/authorize"
    token_url = f"{authority}/oauth2/v2.0/token"

    @app.route('/login', methods=['POST'])
    def login_post():
        login_json_str = api_v1_login_for_ssr()
        login_json = json.loads(login_json_str)
        if (login_json['render'] != ""):
            return render_template(login_json['render'], auth_methods=login_json['auth_methods'],
                                   message=login_json['message'], orgs=login_json['orgs'])
        else:
            return redirect(url_for(login_json['redirect']))

    @app.route('/selectorg', methods=['POST'])
    def select_org():
        login_json_str = api_v1_select_org()
        login_json = json.loads(login_json_str)
        if (login_json['render'] != ""):
            return render_template(login_json['render'], auth_methods=login_json['auth_methods'],
                                   message=login_json['message'], orgs=login_json['orgs'])
        else:
            return redirect(url_for(login_json['redirect']))

    @app.route('/loginms365')
    def msauth_login():
        if session.get('oauth_token') is None or session.get('oauth_token') == "":
            """Redirect to Microsoft login page."""
            microsoft = OAuth2Session(client_id, redirect_uri=redirect_uri,
                                      scope=['openid', 'email', 'profile', 'User.Read'])
            authorization_url, state = microsoft.authorization_url(authorize_url)

            # State is used to prevent CSRF, keep this for later.
            session['oauth_state'] = state
            session['oauth_token'] = ""
            return redirect(authorization_url)
        else:
            org_default_module_function = get_org_default_module_function(session['orgname'])
            if (org_default_module_function is None):
                return redirect(url_for('docchat_home'))
            else:
                return redirect(url_for(org_default_module_function))

    @app.route('/MS365callback')
    def msauth_callback():
        auth_methods = config.AUTH_METHODS_ALLOWED
        """Handle the callback from Microsoft."""
        # app.logger.debug("commencing MS365 callback")
        if session.get('oauth_token') is None or session.get('oauth_token') == "":
            microsoft = OAuth2Session(client_id, state=session['oauth_state'], redirect_uri=redirect_uri,
                                      scope=['openid', 'email', 'profile', 'User.Read'])
            token = microsoft.fetch_token(token_url, client_secret=client_secret,
                                          authorization_response=request.url)
            session['oauth_token'] = token

            # Fetch user's email ID
            user_info = microsoft.get('https://graph.microsoft.com/v1.0/me').json()
            email_id = user_info.get('mail')
            app.logger.debug(json.dumps(user_info))
            if not email_id:
                # Handle case where user is not found
                session['oauth_token'] = ""
                session['username'] = ""
                return redirect(url_for('login_get'))
            else:
                # Connect to MySQL and query for username
                connection = get_connection()
                with connection.cursor() as cursor:
                    query = "SELECT username FROM users WHERE email = %s"
                    cursor.execute(query, (email_id,))
                    result = cursor.fetchone()
                    connection.close()

                if result:
                    username = result[0]
                else:
                    # Handle case where user is not found
                    session['oauth_token'] = ""
                    session['username'] = ""
                    return redirect(url_for('login_get'))

        else:
            username = session.get('username', '')

        session['login_stage'] = 'user_validated'
        user = User()
        user.id = username
        login_user(user)
        session['username'] = username

        """ session['orgname'] = find_org_name(username)
        
    
        # Fetch modules for the organization
        org_id = find_org_id(session['orgname'])
        modules = fetch_modules_by_org(org_id)
        session['modules'] = modules  # Storing modules in session for easy access in other routes
    
        return redirect(url_for('docchat_home')) """

        orgs = find_org_name(username)
        if len(orgs) == 0:
            print("stage 3")
            session['login_stage'] = 'user_not_validated'
            return render_template('login.html', auth_methods=auth_methods,
                                   message="No Org assigned to User. Contact Site Admin.")
        elif len(orgs) == 1:
            print("stage 4")
            user = User()
            user.id = username
            login_user(user)

            session['orgname'] = orgs[0]
            # Fetch modules for the organization
            org_id = find_org_id(orgs[0])
            modules = fetch_modules_by_org(org_id)
            session['modules'] = modules  # Storing modules in session for easy access in other routes
            org_default_module_function = get_org_default_module_function(session['orgname'])
            if (org_default_module_function is None):
                return redirect(url_for('docchat_home'))
            else:
                return redirect(url_for(org_default_module_function))
        else:
            print("stage 5")
            return render_template('login.html', auth_methods=auth_methods, orgs=orgs)

    @app.route("/")
    @login_required
    def docchat_home():
        """ orgname = session.get('orgname', '')
        username = session.get('username', '') """
        session['newchat'] = '0'
        latest_chat_thread_id = request.args.get("f", None)
        # check if the latestchatthreadid on the querystring f= is valid, else will lead to junk value entering the DB
        if (check_latest_chat_thread_id(latest_chat_thread_id) is not True):
            latest_chat_thread_id = None

        old_chats = get_old_chats_index()
        old_chat_logs, old_chat_ids, module, collection, metadata_array_str = get_old_chat_logs_new(
            latest_chat_thread_id)
        print(f"metadata str is {metadata_array_str}")

        load_popup_script = []
        metatadata_present = []

        i = 0
        for item in metadata_array_str:
            item_json = []
            print(f"item in metadata is {item}. item_json len is {len(item_json)}")
            if (item != "" and item != "[]"):
                item_json = json.loads(item)  # Parse the JSON string
            if len(item_json) > 0:
                metatadata_present.append(1)
                load_popup_script.append('loadSeeReferencePopup(' + item + ', \'' + old_chat_ids[i] + '\');\n')
            else:
                metatadata_present.append(0)
            """ else:
                load_popup_script.append("") """
            i = i + 1

        return render_template(
            'docchat.html',
            active_page='/',
            old_chats=old_chats,
            # current_file=current_file,
            latest_chat_thread_id=latest_chat_thread_id,
            old_chat_logs=old_chat_logs,
            old_chat_ids=old_chat_ids,
            type=module,
            collection=collection,
            modules=session.get('modules', []),
            # load_popup_ids = load_popup_ids,
            load_popup_script=load_popup_script,
            metatadata_present=metatadata_present,
            imgpathprefix='https://demo.nlightnconsulting.com/static/images/card-header-img'
        )

    @app.route("/newchat", methods=['POST'])
    @login_required
    def new_chat():
        orgname = session.get('orgname', '')
        username = session.get('username', '')

        current_file = "new_chat"
        old_chats = get_old_chats_index()
        old_chats.append([current_file, current_file])
        # set_latestchatthreadid(current_file)
        session['newchat'] = '1'

        return render_template(
            'docchat.html',
            active_page='/newchat',
            old_chats=old_chats,
            current_file=current_file,
            new_chat='yes',
            type='docchat',
            modules=session.get('modules', []),
            imgpathprefix='https://demo.nlightnconsulting.com/static/images/card-header-img'
        )

    @app.route("/newdataanalysis", methods=['POST'])
    @login_required
    def new_data_analysis():
        old_chats = get_old_chats()
        current_chat_path = os.path.join(userdocs_path, session.get('orgname', ''), 'users',
                                         session.get('username', ''),
                                         'currentchat')
        current_file = "new_chat"
        old_chats.append([current_file, chatname_edits(current_file)])
        # Open the 'currentchat' file and overwrite its content with the value in 'current_file'
        with open(current_chat_path, 'w') as file:  # 'w' mode will overwrite the file
            file.write(current_file)
        return render_template('dataanalysis.html', active_page='/newdataanalysis', old_chats=old_chats,
                               current_file=current_file, new_chat='yes', type='dataanalysis',
                               modules=session.get('modules', []))

    @app.route("/docupload")
    @login_required
    def index3():
        module = request.args.get('type')
        old_chats = get_old_chats_index()
        return render_template('docupload.html', active_page='/docupload/' + module, old_chats=old_chats, type=module,
                               modules=session.get('modules', []))

    @app.route("/filelist", methods=['POST'])  # only used in datanalysis
    @login_required
    def run_script_filelist():
        data = request.get_json()
        module = data["type"]
        orgname = session.get('orgname', '')
        dir_path = os.path.join(userdocs_path, orgname, 'files', module)

        output = []

        if os.path.exists(dir_path):
            for filename in os.listdir(dir_path):
                output.append({
                    "filename": filename,
                    "collection": module  # Assuming the module is the collection
                })

        return jsonify({"result": output})

    @app.route("/filelist2", methods=['POST'])
    @login_required
    def run_script_filelist2():
        response = api_v1_get_file_list()
        return jsonify(response)

    @app.route("/justfilelist2", methods=['POST'])
    @login_required
    def run_script_justfilelist2():
        foldername = request.form.get('collection')
        orgname = session.get('orgname', '')

        # Get the list of files for the specified collection (folder) and organization (orgname)
        output = get_files_for_collection_and_org(foldername, orgname)

        return jsonify({"result": output})

    @app.route("/filelist2unprocessed",
               methods=['POST'])  # legacy route, not used any more as indexing handled by vectoriser
    @login_required
    def run_script_filelist2_unprocessed():
        data = request.get_json()
        module = data["type"]
        orgname = session.get('orgname', '')
        # base_path = os.path.join('data', 'user_docs', orgname, 'files', 'docchat2')
        # folders_path = os.path.join(base_path, 'folders')
        folders_path = os.path.join(orgfolder_path, orgname, insideorgfolder_path)
        output = []

        if os.path.exists(folders_path):
            for collection in os.listdir(folders_path):
                folder_path = os.path.join(folders_path, collection, 'unprocessed')
                if os.path.isdir(folder_path):
                    for file in os.listdir(folder_path):
                        output.append({
                            "filename": file,
                            "collection": collection
                        })

        return jsonify({"result": output})

    @app.route("/folderlist", methods=['POST'])  # only used for dataanalysis
    @login_required
    def run_script_folderlist():
        data = request.get_json()
        module = data["type"]
        orgname = session.get('orgname', '')
        file_path = os.path.join(userdocs_path, orgname, 'files', 'categories.txt')
        output = []

        if os.path.exists(file_path):
            with open(file_path, 'r') as f:
                data = json.load(f)
                for item in data:
                    output.append({
                        "collection": item.get('name', 'No collection')
                    })

        return jsonify({"result": output})

    @app.route("/folderlist2", methods=['POST'])
    @login_required
    def run_script_folderlist2():
        orgname = session.get('orgname', '')

        # Get collections for the org_id
        collections = get_collections_for_org(orgname)

        return jsonify({"result": collections})

    @app.route("/docupload", methods=['POST'])  # only used for dataanalysis
    @login_required
    def doc_upload():
        module = request.form["type"]
        orgname = session.get('orgname', '')
        cur_dir = os.path.dirname(os.path.realpath(__file__))

        # Check whether a file or a URL is being uploaded
        if 'file' in request.files:
            # Save the uploaded file in the data/unprocessed folder
            file = request.files['file']
            folder_name = os.path.join(userdocs_path, orgname, 'files', module)
            os.makedirs(folder_name, exist_ok=True)
            file_path = os.path.join(folder_name, file.filename)
            file.save(file_path)
        elif 'url' in request.form:
            # Download the content from the URL and save it to the data/unprocessed folder
            url = request.form['url']
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": "Failed to download the file from the provided URL."}), 400
            file_content = response.content
            file_name = os.path.basename(url)
            folder_name = os.path.join(userdocs_path, orgname, 'files', module)
            os.makedirs(folder_name, exist_ok=True)
            with open(os.path.join(folder_name, file_name), 'wb') as f:
                f.write(file_content)
        else:
            return jsonify({"error": "Either a file or a URL must be provided."}), 400

        return jsonify({
            "result": "1. Doc submitted to server. \n2.Refresh this page after 1-2 hours time. \n3. You can use it once it appears in the list below."})

    @app.route("/docupload2", methods=['POST'])
    @login_required
    def doc_upload2():
        module = request.form["type"]
        collection = request.form["collection"]
        orgname = session.get('orgname', '')
        cur_dir = os.path.dirname(os.path.realpath(__file__))

        files_path = os.path.join(orgfolder_path, orgname)
        if not os.path.exists(files_path):
            os.makedirs(files_path)

        # Check whether a file or a URL is being uploaded
        if 'file' in request.files:
            # Save the uploaded file in the data/unprocessed folder
            file = request.files['file']
            file_name = file.filename
            current_saved_file_path = os.path.join(files_path, file_name)
            file.save(current_saved_file_path)
        elif 'url' in request.form:
            # Download the content from the URL and save it to the data/unprocessed folder
            url = request.form['url']
            url = remove_query_string(url)
            response = requests.get(url)
            if response.status_code != 200:
                return jsonify({"error": "Failed to download the file from the provided URL."}), 400
            file_content = response.content
            file_name = os.path.basename(url)
            current_saved_file_path = os.path.join(files_path, file_name)
            with open(current_saved_file_path, 'wb') as f:
                f.write(file_content)
        else:
            return jsonify({"error": "Either a file or a URL must be provided."}), 400

        return jsonify({
            "result": "File submitted to server. <br>Please Refresh page after 10-12mins and check in the list below. If not appearing below, inform Support team or email: info@nlightn.in",
            "status": "success", "filename": file_name})

    @app.route("/dataanalysis", methods=['POST'])
    @login_required
    def dataanalysis_msg_post_script():
        orgname = session.get('orgname', '')
        username = session.get('username', '')
        data = request.get_json()
        user_text = data["user_text"]
        module = data["type"]
        dataanalysis_filename = data["dataanalysis_filename"]
        # user_fileselected = data["file_selected"]
        user_files_selected = json.dumps(data["file_selected"])
        # now 'user_text' holds the user input

        cur_dir = os.path.dirname(os.path.realpath(__file__))
        venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        # venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
        venv_python = sys.executable  # Use the current Python interpreter

        current_chat_folder_path = os.path.join(userdocs_path, session.get('orgname', ''), 'users',
                                                session.get('username', ''))
        old_chat_logs, type_temp, dataanalysis_file_temp, folder_temp, metadata_array_str = get_old_chat_logs(
            current_chat_folder_path)
        if type_temp != "":
            module = type_temp
        if dataanalysis_file_temp != "":
            dataanalysis_filename = dataanalysis_file_temp
        if folder_temp != '':
            collection = folder_temp
        old_chat_logs_string = json.dumps(old_chat_logs)
        result = subprocess.run(
            [venv_python, 'dataanalysis.py', user_text, user_files_selected, orgname, userdocs_path, username,
             old_chat_logs_string, module, dataanalysis_filename],
            stdout=subprocess.PIPE
        )
        encoding = 'UTF-8'  # 'windows-1252' if sys.platform == 'win32' else 'utf-8'
        output = result.stdout.decode(encoding, errors="ignore")
        return jsonify(output)

    @app.route("/extfiles/<filename>")
    @login_required
    def run_script_extfiles(filename):
        return send_from_directory('extfiles', filename)

    @app.route('/addfolder', methods=['POST'])  # only used for dataanalysis
    @login_required
    def add_folder():
        # Get orgname from session
        orgname = session.get('orgname')
        if not orgname:
            return jsonify({"error": "orgname not found in session"}), 400

        # Open the categories.txt file
        filepath = os.path.join('data', 'user_docs', orgname, 'files', 'categories.txt')

        # Check if file exists
        if not os.path.exists(filepath):
            # Create the directories leading to the file if they don't exist
            os.makedirs(os.path.dirname(filepath), exist_ok=True)

            # Create the categories.txt file with an empty list
            with open(filepath, 'w') as file:
                json.dump([], file)

        """ if not os.path.exists(filepath):
            return jsonify({"error": "categories.txt file not found"}), 400 """

        # Load the existing folders
        with open(filepath, 'r') as file:
            folders = json.load(file)

        # Get the new collection details from the request
        new_folder = request.json
        folders.append(new_folder)

        # Save the updated folders list back to the file
        with open(filepath, 'w') as file:
            json.dump(folders, file)

        # Get the list of collection names
        folder_names = [d['name'] for d in folders]

        # Return the list of folder names to the client
        return jsonify(folder_names)

    @app.route('/addfolder2', methods=['POST'])
    @login_required
    def add_folder2():
        try:
            orgname = session.get('orgname', None)
            if not orgname:
                raise ValueError("Organization name is missing in the session")

            data = request.get_json()
            folder_name = data['name']
            folder_description = data['description']

            # Create the new collection and link it to the organization
            create_new_collection_with_org(folder_name, folder_description, orgname)

            # Get all collections for the organization
            collections = get_all_collections_for_org(orgname)

            return jsonify(collections)
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/api', methods=['POST'])
    def run_api_script():
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
        username = session.get('username', '')

        data = request.json
        function_name = data.get('function_name', None) if data else None
        parameter1 = data.get('parameter1', None) if data else None
        parameter2 = data.get('parameter2', None) if data else None
        parameter3 = data.get('parameter3', None) if data else None
        input_data = data.get('data', None) if data else None
        # Write data to a temporary file
        with tempfile.NamedTemporaryFile(delete=False, mode='w', suffix='.json') as tmp_file:
            json.dump(input_data, tmp_file)
            tmp_file_path = tmp_file.name

        if not function_name:
            return jsonify({"error": "No function specified"}), 400

        # Ensure only alphanumeric characters are in the function name for security
        if not function_name.isalnum():
            return jsonify({"error": "Invalid function name"}), 400

        script_path = os.path.join('source/api/api/', f'{function_name}.py')

        # Check if the script exists
        if not os.path.isfile(script_path):
            return jsonify({"error": "Script not found"}), 404

        try:
            # Execute the script and capture the output
            command = [venv_python, script_path, username, tmp_file_path]

            # Append parameter1 and parameter2 to the command only if they are not None
            if parameter1 is not None:
                command.append(parameter1)
            if parameter2 is not None:
                command.append(parameter2)
            if parameter3 is not None:
                command.append(parameter3)

            result = subprocess.check_output(command, text=True)
            return jsonify({"output": result.strip()}), 200
        except subprocess.CalledProcessError as e:
            # Handle errors in script execution
            return jsonify({"error": "Script execution failed", "details": str(e)}), 500

    """ @app.route('/callai', methods=['POST'])
    def callai1():
        prompt = request.form['prompt']
        query = request.form['query']
        cur_dir = os.path.dirname(os.path.realpath(__file__))
        venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        venv_python = os.path.join(cur_dir, 'venv', venv_dir, 'python')
        result = subprocess.run(
            [venv_python, 'callai.py', prompt, query],
            stdout=subprocess.PIPE
        )
        #encoding = 'UTF-8' #'windows-1252' if sys.platform == 'win32' else 'utf-8'
        #output = result.stdout.decode(encoding)      
        #return jsonify(output)
        return result.stdout """

    # Load client secrets from a file.
    CLIENT_SECRETS_FILE = "./client_secret_174608231730-gbvlfk19nrd1sqds69gurfdvs90o5obm.apps.googleusercontent.com.json"
    # This scope allows for full read/write access to the authenticated user's account.
    SCOPES = ['https://www.googleapis.com/auth/drive']

    @app.route('/gdrivetest', methods=['GET'])
    @login_required
    def gdrivetest():
        # Create flow instance to manage the OAuth 2.0 Authorization Grant Flow steps.
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES,
            redirect_uri="https://28c6-137-59-78-123.ngrok-free.app/oauth2callback")

        authorization_url, state = flow.authorization_url(
            access_type='offline',
            include_granted_scopes='true')

        # Store the state in the session for later use in the callback.
        session['state'] = state

        return redirect(authorization_url)

    @app.route('/oauth2callback')
    def oauth2callback():
        # state = session['state']
        state = request.args.get('state')
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE, scopes=SCOPES, state=state,
            redirect_uri=url_for('oauth2callback', _external=True))

        flow.fetch_token(authorization_response=request.url)

        credentials = flow.credentials

        # Initialize Google Drive API client
        drive_service = build('drive', 'v3', credentials=credentials)

        # Example: List files in Drive
        results = drive_service.files().list(
            pageSize=10, fields="nextPageToken, files(id, name)").execute()
        items = results.get('files', [])

        if not items:
            return 'No files found.'
        else:
            output = 'Files:<br>'
            for item in items:
                output += f"{item['name']} ({item['id']})<br>"
            return output

    @app.route('/sync_files', methods=['POST'])
    @login_required
    def sync_files():
        try:
            env = os.environ.copy()
            env['OPENAI_API_KEY'] = config.OPENAI_API_KEY
            # os.chdir(os.path.join("..","pw-vectoriser"))
            vectoriser_dir = config.vectoriser_dir
            venv_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
            venv_python = os.path.join(vectoriser_dir, 'venv', venv_dir, 'python')
            result = subprocess.run(
                [venv_python, os.path.join(vectoriser_dir, "index_files_pinecone.py", )], env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT
            )
            # os.chdir("../pw-api")  # Change to your actual Flask app directory
            return  # result.stdout.decode('utf-8')
        except Exception as e:
            return str(e)

    @app.route('/docdelete')
    @login_required
    def doc_delete():
        module = request.args.get('type')
        # Retrieve or define your list of filenames
        return render_template('docdelete.html', active_page='/docupload/docchat', type=module,
                               modules=session.get('modules', []))

    @app.route('/doccollectionchange')
    @login_required
    def doc_collectionchange():
        # Retrieve or define your list of filenames
        return render_template('doccollectionchange.html', active_page='/docupload/docchat',
                               modules=session.get('modules', []))

    @app.route('/docdelete', methods=['POST'])
    def delete_file():
        orgname = session.get('orgname', '')
        selected_filenames = request.form.getlist('filenames[]')
        selected_collectionname = request.form.get('collectionname')

        # Pinecone vector deletion is being handled by vectoriser+watcher process and so not needed here
        # only file delete is needed here

        """ # Initialize Pinecone
        api_key = config.pinecone_api_key
        pinecone.init(api_key=api_key, environment=config.pinecone_environment)
        # Connect to your Pinecone index
        index_name = config.pinecone_index_name
        index = pinecone.Index(index_name)
    
        #app.logger.debug("Files selected: " + str(selected_filenames))
    
        for filename in selected_filenames:  
            # Specify the filename to search for
            target_filename = filename
            app.logger.debug(orgname, selected_collectionname, filename)
            # Query to find vector IDs with the specified filename in metadata
            query_result = index.query(
                vector= [0] * 1536, # embedding dimension
                filter={"orgname": {"$eq":orgname}, "collection": {"$eq":selected_collectionname}, "filename": {"$eq": target_filename}},
                top_k=500
            )
            app.logger.debug("stage 1")
            # Extract vector IDs from the query result
            vector_ids_to_delete = [match["id"] for match in query_result["matches"]]
    
            # Delete vectors by ID
            if vector_ids_to_delete:
                index.delete(ids=vector_ids_to_delete)
                # Move processed file to the processed folder
                folders_path = os.path.join(orgfolder_path,orgname,insideorgfolder_path)
                file_path = os.path.join(folders_path, selected_foldername, 'processed',target_filename)
                # Check if the file already exists
                if os.path.exists(file_path):
                    os.remove(file_path)  # Remove the existing file
            app.logger.debug("stage 2")
    
        # Close the connection
        index.close() """

        for filename in selected_filenames:
            folders_path = os.path.join(orgfolder_path, orgname)
            file_path = os.path.join(folders_path, filename)
            if os.path.exists(file_path):
                os.remove(file_path)  # Remove the existing file

        return jsonify({"result": "File(s) deleted. <br>Please Refresh page after few mins to check."})

    @app.route('/modifycollections', methods=['POST'])
    @login_required
    def modify_collections():
        orgname = session.get('orgname', '')
        try:
            selected_files = request.form.getlist('filenames[]')
            new_collection_name = request.form['newcollectionname']

            # Update collections for the selected files
            update_file_collections(orgname, selected_files, new_collection_name)

            # update pinecone vectors for these files to reflect new Collection in metadata
            update_pinecone_vectors_metadata(selected_files, orgname, new_collection_name)

            return jsonify({'status': 'success', 'message': 'Collections updated successfully'})
        except Exception as e:
            return jsonify({'status': 'error', 'message': str(e)})

    def format_response_to_html(formatted_res):
        """
        Convert the formatted response into an HTML table.

        :param formatted_res: List of dictionaries representing the formatted response.
        :return: A string containing the HTML representation of the data.
        """
        # Start the HTML table
        html_table = '<table style="border-collapse: collapse; width: 100%;">'

        # Add the header row
        headers = formatted_res[0].keys() if formatted_res else []
        html_table += '<tr style="background-color: #f2f2f2;">'
        for header in headers:
            html_table += f'<th style="border: 1px solid #ddd; padding: 8px; text-align: left;">{header.capitalize()}</th>'
        html_table += '</tr>'

        # Add the data rows
        for item in formatted_res:
            html_table += '<tr>'
            for value in item.values():
                html_table += f'<td style="border: 1px solid #ddd; padding: 8px;">{value}</td>'
            html_table += '</tr>'

        # Close the table
        html_table += '</table>'

        return html_table

        # route for seeing all pinecone orgs, files, collections for admin

    @app.route('/pineconeviewer', methods=['GET'])
    def pineconeviewer():
        # Check for the API key in the request header
        api_key = request.args.get('token')
        orgname = request.args.get('orgname')
        if api_key != config.PINECONE_VIEWER_TOKEN:
            # If the API key is not correct, return a 401 Unauthorized response
            return jsonify({'status': 'error', 'message': 'Unauthorized'}), 401
        try:
            from pinecone import Pinecone

            # initialize connection to pinecone (get API key at app.pinecone.io)
            pc = Pinecone(
                api_key=config.PINECONE_API_KEY
            )
            # print("Pinecone initialised: " + datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S") + "<br>")

            # connect to index
            index = pc.Index(config.PINECONE_INDEX_NAME)
            print(index)
            # Perform the query
            res = index.query(vector=[0] * 1536, filter={"orgname": {"$eq": orgname}}, top_k=10000,
                              include_metadata=True, include_values=False)

            formatted_res = []
            seen = set()

            for match in res['matches']:
                item = {
                    "orgname": match['metadata']['orgname'],
                    "collection": match['metadata']['collection'],
                    "filename": match['metadata']['filename']
                }

                # Convert the dictionary to a tuple to make it hashable for set operations
                item_tuple = tuple(item.items())
                if item_tuple not in seen:
                    seen.add(item_tuple)
                    formatted_res.append(item)

            return format_response_to_html(formatted_res)
        except Exception as error:
            return f"Error querying Pinecone Index: {error}"

    @app.route('/testapi/<filename>', methods=['GET'])
    def testapi(filename):
        return render_template(filename)

    return app
