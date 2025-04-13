import json
import logging
import os
import re
from flask import Blueprint, Response, jsonify, make_response, request, stream_with_context, send_from_directory, send_file
from source.api.utilities import db_helper, externalapi_helper, queries
from source.api.utilities.constants import StreamEvent, PortKeyConfigs
from source.api.utilities.externalapi_helpers import auth_helper, chat_helper, chats_helper, popupbot_helper
from source.api.utilities.externalapi_helpers.admin_helper import create_organization
from source.api.utilities.externalapi_helpers.collections_helper import create_collection_helper
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.common import config
import uuid
from datetime import datetime
import bcrypt

popupbot = Blueprint('popupbot', __name__)

logger = logging.getLogger('app')


""" PENDING TODO
url_slug,
"""
@popupbot.route("/admin/users", methods=["POST"])
def create_user():
    try:
        # Extract user data from request JSON
        user_data = request.json
        if not user_data:
            return make_response(jsonify({"message": "Missing user data"}), 400)
        
        # Validate required fields
        required_fields = ["username", "first_name", "last_name", "email", "password"]
        for field in required_fields:
            if field not in user_data:
                return make_response(jsonify({"message": f"Missing required field: {field}"}), 400)
        
        # Check if username or email already exists
        existing_user = db_helper.find_one(queries.FIND_USER_BY_USERNAME, user_data["username"])
        if existing_user:
            return make_response(jsonify({"message": "Username already exists"}), 400)
        
        existing_email = db_helper.find_one(queries.FIND_USER_BY_EMAIL, user_data["email"])
        if existing_email:
            return make_response(jsonify({"message": "Email already exists"}), 400)
        
        # Hash the password
        hashed_password = bcrypt.hashpw(user_data["password"].encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        # Generate unique identifiers
        clientid = uuid.uuid4().hex
        url_slug = user_data["url_slug"] or user_data["username"]
        allowed_domains = user_data.get("allowed_domains", '["api.pwdev.internal.nlightnconsulting.com","chat.nlightnconsulting.com"]')
        
        # Insert user into database
        user_id = db_helper.execute_and_get_id(
            queries.INSERT_USER_2,
            user_data["username"],
            user_data["first_name"],
            user_data["last_name"],
            hashed_password,
            user_data["email"]
        )

        # Create default organization for the user
        org_name = f"{user_data['username']}_org"
        print(f"org_name: {org_name}, clientid: {clientid}, user_id: {user_id}")
        org_id = create_organization(org_name, clientid, user_id).get("org_id")

        # Add popupbot related entries to organization_popupbot table
        db_helper.execute(queries.INSERT_ORG_POPUPBOT_CONFIG, org_id, allowed_domains, url_slug, "sales")

        
        # Create default collections for the organization
        for collection_name in ["Content", "Sitemap", "Media"]:
            create_collection_helper(collection_name, f"Default {collection_name} collection", 10, org_id, False, user_id, 'file', '', '')
        
        # Return the created user data
        user_details = {
            "user_id": user_id,
            "username": user_data["username"],
            "first_name": user_data["first_name"],
            "last_name": user_data["last_name"],
            "email": user_data["email"],
            "clientid": clientid
        }
        
        return make_response(jsonify(user_details), 201)
        
    except Exception as e:
        logger.error(f"Error in create_user: {str(e)}")
        return make_response(jsonify({
            "message": "Failed to create user",
            "error": str(e)
        }), 500)

@popupbot.route('admin/sitemap', methods=['GET'])
@auth_helper.token_required
def get_sitemap():
    try:
        # 1. Get the user id (and username) from the token stored in request.context.
        user_id = request.context.get('user_id')
        username = request.args.get('username', '')
        if not user_id:
            return make_response(jsonify({"message": "User not found in context"}), 401)
        
        # 2. Find the organization for this user using the user_organization table.
        # Assumes queries.FIND_ORG_BY_USER_ID returns a record with keys "org_id" and "org_name".
        org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if not org:
            return make_response(jsonify({"message": "No organization found for this user"}), 404)
        org_id = org.get("org_id")
        org_name = org.get("org_name")
        
        # 3. Find the collection named "sitemap" for this organization.
        # Assumes queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID takes parameters (collection_name, org_id)
        sitemap_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Sitemap", org_id)
        if not sitemap_collection:
            return make_response(jsonify({"message": "No sitemap collection found for this organization"}), 404)
        collection_id = sitemap_collection.get("collection_id")
        
        # 4. Retrieve the files within that collection.
        # Assumes queries.FIND_FILES_BY_COLLECTION_ID returns a list of file records.
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID, collection_id, org_id)
        if not files:
            return make_response(jsonify({"message": "No sitemaps found for this organization"}), 404)
        
        # 5. Build the sitemap URL list.
        sitemap_urls = []
        for file in files:
            # Use the file_url if available; otherwise, build it from file_name.
            url = file.get("file_url")
            sitemap_urls.append(url)
        
        # 6. Return the sitemap list in JSON.
        return make_response(jsonify({
            "username": username,
            "sitemaps": sitemap_urls
        }), 200)
    
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/file', methods=['GET'])
@auth_helper.token_required
def get_file():
    try:
        # 1. Get the user id (and username) from the token stored in request.context.
        user_id = request.context.get('user_id')
        username = request.args.get('username', '')
        if not user_id:
            return make_response(jsonify({"message": "User not found in context"}), 401)
        
        # 2. Find the organization for this user using the user_organization table.
        # Assumes queries.FIND_ORG_BY_USER_ID returns a record with keys "org_id" and "org_name".
        org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if not org:
            return make_response(jsonify({"message": "No organization found for this user"}), 404)
        org_id = org.get("org_id")
        org_name = org.get("org_name")
        
        # 3. Find the collection named "files" for this organization.
        # Assumes queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID takes parameters (collection_name, org_id)
        files_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Content", org_id)
        if not files_collection:
            return make_response(jsonify({"message": "No files collection found for this organization"}), 404)
        collection_id = files_collection.get("collection_id")
        
        # 4. Retrieve the files within that collection.
        # Assumes queries.FIND_FILES_BY_COLLECTION_ID returns a list of file records.
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID, collection_id, org_id)
        if not files:
            return make_response(jsonify({"message": "No files found for this organization"}), 404)
        
        # 5. For each file, get details of description, training (boolean) and handout (boolean) from files_metadata table and then construct the file object for response
        file_details = []
        for file in files:
            # Assumes queries.FIND_FILE_METADATA_BY_FILE_ID returns a record with keys "description", "training", "handout".
            metadata = db_helper.find_one(queries.FIND_FILES_METADATA_BY_FILE_ID, file.get("file_id"))
            if not metadata:
                return make_response(jsonify({"message": "No metadata found for file"}), 404)
            file_details.append({
                "file_id": file.get("file_id"),
                "file_name": file.get("file_name"),
                "description": metadata.get("file_description"),
                "training": metadata.get("training"),
                "handout": metadata.get("handout"),
                "file_url": file.get("file_url")
            })
        
        # 6. Return the file details in JSON.
        return make_response(jsonify
        ({
            "files": file_details
        }), 200)
        
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/file', methods=['POST'])
@auth_helper.token_required
def post_file():
    try:
        logger.debug(f"Received form data: {request.form}")
        
        # Handle existingFiles which is sent as a JSON string array
        existing_files_str = request.form.get('existingFiles')
        if existing_files_str:
            try:
                # Parse the JSON string containing the array of files
                existing_files = json.loads(existing_files_str)
                
                # Process each file in the array
                for file in existing_files:
                    file_id = file.get('file_id')
                    training = file.get('training', 0)  # Default to 0 if not present
                    handout = file.get('handout', 0)    # Default to 0 if not present
                    description = file.get('file_description', '')  # Default to empty string
                    url = file.get('file_url')
                    
                    # Log the metadata being updated
                    logger.debug(f"Updating metadata for file {file_id}: training={training}, handout={handout}, description={description}")
                    
                    # Update the metadata in the database
                    db_helper.execute(queries.UPDATE_METADATA_IN_FILES_METADATA_BY_FILE_ID_2, 
                                     training, handout, description, file_id)
                
                logger.info(f"Updated metadata for {len(existing_files)} files")
            except json.JSONDecodeError as je:
                logger.error(f"Failed to parse existingFiles JSON: {je}")
                return make_response(jsonify({
                    "message": "Invalid JSON format for existingFiles",
                    "error": str(je)
                }), 400)
        
        # Handle new file uploads if any
        try:
            file_uploaded = externalapi_helper.file_upload_helper()
            if file_uploaded:
                return make_response(jsonify({
                    "message": "File uploaded successfully and details saved"
                }), 200)
            else:
                return make_response(jsonify({
                    "message": "File details saved but no new files were uploaded"
                }), 200)
        except Exception as e:
            logger.warning(f"File upload failed but metadata was saved: {str(e)}")
            return make_response(jsonify({
                "message": "File details saved, but file upload failed",
                "warning": str(e)
            }), 200)
            
    except Exception as e:
        logger.error(f"Error in post_file: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/mediauploads', methods=['GET'])
@auth_helper.token_required
def get_media():
    try:
        # 1. Get the user id (and username) from the token stored in request.context.
        username = request.args.get('username', '')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get("id")
        if not user_id:
            return make_response(jsonify({"message": "User not found in context"}), 401)
        
        # 2. Find the organization for this user using the user_organization table.
        # Assumes queries.FIND_ORG_BY_USER_ID returns a record with keys "org_id" and "org_name".
        org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if not org:
            return make_response(jsonify({"message": "No organization found for this user"}), 404)
        org_id = org.get("org_id")
        org_name = org.get("org_name")
        
        # 3. Find the collection named "files" for this organization.
        # Assumes queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID takes parameters (collection_name, org_id)
        files_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Media", org_id)
        if not files_collection:
            return make_response(jsonify({"message": "No files collection found for this organization"}), 404)
        collection_id = files_collection.get("collection_id")
        
        # 4. Retrieve the files within that collection.
        # Assumes queries.FIND_FILES_BY_COLLECTION_ID returns a list of file records.
        files = db_helper.find_many(queries.V2_FIND_FILES_BY_ORGANIZATION_ID_AND_COLLECTION_ID, collection_id, org_id)
        if not files:
            return make_response(jsonify({"message": "No files found for this organization"}), 404)
        
        # 5. For each file, get details of description, training (boolean) and handout (boolean) from files_metadata table and then construct the file object for response
        media_details = []
        for file in files:
            # Assumes queries.FIND_FILE_METADATA_BY_FILE_ID returns a record with keys "description", "training", "handout".
            metadata = db_helper.find_one(queries.FIND_FILES_METADATA_BY_FILE_ID, file.get("file_id"))
            if not metadata:
                return make_response(jsonify({"message": "No metadata found for file"}), 404)
            media_details.append({
                "file_id": file.get("file_id"),
                "url": file.get("file_url"),
                "description": metadata.get("file_description"),
            })
        
        # 6. Return the file details in JSON.
        return make_response(jsonify
        ({
            "media": media_details
        }), 200)
        
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/mediauploads', methods=['POST'])
@auth_helper.token_required
def insert_media():
    try:
        file_name = "media file"
        file_url = request.form.get('mediaurl')
        file_description = request.form.get('mediadesc', '')
        
        if not file_name or not file_url:
            return make_response(jsonify({"message": "Missing required file_name or file_url"}), 400)
        
        # Get user info and organization details
        username = request.form.get('username', '')
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get("id")
        org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if not org:
            return make_response(jsonify({"message": "No organization found for user"}), 404)
        org_id = org.get("org_id")
        
        # Find the collection to insert the file record. Here we assume "Content" collection.
        content_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Media", org_id)
        if not content_collection:
            return make_response(jsonify({"message": "No content collection found for the organization"}), 404)
        collection_id = content_collection.get("collection_id")
        
        # Insert into files table.
        # This query assumes the parameter order: file_name, an empty string (if applicable), collection_id and file_url.
        file_id = db_helper.execute_and_get_id(queries.V2_INSERT_FILE, file_name, '', collection_id, file_url)
        
        # Insert into files_metadata table.
        # Adjust the query and parameter order as needed.
        db_helper.execute(queries.INSERT_FILE_METADATA, file_id, file_name, file_description, 0, 0, 1)
        
        return make_response(jsonify({
            "message": "File and metadata inserted successfully",
            "file_id": file_id
        }), 200)
        
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong while inserting file.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/sitemap/post', methods=['GET'])
@auth_helper.token_required
def process_sitemap():
    logger.debug("Processing sitemap - before try")
    try:
        logger.info("Processing sitemap")
        logger.debug("Processing sitemap")
        sitemap_url = request.args.get('sitemap_url')
        username = request.args.get('username', '')
        if not sitemap_url or not username:
            return make_response(jsonify({"message": "Missing parameters"}), 400)
    
        return Response(stream_with_context(popupbot_helper.add_sitemap(sitemap_url, username)),
                        mimetype="text/event-stream")
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong in process_sitemap.",
            "error": str(e)
        }), 500)

