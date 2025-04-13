import json
import random
from flask import Blueprint, Response, jsonify, make_response, request
from source.api.utilities import db_helper, queries
from source.api.utilities.externalapi_helpers import auth_helper

entities = Blueprint('entities', __name__)

# GET - Retrieve multiple entities
@entities.route('/<entity_type>/<username>', methods=['GET'])
@auth_helper.token_required
def get_entities(entity_type, username):
    try:
        # Example: Query to retrieve all entities of a specific type
        entity_list = db_helper.find_many(
            queries.V2_FIND_ENTITIES_BY_TYPE_USERNAME, entity_type, username
        )
        return jsonify({'data': entity_list}), 200
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

# POST - Create a new entity
@entities.route('/<entity_type>', methods=['POST'])
@auth_helper.token_required
def create_entity(entity_type):
    try:
        data = request.get_json()
        if not data:
            raise RuntimeError("Invalid input. No data provided.")
        #insert a ticket_number field with a random large number as the value
        data['ticket_number'] = random.randint(1000000000, 9999999999)
        data_str = json.dumps(data)
        # Example query to insert a new entity
        db_helper.execute(
            queries.INSERT_ENTITY, entity_type, data_str
        )
        return jsonify({'message': f'{entity_type} created successfully.'}), 201
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

# PUT - Update an existing entity
@entities.route('/<entity_type>/<entity_id>', methods=['PUT'])
@auth_helper.token_required
def update_entity(entity_type, entity_id):
    try:
        data = request.get_json()
        if not data:
            raise RuntimeError("Invalid input. No data provided.")

        # Example query to update an entity
        db_helper.find_many(
            queries.UPDATE_ENTITY, [entity_id, entity_type, data]
        )
        return jsonify({'message': f'{entity_type} updated successfully.'}), 200
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

# DELETE - Delete an entity
@entities.route('/<entity_type>/<entity_id>', methods=['DELETE'])
@auth_helper.token_required
def delete_entity(entity_type, entity_id):
    try:
        # Example query to delete an entity
        db_helper.find_many(
            queries.DELETE_ENTITY, [entity_id, entity_type]
        )
        return jsonify({'message': f'{entity_type} deleted successfully.'}), 200
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 500)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)

@entities.route('/entity_configuration', methods=['GET'])
def get_entity_configuration():
    entity_type = request.args.get('type')
    if not entity_type:
        return jsonify({'error': 'Entity type is required'}), 400
    config = db_helper.find_one(queries.GET_ENTITY_CONFIGURATION, [entity_type])
    return jsonify({'data': config}), 200
