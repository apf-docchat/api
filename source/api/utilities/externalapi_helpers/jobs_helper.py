import json
import logging
import os
from urllib.parse import quote
import uuid

import urllib

from flask import request

from source.api.utilities import db_helper, queries
from source.api.utilities.constants import PortKeyConfigs, StreamEvent
from source.api.utilities.externalapi_helpers import agent_helper
from source.common import config
from source.api.utilities.externalapi_helpers.openai_helper import OpenAIHelper
import re

logger = logging.getLogger('app')

# Job related functions - BEGIN

def get_jobs_list():
    try:
        logger.debug("@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@@commencing get jobs list...")
        if 'organization_id' not in request.context:
            #raise RuntimeError('Organization Id is required!')
            user_id = request.context['user_id']
            logger.debug(f"Organization ID not found in context. Fetching organizations for user ID: {user_id}")
            organizations = db_helper.find_many(queries.FIND_ORGANIZATION_BY_USER_ID, user_id)
            if not organizations:
                raise RuntimeError('No organizations found for the user!')

            all_jobs = []
            for org in organizations:
                organization_id = org.get('org_id')
                orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
                jobs_list = db_helper.find_many(queries.FIND_JOBS_LIST_BY_ORG_ID, organization_id)
                #jobs_list = db_helper.find_many(queries.FIND_JOBS_LIST_BY_ORG_ID, organization_id)
                if not jobs_list:
                    continue
                i = 0
                for job in jobs_list:
                    file_path_uuid = job.get('file_path_uuid')
                    folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
                    steps = job.get('steps')
                    steps = json.loads(steps)
                    html_steps_data = {}
                    image_steps_data = {}
                    for step in steps:
                        #step = json.loads(step)
                        step_id = step.get('id')
                        html_file_path = f"{folder_path}/{step_id}_html"
                        image_file_path = f"{folder_path}/{step_id}_image"
                        if os.path.exists(html_file_path):
                            with open(html_file_path) as f:
                                html_steps_data[step_id] = f.read()
                        if os.path.exists(image_file_path):
                            with open(image_file_path) as f:
                                image_steps_data[step_id] = f.read()
                    jobs_list[i]['html_steps_data'] = html_steps_data
                    jobs_list[i]['image_steps_data'] = image_steps_data
                    i += 1
                all_jobs.extend(jobs_list)
            print("completed looping through all jobs")
            return all_jobs
        else:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
            user_id = request.context['user_id']
            collection_id = request.args.get('collection_id') or None
            jobs_list = []
            if collection_id is not None:
                jobs_list = db_helper.find_many(queries.FIND_JOBS_LIST_BY_COLLECTION_ID, collection_id, organization_id)
            else:
                jobs_list = db_helper.find_many(queries.FIND_JOBS_LIST_BY_ORG_ID, organization_id)
            if not jobs_list:
                jobs_list = []
            i = 0
            for job in jobs_list:
                file_path_uuid = job.get('file_path_uuid')
                folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
                steps = job.get('steps')
                steps = json.loads(steps)
                html_steps_data = {}
                image_steps_data = {}
                for step in steps:
                    #step = json.loads(step)
                    step_id = step.get('id')
                    html_file_path = f"{folder_path}/{step_id}_html"
                    image_file_path = f"{folder_path}/{step_id}_image"
                    if os.path.exists(html_file_path):
                        with open(html_file_path) as f:
                            html_steps_data[step_id] = f.read()
                    if os.path.exists(image_file_path):
                        with open(image_file_path) as f:
                            image_steps_data[step_id] = f.read()
                jobs_list[i]['html_steps_data'] = html_steps_data
                jobs_list[i]['image_steps_data'] = image_steps_data
                i += 1
            print("completed looping through all jobs")
            return jobs_list
    except Exception as e:
        logger.error(e)
        raise e