@popupbot.route('admin/details', methods=['GET'])
@auth_helper.token_required
def get_details():
    try:
        username = request.args.get('username', '')
        #get user_id from username
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get("id")
        if not user_id:
            return make_response(jsonify({"message": "User not found in context"}), 401)
        
        org = db_helper.find_one(queries.FIND_ORG_ID_BY_USER_ID, user_id)
        if not org:
            return make_response(jsonify({"message": "No organization found for this user"}), 404)

        url_slug = db_helper.find_one(queries.FIND_URLSLUG_BY_ORG_ID, org.get("org_id")).get("url_slug")

        return make_response(jsonify({
            "username": username,
            "org_id": org.get("org_id"),
            "url_slug": url_slug,
        }), 200)
    
    except Exception as e:
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route('/js', methods=['GET'])
def get_popupbot_js():
    try:
        return send_from_directory('static/js', 'popupbot.js')
    except Exception as e:
        return make_response(jsonify({
            "message": "File not found.",
            "error": str(e)
        }), 404)

# Internal bot is scrapped in favour a simpler agentic bot within pw-webapp
@popupbot.route('/internal/js', methods=['GET'])
#need to add auth later
def get_popupbot_internal_js():
    try:
        return send_from_directory('static/js', 'popupbot_int.js')
    except Exception as e:
        return make_response(jsonify({
            "message": "File not found.",
            "error": str(e)
        }), 404)

