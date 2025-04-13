import json
import random
from flask import Blueprint, Response, jsonify, make_response, request
from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import auth_helper, jobs_helper, functions_hr_helper

functions = Blueprint('functions', __name__)

@functions.route('/hr/candidates', methods=['POST'])
@auth_helper.token_required
def add_candidates():
    try:
        # Extract form data
        job_id = request.form.get('job_id')

        if not job_id:
            return make_response(jsonify({'message': 'Invalid request', 'error': 'Missing required fields'}), 400)

        # Add candidate to the database
        candidate_id = functions_hr_helper.add_candidates(job_id)
        
        return make_response(jsonify({'candidate_id': candidate_id, 'message': 'CV uploaded successfully'}), 201)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

""" @functions.route('/hr/candidates/filter', methods=['GET'])
@auth_helper.token_required
def filter_candidates():
    try:
        # Extract form data
        filter_str = json.dumps(request.args.to_dict())

        # Add candidate to the database
        response = jobs_helper.get_job(58, filter_str)
        response = response.get('html_steps_data')
        response = response.get(3)
        file_ids = response.replace('json\n', '')
        
        return make_response(jsonify({'file_ids': file_ids, 'message': 'CVs filtered successfully'}), 201)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500) """

@functions.route('', methods=['GET'])
@auth_helper.token_required
def process_api():
    try:
        api_endpoint = request.args.get('api')
        #find the job which has the api_endpoint
        job = db_helper.find_one(queries.FIND_JOB_BY_API_ENDPOINT, api_endpoint)
        if not job:
            return make_response(jsonify({'message': f'API endpoint {api_endpoint} not found'}), 404)

        # Extract input_params after removing the querystring param 'api'
        input_params = request.args.to_dict()
        input_params.pop('api')
        input_params = json.dumps(input_params)

        # Add candidate to the database
        response = jobs_helper.get_job(job.get('id'),input_params)
        #find the value of html_steps_data and find the last item's value in that
        response = response.get('html_steps_data')
        response = response.get(len(response))

        return make_response(jsonify({'data': response, 'message': 'API executed successfully'}), 201)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)