#get job function: to run a job with input files etc and send back results
""" def get_job(id, input_params=None):
    try:
        user_id = request.context['user_id']
        job = db_helper.find_one(queries.FIND_JOB_BY_ID, id)
        print(job)

        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job.get('job_collection_id')
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')
        
        
        response_json = {}
        #iterate for each step in job.steps. find the collection_id, use the prompt field as query and load the control_flow list as: {"steps": [{"user_query": step.prompt, "file_category": step.file_category}]. Then call chat_query with collection id 
        steps = json.loads(job.get('steps') or "[]")
        manager = agent_helper.AgentManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.thread_id = ''
        previous_step_output = ''
        last_step = False

        file_path_uuid = job.get('file_path_uuid')
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        os.makedirs(folder_path, exist_ok=True)
        #delete all old files in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            # Check if it is a file and delete it
            if os.path.isfile(file_path):
                os.remove(file_path)

        html_steps_data = {}
        image_steps_data = {}
        for step in steps:
            if step == steps[-1]:
                last_step = True

            print(f"!!!!!!!!!!!!!!!!!!!!!!!!!!!!!Step ID: {step.get('id')}!!!!!!!!Input Params: {input_params}")
            step_prompt = step.get('prompt').replace('$input_params', input_params or '')
            print(step)
        
            manager.query = f"
                Previous Step Output:
                {previous_step_output}
                Query:
                {step_prompt}
                {step.get('output_format')}
            "
            print(f"##############################################Query: {manager.query}")
            manager.collection_id = job.get('job_collection_id')

            if step.get('selected_file_ids') is not None and step.get('selected_file_ids') != []:
                manager.selected_file_ids = step.get('selected_file_ids')

            manager.fetch_query_data()
            manager.fetch_previous_chat_history()
            manager.add_user_chat_history()
            manager.control_sequence={"steps": [{"user_query": manager.query, "file_category": step.get('file_category')}]}
            chat_response = manager.init_chat_query()
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
                    else:
                        data_json = {}

                    if last_step:
                        if data_json.get('image_data') is not None:
                            response_json = dict(order_number=job.get('order_number'), title=job.get('title'), steps=job.get('steps'), query=job.get('query'), job_collection_id=job.get('job_collection_id'), file_path_uuid=job.get('file_path_uuid'), api_endpoint=job.get('api_endpoint'))
                        else:
                            response_json = dict(order_number=job.get('order_number'), title=job.get('title'), steps=job.get('steps'), query=job.get('query'), job_collection_id=job.get('job_collection_id'), file_path_uuid=job.get('file_path_uuid'), api_endpoint=job.get('api_endpoint'))
                    else:
                        previous_step_output = data
                        print(f"##################: {previous_step_output}")

                    #store intermediate results as files & add to html_data and image_data array variables for each step
                    file_name = step.get('id')
                    file_data = data_json['message'].strip('\n')
                    htmlfile_path = f"{folder_path}/{file_name}_html"
                    with open(htmlfile_path, 'w') as file:
                        file.write(file_data)
                    html_steps_data[step.get('id')] = file_data

                    if data_json.get('image_data') is not None:
                        image_data = data_json['image_data']
                        image_path = f"{folder_path}/{file_name}_image"
                        with open(image_path, 'wb') as image_file:
                            image_file.write(image_data)
                        image_steps_data[step.get('id')] = image_data

                    #upload file to s3
                    #s3_helper.upload_file(file_path, file_name)
                    #remove file from local
                    #os.remove(file_path)
        response_json['html_steps_data'] = html_steps_data
        if not image_steps_data == {}:
            response_json['image_steps_data'] = image_steps_data
        logger.info(f"Final response JSON: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error in get_job: {str(e)}", exc_info=True)
        raise e """

def get_job(id, input_params=None):
    try:
        user_id = request.context['user_id']
        job = db_helper.find_one(queries.FIND_JOB_BY_ID, id)
        if not job:
            raise RuntimeError('Job not found!')

        # Determine organization details
        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job.get('job_collection_id')
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')

        # Prepare folder for storing intermediate results
        file_path_uuid = job.get('file_path_uuid')
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        os.makedirs(folder_path, exist_ok=True)

        # Delete all old files in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            if os.path.isfile(file_path):
                os.remove(file_path)

        # Process each step using get_step
        steps = json.loads(job.get('steps') or "[]")
        html_steps_data = {}
        image_steps_data = {}
        previous_step_output = ''

        for step in steps:
            step_id = step.get('id')
            # Call get_step for each step
            step_response = get_step(id, step_id, input_params)

            # Collect HTML and image data from the step response
            html_steps_data.update(step_response.get('html_steps_data', {}))
            image_steps_data.update(step_response.get('image_steps_data', {}))

            # Update previous_step_output for the next step
            previous_step_output = step_response.get('html_steps_data', {}).get(step_id, '')

        # Prepare the final response JSON
        response_json = {
            'order_number': job.get('order_number'),
            'title': job.get('title'),
            'steps': job.get('steps'),
            'query': job.get('query'),
            'job_collection_id': job.get('job_collection_id'),
            'file_path_uuid': job.get('file_path_uuid'),
            'api_endpoint': job.get('api_endpoint'),
            'html_steps_data': html_steps_data
        }

        if image_steps_data:
            response_json['image_steps_data'] = image_steps_data

        logger.info(f"Final response JSON: {response_json}")
        return response_json

    except Exception as e:
        logger.error(f"Error in get_job: {str(e)}", exc_info=True)
        raise e