@popupbot.route('/css', methods=['POST'])
def get_popupbot_css():
    try:
        return send_from_directory('static/styles', 'chat.css')
    except Exception as e:
        return make_response(jsonify({
            "message": "File not found.",
            "error": str(e)
        }), 404)

# Internal bot is scrapped in favour a simpler agentic bot within pw-webapp
@popupbot.route('internal/css', methods=['POST'])
#need to add auth later
def get_popupbot_css_internal():
    try:
        return send_from_directory('static/styles', 'chat_internal.css')
    except Exception as e:
        return make_response(jsonify({
            "message": "File not found.",
            "error": str(e)
        }), 404)

@popupbot.route("/visit", methods=["POST"])
def post_visit():
    try:
        # Extract clientid from posted form data.
        clientid = request.form.get("clientid")
        if not clientid:
            return make_response(jsonify({"message": "Missing clientid"}), 400)
        
        # Retrieve the user using a raw SQL query.
        # Assume queries.FIND_USER_BY_CLIENTID returns a row/dictionary for the user.
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, clientid)
        if not org:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)

        user_id = db_helper.find_one(queries.FIND_SUPERUSER_BY_ORG_ID, org.get("org_id"))
        if not user_id:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)

        """ # Get the IP address from X-Forwarded-For header.
        x_forwarded_for = request.headers.get("X-Forwarded-For")
        try:
            ip = x_forwarded_for.split(",")[0] if x_forwarded_for else "127.0.0.1"
        except Exception:
            ip = "127.0.0.1"
        
        user_details = {
            "user_id": user_id,
            "ip_address": ip,
            "user_agent": request.headers.get("user-agent"),
            "referer": request.headers.get("referer"),
            "host": request.headers.get("host")
        }
        
        # Log the visit.
        log_visit(user_details) """
        
        # Retrieve chatbot settings for the user using raw SQL.
        # Assume queries.FIND_CHATBOT_SETTINGS_BY_USER_ID returns a dictionary.
        """ chatbot_settings = db_helper.find_one(queries.FIND_CHATBOT_SETTINGS_BY_USER_ID, user_id)
        
        if chatbot_settings:
            logger.info(f"Chatbot settings found for user {user_id}")
            settings_response = {
                "chatwindow_size": {
                    "width": chatbot_settings.get("chatwindow_width"),
                    "height": chatbot_settings.get("chatwindow_height")
                },
                "chatwindow_position": {
                    "bottom": chatbot_settings.get("chatwindow_bottom_css"),
                    "right": chatbot_settings.get("chatwindow_right_css")
                },
                "icon_position": {
                    "bottom": chatbot_settings.get("icon_bottom_css"),
                    "right": chatbot_settings.get("icon_right_css")
                },
                "title": chatbot_settings.get("title_text"),
                "icon_url": chatbot_settings.get("icon_url"),
                "callout_text": chatbot_settings.get("callout_text"),
                "callout_delay": chatbot_settings.get("callout_delay"),
                "mode": chatbot_settings.get("mode")
            }
        else:
            logger.warning(f"No chatbot settings found for user {user_id}") """
        settings_response = {
            "chatwindow_size": {"width": "350px", "height": "500px"},
            "chatwindow_position": {"bottom": "20px", "right": "20px"},
            "title": "AI Chatbot",
            "icon_url": f"{config.STATIC_FILES_HOST}/static/images/ai-chat.png",
            "callout_text": "Click to speak!",
            "callout_delay": 3000,
            "mode": "Sales"
        }
        
        return jsonify(settings_response)
    
    except Exception as e:
        logger.error(f"Error in post_visit: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/text", methods=["POST"])
