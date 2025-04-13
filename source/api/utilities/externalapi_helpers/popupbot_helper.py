from datetime import datetime
import json
import logging
import os
import time
from bs4 import BeautifulSoup
import pdfkit
import requests
import xml.etree.ElementTree as ET
from flask import request
from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
from source.common import config
from urllib.parse import quote
from fake_useragent import UserAgent

logger = logging.getLogger('app')

def add_sitemap(sitemap_url, username):
    """
    Generator function that:
      1. Fetches and parses the sitemap XML.
      2. Inserts an entry for the sitemap URL in the Sitemap collection.
      3. For each URL in the sitemap, converts the page to PDF, saves it in the "Content" collection,
         and makes a corresponding file entry.
      4. Yields progress updates as Server-Sent Events.
    """
    logger.info("Initiating sitemap processing")
    logger.debug("Initiating sitemap processing")
    session = requests.Session()
    session.headers.update({
        'Accept': 'application/xml, text/xml, */*; q=0.01',
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3'
    })
    
    try:
        # 1. Get user info from token (using request.context set by auth_helper.token_required)
        user_id = request.context.get('user_id')
        if not user_id:
            yield f"data: {json.dumps({'error': 'User not found in context'})}\n\n"
            return
        
        # 2. Fetch the organization via user_organization table.
        org = db_helper.find_one(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
        if not org:
            yield f"data: {json.dumps({'error': 'No organization found for user'})}\n\n"
            return
        org_id = org.get("org_id")
        org_name = org.get("org_name")
        
        # 3. Find the Sitemap collection for this organization.
        sitemap_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Sitemap", org_id)
        if not sitemap_collection:
            yield f"data: {json.dumps({'error': 'No sitemap collection found for this organization'})}\n\n"
            return
        sitemap_collection_id = sitemap_collection.get("collection_id")
        
        # 4. Insert the sitemap URL into the files table for the Sitemap collection.
        # Here we assume INSERT_SITEMAP_FILE query takes parameters: collection_id, file_name, file_url, created_at
        sitemap_file_name = "sitemap_" + datetime.utcnow().strftime("%Y%m%d%H%M%S") + ".xml"
        db_helper.execute(queries.V2_INSERT_FILE, sitemap_file_name, '', sitemap_collection_id,sitemap_url)
        yield f"data: {json.dumps({'status': 'sitemap_entry_created', 'msg': 'Sitemap URL entry created'})}\n\n"
        
        # 5. Fetch and parse the sitemap.
        try:
            sitemap_response = session.get(sitemap_url)
            sitemap_response.raise_for_status()
            sitemap_xml = ET.fromstring(sitemap_response.content)
        except Exception as e:
            yield f"data: {json.dumps({'error': f'Failed to fetch sitemap: {str(e)}'})}\n\n"
            return
        
        # Namespace for sitemap if needed.
        namespaces = {'ns': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
        urls = [elem.text for elem in sitemap_xml.findall('.//ns:loc', namespaces)]
        url_list = [{"url": url, "processed": False} for url in urls]
        yield f"data: {json.dumps({'status': 'full_list', 'list': url_list, 'msg': '', 'waiting': '1'})}\n\n"
        
        # 6. For each URL in the sitemap, fetch and convert to PDF, then insert into Content collection.
        # Find the Content collection for this organization.
        content_collection = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Content", org_id)
        if not content_collection:
            yield f"data: {json.dumps({'error': 'No Content collection found for this organization'})}\n\n"
            return
        content_collection_id = content_collection.get("collection_id")
        
        options = {
            # Basic options that should work with most wkhtmltopdf versions
            'quiet': None,
            'print-media-type': None,
            'javascript-delay': '10000',  # Wait for JavaScript (note using string)
            'no-stop-slow-scripts': None,
            'encoding': 'UTF-8',
            
            # Image and quality settings
            'image-quality': '100',
            
            # Error handling
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore',
            
            # User agent
            'custom-header': [
                ('User-Agent', 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/108.0.0.0 Safari/537.36')
            ]
            
            # Removed incompatible options:
            # 'window-size': '1280,1024'
            # 'quality': 100
            # 'enable-javascript': None
            # 'enable-local-file-access': None
            # 'enable-smart-shrinking': None
            # 'disable-external-links': None
            # 'disable-internal-links': None
            # 'no-background': None
        }
        page_count = 0
        output_folder_path = os.path.join(config.ORGDIR_PATH, quote(org_name))
        os.makedirs(output_folder_path, exist_ok=True)
        output_tempfolder_path = os.path.join(config.ORGFILES_BASE_DIR, quote(org_name))
        os.makedirs(output_tempfolder_path, exist_ok=True)

        # Debian-compatible options
        debian_options = {
            'quiet': '',
            'encoding': 'UTF-8',
            'disable-javascript': '',
            'disable-smart-shrinking': '',
            'no-background': '',
            'load-error-handling': 'ignore',
            'load-media-error-handling': 'ignore'
        }
        for page_url in urls:
            try:
                #page_response = session.get(page_url)
                #page_response.raise_for_status()
                page_response = get_request(url=page_url)
                
                webpage_name = get_webpage_name(page_url) + "_"
                # Convert the fetched webpage to PDF using pdfkit.
                pdf_filename = "webpage_" + webpage_name + datetime.utcnow().strftime("%Y%m%d%H%M%S") + ".pdf"
                output_path = os.path.join(output_folder_path, pdf_filename)
                
                #pdfkit.from_url(page_url, output_path, options=options)
                #html_content = page_response.text

                # Use BeautifulSoup to parse the HTML and extract text content
                soup = BeautifulSoup(page_response.content, 'html.parser')
                text_content = soup.get_text()

                html_path = os.path.join(output_tempfolder_path, f"temp_{webpage_name}.html")
                
                with open(html_path, 'w', encoding='utf-8') as f:
                    f.write(f"<html><body><pre>{text_content}</pre></body></html>")
                
                try:
                    pdfkit.from_file(html_path, output_path, verbose=True, options=debian_options)
                except Exception as pdf_error:
                    logger.warning(f"Error converting HTML to PDF: {pdf_error}. Falling back to URL method.")
                    # Fallback to URL method
                    #pdfkit.from_url(page_url, output_path, options=options)
                finally:
                    # Clean up temporary HTML file
                    if os.path.exists(html_path):
                        os.remove(html_path)
                
                # Build a file URL (adjust according to your static files hosting)
                file_url = f"{config.STATIC_FILES_PREFIX}/{org_name}/{quote(pdf_filename)}"
                
                # Insert entry into files table for the Content collection.
                db_helper.execute(queries.V2_INSERT_FILE, pdf_filename, '', content_collection_id,file_url)
                
                # Mark this page as processed.
                for item in url_list:
                    if item["url"] == page_url:
                        item["processed"] = True
                        break
                
                yield f"data: {json.dumps({'status': 'completed_items', 'list': url_list, 'msg': f'Page processed: {page_url}', 'waiting': '1'})}\n\n"
                page_count += 1
                if page_count >= 100:  #cutting off at 100 pages for now
                    break
            except Exception as e:
                # Log or yield an update message for failed pages
                yield f"data: {json.dumps({'status': 'error', 'msg': f'Failed: {page_url}', 'error': str(e)})}\n\n"
        
        final_result = {"status": "completed", 'list': url_list, 'msg': 'Sitemap uploaded successfully', 'waiting': '0'}
        yield f"data: {json.dumps(final_result)}\n\n"
    except Exception as e:
        yield f"data: {json.dumps({'status': 'error', 'msg': 'Unexpected error', 'error': str(e)})}\n\n"

def get_request(url, params=None, cookies=None, max_retries=2):
    headers = {
            'user-agent': UserAgent().random,
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
            'accept-language': 'en-IN,en-GB;q=0.9,en-US;q=0.8,en;q=0.7,hi;q=0.6,de;q=0.5',
            'priority': 'u=0, i',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'document',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-site': 'same-origin',
            'sec-fetch-user': '?1',
            'upgrade-insecure-requests': '1',
        }

    for attempt in range(1, max_retries + 1):
        try:
            response = requests.get(url, params=params, headers=headers, cookies=cookies, timeout=30)
            
            if response.status_code == 200:
                return response
            else:
                print(f"Attempt {attempt}: Failed with status code {response.status_code}")
        except requests.RequestException as e:
            print(f"Attempt {attempt}: Request failed due to {e}")

        if attempt < max_retries:
            time.sleep(2)  # Add a delay before retrying
    
    print("Max retries reached. Request failed.")
    return None

def get_webpage_name(page_url):
    # Extract a meaningful name from the URL
    url_parts = page_url.rstrip('/').split('/')
    if url_parts[-1]:  # If there's text after the last slash
        webpage_name = url_parts[-1]
    else:
        # If URL ends with slash, take the second-to-last segment
        for i in range(len(url_parts)-1, -1, -1):
            if url_parts[i]:  # Find the first non-empty segment going backwards
                webpage_name = url_parts[i]
                break
        else:
            # Fallback if no meaningful segments are found
            webpage_name = "index"
    return webpage_name

def log_visit(user_details):
    """
    Synchronous function to log the visit.
    For example, it might execute an INSERT query using db_helper.execute.
    """
    try:
        # Example raw SQL query execution.
        db_helper.execute(queries.INSERT_VISIT, 
                          user_details["user_id"],
                          user_details["ip_address"],
                          user_details["user_agent"],
                          user_details["referer"],
                          user_details["host"])
    except Exception as e:
        logger.error(f"Error logging visit: {e}")
    
def get_handouts(org_id, user_query, user_id):
    collection_id = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Content", org_id).get("collection_id")
    files = db_helper.find_many(queries.V2_FIND_FILE_DETAILS_BY_COLLECTION_ID, collection_id)
    handout_list = []
    for file in files:
        if file.get("handout"):
            handout_list.append({
                "file_id": file.get("file_id"),
                "file_name": file.get("file_name"),
                "file_description": file.get("file_description")
            })
   
    openai_helper = OpenAIHelper()
    response = json.loads(openai_helper.callai_json(
            system_content = f""" Your task is to identify the relevant handouts from the User query.
            User query:
            {user_query}
            Return the output as a JSON in the following format: 
            {{"handouts": [{{'file_id': <file_id>, 'file_name': <file_name>}}]}}
            Handouts available:
            {handout_list}
            """,
            user_content='',
            extra_context=[],
            user_id=user_id
        ))
        # Parse the response to get the new insight query
    handout_list = response.get('handouts', [])
    return handout_list

def get_media(org_id, user_query, user_id):
    collection_id = db_helper.find_one(queries.FIND_COLLECTIONS_BY_NAME_AND_ORG_ID, "Media", org_id).get("collection_id")
    files = db_helper.find_many(queries.V2_FIND_FILE_DETAILS_BY_COLLECTION_ID, collection_id)
    media_list = []
    for file in files:
        if file.get("media"):
            media_list.append({
                "file_id": file.get("file_id"),
                "file_name": file.get("file_name"),
                "file_url": file.get("file_url"),
                "file_description": file.get("file_description")
            })
   
    openai_helper = OpenAIHelper()
    response = json.loads(openai_helper.callai_json(
            system_content = f""" Your task is to identify the relevant media from the User query.
            User query:
            {user_query}
            Return the output as a JSON in the following format: 
            {{"media": [{{'file_id': <file_id>, 'file_name': <file_name>, 'file_url': <file_url>}}]}}
            Media available:
            {media_list}
            """,
            user_content='',
            extra_context=[],
            user_id=user_id
        ))
        # Parse the response to get the new insight query
    media_list = response.get('media', [])
    return media_list