def get_steps_html_output(steps, folder_path):
    html_steps_data = {}
    for step in steps:
        file_name = step.get('id')
        file_path = f"{folder_path}/{file_name}_html"
        try:
            with open(file_path, 'r') as file:
                file_data = file.read()
            html_steps_data[step.get('id')] = file_data
        except Exception as e:
            html_steps_data[step.get('id')] = ''
    return html_steps_data

def get_steps_image_output(steps, folder_path):
    image_steps_data = {}
    for step in steps:
        file_name = step.get('id')
        file_path = f"{folder_path}/{file_name}_image"
        try:
            with open(file_path, 'rb') as image_file:
                image_data = image_file.read()
            image_steps_data[step.get('id')] = image_data
        except Exception as e:
            image_steps_data[step.get('id')] = ''
    return image_steps_data

def get_step(job_id, step_id, input_params=None):
    try:
        user_id = request.context['user_id']
        job = db_helper.find_one(queries.FIND_JOB_BY_ID, job_id)

        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job.get('job_collection_id')
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')
        
        response_json = {}
        #iterate for each step in job.steps. find the collection_id, use the prompt field as query and load the control_flow list as: {"steps": [{"user_query": step.prompt, "file_category": step.file_category}]. Then call chat_query with collection id 
        steps = json.loads(job.get('steps') or "[]")
        #load the element of dict with key step_id from steps to step
        step = next((item for item in steps if item["id"] == int(step_id)), None)

        manager = agent_helper.AgentManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.thread_id = ''

        file_path_uuid = job.get('file_path_uuid')
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        file_path = f"{folder_path}/{step_id}_html"
        os.makedirs(folder_path, exist_ok=True)
        if os.path.exists(file_path):
            os.remove(file_path)

        html_steps_data = get_steps_html_output(steps, folder_path)
        image_steps_data = get_steps_image_output(steps, folder_path)


        previous_step_id = int(step_id) - 1
        #read the contents of file with name f"{previous_step_id}_html" from the folder_path as previous_step_output
        if (previous_step_id > 0):
            try:
                prev_file_path = f"{folder_path}/{previous_step_id}_html"
                with open(prev_file_path, 'r') as file:
                    previous_step_output = file.read()
            except Exception as e:
                previous_step_output = ''
        else:
            previous_step_output = ''
        manager.previous_step_output = previous_step_output

        # Parse input_params as JSON if it exists
        input_params_dict = {}
        if input_params:
            try:
                # Parse JSON string into dictionary
                input_params_dict = json.loads(input_params)
            except json.JSONDecodeError as e:
                logger.warning(f"Error parsing input_params as JSON: {str(e)}")
                # Fallback to trying as a string value if JSON parsing fails
                input_params_dict = {"value": input_params}
        
        # First process placeholder replacements for specific parameters
        step_prompt = step.get('prompt')
        param_matches = re.findall(r'\$input_params\.(\w+)', step_prompt)
        for param in param_matches:
            if param in input_params_dict:
                step_prompt = step_prompt.replace(f'$input_params.{param}', str(input_params_dict[param]))
                print(f"@@@@@@@@@@@@@@@$input_params.{param} replaced with {input_params_dict[param]}")
        
        # Then handle the general $input_params placeholder if it still exists
        step_prompt = step_prompt.replace('$input_params', input_params or '')

        manager.query = f"""
{step_prompt}
output_format: {step.get('output_format')}
        """
        print(f"##############################################Query: {manager.query}")
        manager.collection_id = job.get('job_collection_id')

        if step.get('selected_file_ids') is not None and step.get('selected_file_ids') != []:
            manager.selected_file_ids = step.get('selected_file_ids')

        manager.fetch_query_data()
        manager.fetch_previous_chat_history()
        manager.add_user_chat_history()
        manager.control_sequence={"steps": [{"user_query": manager.query, "file_category": step.get('file_category'), "tool_id": step.get('tool_id', '')}]}
        chat_response = manager.init_chat_query()
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
            if (event == StreamEvent.FINAL_OUTPUT):
                if data is not None:
                    data_json = json.loads(data)
                else:
                    data_json = {}

                if data_json.get('image_data') is not None:
                    response_json = dict(order_number=job.get('order_number'), title=job.get('title'), steps=job.get('steps'), query=job.get('query'), job_collection_id=job.get('job_collection_id'), file_path_uuid=job.get('file_path_uuid'), api_endpoint=job.get('api_endpoint'))
                else:
                    response_json = dict(order_number=job.get('order_number'), title=job.get('title'), steps=job.get('steps'), query=job.get('query'), job_collection_id=job.get('job_collection_id'), file_path_uuid=job.get('file_path_uuid'), api_endpoint=job.get('api_endpoint'))

                #store intermediate results as files & add to html_data and image_data array variables for each step
                file_name = step.get('id')
                file_data = data_json['message'].strip('\n')
                htmlfile_path = f"{folder_path}/{file_name}_html"
                with open(htmlfile_path, 'w') as file:
                    file.write(file_data)
                html_steps_data[step.get('id')] = file_data

                if data_json.get('image_data') is not None:
                    image_data = data_json['image_data']
                    image_path = f"{folder_path}/{file_name}_image"
                    with open(image_path, 'wb') as image_file:
                        image_file.write(image_data)
                    image_steps_data[step.get('id')] = image_data

                #upload file to s3
                #s3_helper.upload_file(file_path, file_name)
                #remove file from local
                #os.remove(file_path)

        response_json['html_steps_data'] = html_steps_data
        if not image_steps_data == {}:
            response_json['image_steps_data'] = image_steps_data
        logger.info(f"Final response JSON: {response_json}")
        return response_json
    except Exception as e:
        logger.error(f"Error in get_job: {str(e)}", exc_info=True)
        raise e