def post_text():
    try:
        # Retrieve form data
        user_query = request.form.get("user_query")
        clientid = request.form.get("clientid")
        thread_id = request.form.get("thread_id", None)
        selected_file_ids = request.form.get("selected_file_ids", None)

        #check if clientid is valid
        if not clientid:
            return make_response(jsonify({"message": "Missing clientid"}), 400)
        
        # Retrieve the user using a raw SQL query.
        # Assume queries.FIND_USER_BY_CLIENTID returns a row/dictionary for the user.
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, clientid)
        if not org:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        user_id = db_helper.find_one(queries.FIND_SUPERUSER_BY_ORG_ID, org.get("org_id")).get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=org.get("org_id"), module='POPUPBOT')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']
        user_chat_payload = dict(role='user', content=user_query)
        chats_helper.add_chat_history(thread_id, user_chat_payload)

        request.context = {"user_id": user_id, "organization_id": org.get("org_id"), "organization_name": org.get("org_name")}
        # Log incoming data for debugging (remove in production)
        logger.debug(f"{request.context}")

        handouts = popupbot_helper.get_handouts(org.get("org_id"), user_query, user_id)
        media = popupbot_helper.get_media(org.get("org_id"), user_query, user_id)
        collection_id = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Content", org.get("org_id")).get("collection_id")

        user_query = user_query + "\nHandouts: " + str(handouts) + "\nMedia: " + str(media)

        chat_mode = db_helper.find_one(queries.FIND_CHATMODE_BY_ORG_ID, org.get("org_id")).get("chat_mode")
        if chat_mode == "sales" or None:
            current_role = {
                                'role_name': 'Buyer',
                                'details': 'I am a buyer seeking info on the company website and need to be sold the Products or Services.',
                                'objectives': '1. Inform me of all the details\n2. After that collect my Contact info to contact me'
                            }
        else:
            current_role = {
                            'role_name': 'Information Seeker',
                            'details': 'I am a visitor seeking information.',
                            'objectives': '1. Inform me of all the details'
                        }
        user_query = f"{user_query}\n\nMy Role: {str(current_role)}\n"
        print("commencing chat query with params: ", user_query, collection_id, thread_id, selected_file_ids)
        chat_response = chat_helper.chat_query(user_query, collection_id, thread_id, selected_file_ids)
        for response in chat_response:
                # Parse the response string while preserving spaces
                event = None
                data = None
                for line in response.splitlines():
                    if line.startswith("event:"):
                        event = line[len("event:"):].strip()  # Remove trailing spaces only
                    elif line.startswith("data:"):
                        data = line.replace("data: ","")  # Remove trailing spaces only

                # Reformat the response and yield it
                if event == StreamEvent.FINAL_OUTPUT:
                    if data is not None:
                        data_json = json.loads(data)

        response_data = {
            "thread_id": data_json.get('thread_id'),
            "function": "chat",
            "ai_message": data_json.get('message'),
            "handouts": handouts,
            "media": media
        }
        assistant_chat_payload = dict(role='assistant', content=data_json.get('message'))
        chats_helper.add_chat_history(thread_id, assistant_chat_payload)
        #return Response(chat_response, content_type='text/event-stream')
        return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in /text endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

# Internal bot is scrapped in favour a simpler agentic bot within pw-webapp
@popupbot.route("internal/text", methods=["POST"])
#need to add auth later
def post_internal_text():
    try:
        # Retrieve form data
        user_query = request.form.get("user_query")
        clientid = request.form.get("clientid")
        thread_id = request.form.get("thread_id", None)
        collection_id = request.form.get("collection_id", None)
        selected_file_ids = request.form.get("selected_file_ids", None)

        #check if clientid is valid
        if not clientid:
            return make_response(jsonify({"message": "Missing clientid"}), 400)
        
        # Retrieve the user using a raw SQL query.
        # Assume queries.FIND_USER_BY_CLIENTID returns a row/dictionary for the user.
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, clientid)
        if not org:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        user_id = db_helper.find_one(queries.FIND_SUPERUSER_BY_ORG_ID, org.get("org_id")).get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)

        if not thread_id:
            thread_payload = dict(user_id=user_id, organization_id=org.get("org_id"), module='POPUPBOT')
            thread = chats_helper.create_thread(thread_payload)
            thread_id = thread['thread_id']
        user_chat_payload = dict(role='user', content=user_query)
        chats_helper.add_chat_history(thread_id, user_chat_payload)

        request.context = {"user_id": user_id, "organization_id": org.get("org_id"), "organization_name": org.get("org_name")}
        # Log incoming data for debugging (remove in production)
        logger.debug(f"{request.context}")

        handouts = []
        media = []

        if collection_id is None:
            collection_ids = db_helper.find_many(queries.V2_FIND_ALL_COLLECTIONS_BY_ORGANIZATION_ID, org.get("org_id"))
            
            # Create a list of collection objects instead of HTML
            collections_data = []
            for collection in collection_ids:
                collections_data.append({
                    "collection_id": collection.get("collection_id"),
                    "collection_name": collection.get("collection_name"),
                    "description": collection.get("description")
                })
            
            # Return a message and the collections data
            response_data = {
                "thread_id": thread_id,
                "function": "choose_collection",
                "ai_message": "Please choose a collection to continue.",
                "collections": collections_data,  # Add the collections as structured data
                "handouts": handouts,
                "media": media
            }
            return jsonify(response_data)    
        else: 
            print("commencing chat query with params: ", user_query, collection_id, thread_id, selected_file_ids)
            chat_response = chat_helper.chat_query(user_query, collection_id, thread_id, selected_file_ids)
            for response in chat_response:
                    # Parse the response string while preserving spaces
                    event = None
                    data = None
                    for line in response.splitlines():
                        if line.startswith("event:"):
                            event = line[len("event:"):].strip()  # Remove trailing spaces only
                        elif line.startswith("data:"):
                            data = line.replace("data: ","")  # Remove trailing spaces only

                    # Reformat the response and yield it
                    if event == StreamEvent.FINAL_OUTPUT:
                        if data is not None:
                            data_json = json.loads(data)

            response_data = {
                "thread_id": data_json.get('thread_id'),
                "function": "chat",
                "ai_message": data_json.get('message'),
                "handouts": handouts,
                "media": media
            }
            assistant_chat_payload = dict(role='assistant', content=data_json.get('message'))
            chats_helper.add_chat_history(thread_id, assistant_chat_payload)
            #return Response(chat_response, content_type='text/event-stream')
            return jsonify(response_data)

    except Exception as e:
        logger.error(f"Error in /text endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/voice", methods=["POST"])