def add_job():
    try:
        user_id = request.context['user_id']
        data = request.get_json()
        username = data.get('username')
        job_collection_id = data.get('job_collection_id')
        query = ''
        file_path_uuid = str(uuid.uuid4())

        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job_collection_id
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')

        if not username:
            raise RuntimeError('Username is required!')
        #steps = request.context['steps']
        max_order_number = db_helper.find_one(queries.FIND_JOBS_LARGEST_ORDER_NUMBER, organization_id).get('max_order_number')
        if max_order_number is None:
            order_number = 1
        else:
            order_number = max_order_number+1
        #default_step_data = json.dumps([{"id":1,"step_type":"","collection_id":'',"file_category":"","prompt":"","output_format":""}])
        default_step_data = json.dumps([])
        new_job_id = db_helper.execute_and_get_id(queries.INSERT_JOB,f"Agent {order_number}", order_number, username, organization_id, default_step_data, job_collection_id, query, file_path_uuid)
        new_job = db_helper.find_one(queries.FIND_JOB_BY_ID, new_job_id)
        #set the default_api_endpoint to /functions/{new_job_id}
        api_endpoint = f"/{new_job_id}"
        updated_job_id = db_helper.execute_and_get_id(queries.UPDATE_JOB_API_ENDPOINT, api_endpoint, new_job_id)

        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        os.makedirs(folder_path, exist_ok=True)

        response_json = dict(order_number=new_job.get('order_number'), title=new_job.get('title'), steps=new_job.get('steps'), id=new_job.get('id'), job_collection_id=job_collection_id, query=query, file_path_uuid=file_path_uuid, api_endpoint=api_endpoint)
        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def create_steps(id):
    #TODO: Once decide_control_flow is modified to suggest tools in Steps rather than file_category, make appropriate changes here too in tandem
    try:
        user_id = request.context['user_id']
        data = request.get_json()
        username = data.get('username')
        job_collection_id = request.json.get('job_collection_id')
        query = request.json.get('query')
        api_endpoint = request.json.get('api_endpoint')
        job = db_helper.find_one(queries.FIND_JOB_BY_ID, id)

        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job_collection_id
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')

        file_path_uuid = job.get('file_path_uuid')
        #delete the files in the uuid folder
        folder_path = f"{config.ORGFILES_BASE_DIR}/{orgname}/{file_path_uuid}"
        # Loop through all the files in the folder
        for file_name in os.listdir(folder_path):
            file_path = os.path.join(folder_path, file_name)
            # Check if it is a file and delete it
            if os.path.isfile(file_path):
                os.remove(file_path)

        #get a new title appropriate to new query
        #new_title = get_query_title(query, user_id)
        #new_title = 'My Job'
        
        response_json = []
        #iterate for each step in job.steps. find the collection_id, use the prompt field as query and load the control_flow list as: {"steps": [{"user_query": step.prompt, "file_category": step.file_category}]. Then call chat_query with collection id 
        manager = agent_helper.AgentManager()
        manager.organization_id = organization_id
        manager.orgname = orgname
        manager.user_id = user_id
        manager.thread_id = ''
        previous_step_output = ''
        manager.query = query
        manager.collection_id = job_collection_id
        manager.fetch_query_data()
        manager.decide_control_flow()
        control_flow_steps = manager.control_sequence['steps']

        steps = []
        i = 1
        for step in control_flow_steps:
            steps.append({"id":i,"step_type":"","file_category":step.get('file_category'),"prompt":step.get('user_query'),"output_format":"share in html format"})
            i += 1

        response_json = dict(order_number=job.get('order_number'), title=job.get('title'), job_collection_id=job_collection_id, query=query, steps=steps, id=job.get('id'), file_path_uuid=file_path_uuid, api_endpoint=job.get('api_endpoint'))
        updated_job_id = db_helper.execute_and_get_id(queries.UPDATE_JOB_STEPS_QUERY, json.dumps(steps), username, query, job_collection_id, api_endpoint, job.get('id'))
        return response_json
    except Exception as e:
        logger.error(e)
        raise e