def post_voice():
    try:
        # Check if audio file is in the request
        if 'file' not in request.files:
            return make_response(jsonify({"message": "No audio file uploaded"}), 400)
        
        audio_file = request.files['file']
        clientid = request.form.get("clientid")
        
        # Check if clientid is valid
        if not clientid:
            return make_response(jsonify({"message": "Missing clientid"}), 400)
        
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, clientid)
        if not org:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        user_id = db_helper.find_one(queries.FIND_SUPERUSER_BY_ORG_ID, org.get("org_id")).get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.POPUPBOT_01, use_portkey='False', base_url='https://api.openai.com/v1')
        # Process the audio file
        transcribed_text = openai_helper.voice2text(audio_file, user_id)
        
        # Return the transcribed text
        return jsonify({
            "user_message": transcribed_text
        })
        
    except Exception as e:
        logger.error(f"Error in /voice endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/chat", methods=["GET"])
def get_embed():
    try:
        # Get clientId from query string
        client_id = request.args.get('clientid', '')
        
        if not client_id:
            return make_response(jsonify({
                "message": "Missing clientid parameter"
            }), 400)
        
        # Check if the clientId is valid
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, client_id)
        if not org:
            return make_response(jsonify({
                "message": "Invalid clientid"
            }), 404)
        
        # Define the HTML template with the clientId replaced
        html_template = f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script>
    window.myScriptData = {{
        clientId: '{client_id}',
        API_BASE_URL: '{config.STATIC_FILES_HOST}'
    }};

    (function(w,d,s,f,js,fjs){{
        js=d.createElement(s);
        fjs=d.getElementsByTagName(s)[0];
        js.async=1;
        js.src=f;
        js.id='myWidgetScript';
        fjs.parentNode.insertBefore(js,fjs);
    }}(window,document,'script','{config.STATIC_FILES_HOST}/api/v2/popupbot/js'));
</script>
</head>

<body>
Click on the chat icon to start a conversation.
</body>
</html>
'''
        
        # Return the rendered HTML
        return Response(html_template, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"Error in /embed endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

# Internal bot is scrapped in favour a simpler agentic bot within pw-webapp
@popupbot.route("internal/chat", methods=["GET"])
#need to add auth later
def get_internal_embed():
    try:
        # If no user_id in context, fall back to client_id from query args
        client_id = request.args.get('clientid', '')
        
        if not client_id:
            return make_response(jsonify({
                "message": "Missing clientid parameter"
            }), 400)
        
        # Check if the clientId is valid
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, client_id)
        if not org:
            return make_response(jsonify({
                "message": "Invalid clientid"
            }), 404)

        html_template = f'''
<!DOCTYPE html>
<html>
<head>
<meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
<script>
    window.myScriptData = {{
        clientId: '{client_id}',
        API_BASE_URL: '{config.STATIC_FILES_HOST}'
    }};

    (function(w,d,s,f,js,fjs){{
        js=d.createElement(s);
        fjs=d.getElementsByTagName(s)[0];
        js.async=1;
        js.src=f;
        js.id='myWidgetScript';
        fjs.parentNode.insertBefore(js,fjs);
    }}(window,document,'script','{config.STATIC_FILES_HOST}/api/v2/popupbot/internal/js'));
</script>
</head>

<body>
<!-- <div id="login_wrapper" class="login_wrapper">
  <div class="login_card">
    <form id="login_form" class="login-form">
      <div class="form-item">
        <div class="form-control">
          <div class="input-group">
            <input type="text" id="username" placeholder="Username" required />
          </div>
        </div>
      </div>
      <div class="form-item">
        <div class="form-control">
          <div class="input-group">
            <input type="password" id="password" placeholder="Password" required />
          </div>
        </div>
      </div>
      <button type="submit" class="login-form-button primary-button">Log in</button>
    </form>
    <div class="divider">or</div>
    <button id="ms_login_button" class="login-form-button primary-button">MS 365 Log in</button>
  </div>