def update_job(id):
    try:
        user_id = request.context['user_id']
        username = request.json.get('username')
        steps = request.json.get('steps')
        api_endpoint = request.json.get('api_endpoint')
        job_collection_id = request.json.get('job_collection_id')

        if 'organization_id' in request.context:
            organization_id = request.context['organization_id']
            orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        else:
            collection_id = job_collection_id
            organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_COLLECTION_ID, collection_id)
            organization_id = organization.get('org_id')
            orgname = organization.get('org_name')


        #get a new title appropriate to new query
        #new_title = get_query_title(query, user_id)
        #new_title = 'My Job'
        updated_job_id = db_helper.execute_and_get_id(queries.UPDATE_JOB_STEPS, steps, username, api_endpoint, job_collection_id, id)
        updated_job = db_helper.find_one(queries.FIND_JOB_BY_ID, id)
        return updated_job
    except Exception as e:
        logger.error(e)
        raise e
    
""" def update_step(job_id, step_id):
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context['organization_id']
        orgname = db_helper.find_one(queries.FIND_ORG_NAME_BY_ORG_ID, organization_id).get('org_name')
        user_id = request.context['user_id']
        data = request.get_json()
        username = data.get('username')
        step = data.get('step')

        #get a new title appropriate to new query
        #new_title = get_query_title(query, user_id)
        #new_title = 'My Job'
        #get the the steps array from the job and update the step with the step_id
        job = db_helper.find_one(queries.FIND_JOB_BY_ID, job_id)
        steps = json.loads(job.get('steps'))
        for i in range(len(steps)):
            if steps[i].get('id') == json.loads(step).get('id'):
                steps[i] = json.loads(step)
                break
        steps_json = json.dumps(steps)
        updated_job_id = db_helper.execute_and_get_id(queries.UPDATE_JOB_STEPS, steps_json, username, job_id)
        updated_job = db_helper.find_one(queries.FIND_JOB_BY_ID, job_id)
        return updated_job
    except Exception as e:
        logger.error(e)
        raise e """

def delete_job(id, username):
    try:
        db_helper.execute_and_get_id(queries.DELETE_JOB, username, id)
        return f"Job with id {id} deleted successfully"
    except Exception as e:
        logger.error(e)
        raise e

""" def get_query_title(query, user_id):
    try:
        # Call AI to identify get new title
        openai_helper = OpenAIHelper(portkey_config=PortKeyConfigs.DEFAULT_GPT4o)
        response = json.loads(openai_helper.callai_json(
            system_content="For the english language query given by the user give an appropriate 2-3 word title. Return the output as a JSON in the following format: {'title': <appropriate 2-3 word title for this job>}",
            user_content=query,
            user_id=user_id
        ))
        #print(response)
        return response['title']
    except Exception as e:
        logger.error(e)
        raise e """

# Job related functions - END