</div> -->
</body>
</html>
'''

        # Return the rendered HTML
        return Response(html_template, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"Error in /embed endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/download", methods=["POST"])
def download_file():
    try:        
        file_id = request.form.get('file_id')
        file_name = request.form.get('file_name')
        clientid = request.form.get("clientid")
        
        # Check if clientid is valid
        if not clientid:
            return make_response(jsonify({"message": "Missing clientid"}), 400)
        
        org = db_helper.find_one(queries.FIND_ORG_BY_CLIENTID, clientid)
        if not org:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        user_id = db_helper.find_one(queries.FIND_SUPERUSER_BY_ORG_ID, org.get("org_id")).get("user_id")
        if not user_id:
            return make_response(jsonify({"message": "Invalid clientid"}), 404)
        
        file_path = os.path.join(config.ORGDIR_PATH,org.get("org_name"),file_name)
        response = make_response(send_file(file_path, as_attachment=True))
        response.headers['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        return response
        
    except Exception as e:
        logger.error(f"Error in /download endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/bot/<url_slug>", methods=["GET"])
def bot_endpoint(url_slug):
    try:
        # Find organization by url_slug
        org_data = db_helper.find_one(queries.FIND_ORG_BY_URL_SLUG, url_slug)
        if not org_data:
            return make_response(jsonify({"message": "Organization not found"}), 404)
        
        # Get the client ID for the organization
        client_id = db_helper.find_one(queries.FIND_CLIENT_ID_BY_ORG_ID, org_data.get("org_id")).get("clientid")
        if not client_id:
            return make_response(jsonify({"message": "Client ID not found"}), 404)
        
        # Find the first page content for the organization (assuming you have a webpages table)
        # If you don't have an equivalent table structure, you can use a default empty string
        webpage_content = ""
        """ webpage_data = db_helper.find_one(queries.FIND_HOMEPAGE_BY_ORG_ID, org_data.get("org_id"))
        if webpage_data:
            webpage_content = webpage_data.get("content", "") """
        
        # Create the HTML content with the clientId replaced
        html_content = f"""
        <html>
        <head>
            <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no">
            <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
            <link href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/css/bootstrap.min.css" rel="stylesheet" integrity="sha384-QWTKZyjpPEjISv5WaRU9OFeRpok6YctnYmDr5pNlyT2bRjXh0JMhjY6hW+ALEwIH" crossorigin="anonymous">
        </head>
        <body>
            <div id="html-placeholder">{webpage_content}</div>
            <script>
                window.myScriptData = {{
                    clientId: '{client_id}',
                    API_BASE_URL: '{config.STATIC_FILES_HOST}'
                }};
            
                (function(w,d,s,f,js,fjs){{
                    js=d.createElement(s);
                    fjs=d.getElementsByTagName(s)[0];
                    js.async=1;
                    js.src=f;
                    js.id='myWidgetScript';
                    fjs.parentNode.insertBefore(js,fjs);
                }}(window,document,'script','{config.STATIC_FILES_HOST}/api/v2/popupbot/js'));
            </script>
            <script src="https://cdn.jsdelivr.net/npm/bootstrap@5.3.3/dist/js/bootstrap.bundle.min.js" integrity="sha384-YvpcrYf0tY3lHB60NNkmXc5s9fDVZLESaAA55NDzOxhy9GkcIdslK1eN7N6jIeHz" crossorigin="anonymous"></script>
        </body>
        </html>
        """
        
        # Return the HTML content
        return Response(html_content, mimetype='text/html')
        
    except Exception as e:
        logger.error(f"Error in bot_endpoint: {str(e)}")
        return make_response(jsonify({
            "message": "Oops! something went wrong.",
            "error": str(e)
        }), 500)

@popupbot.route("/admin/urlslug", methods=["POST"])
@auth_helper.token_required
def update_url_slug():
    try:
        # Extract data from request JSON
        request_data = request.json
        if not request_data:
            return make_response(jsonify({"message": "Missing request data"}), 400)
        
        url_slug = request_data.get("url_slug")
        username = request_data.get("username")
        
        # Validate required fields
        if not url_slug:
            return make_response(jsonify({"message": "Missing url_slug"}), 400)
        if not username:
            return make_response(jsonify({"message": "Missing username"}), 400)
        
        # Check if URL slug follows valid format
        if not re.match(r'^[a-zA-Z0-9_-]+$', url_slug):
            return make_response(jsonify({"message": "URL slug can only contain letters, numbers, underscores and hyphens"}), 400)
            
        # Check if URL slug is already in use (except by this user's org)
        existing_url_slug = db_helper.find_one(queries.FIND_ORG_BY_URL_SLUG, url_slug)
        user_id = db_helper.find_one(queries.FIND_USERID_BY_USERNAME, username).get("id")
        user_org = db_helper.find_one(queries.FIND_ORG_ID_BY_USER_ID, user_id)
        
        if existing_url_slug and existing_url_slug.get("org_id") != user_org.get("org_id"):
            return make_response(jsonify({"message": "URL slug already in use by another organization"}), 400)
        
        # Update URL slug in organization_popupbot table
        db_helper.execute(queries.UPDATE_URL_SLUG_BY_ORG_ID, url_slug, user_org.get("org_id"))
        
        return make_response(jsonify({
            "message": "URL slug updated successfully",
            "url_slug": url_slug,
            "bot_url": f"{config.STATIC_FILES_HOST}/api/v2/popupbot/bot/{url_slug}"
        }), 200)
        
    except Exception as e:
        logger.error(f"Error in update_url_slug: {str(e)}")
        return make_response(jsonify({
            "message": "Failed to update URL slug",
            "error": str(e)
        }), 500)