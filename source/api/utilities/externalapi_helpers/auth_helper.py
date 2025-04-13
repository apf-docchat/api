import logging
import os
from datetime import datetime, timedelta

import bcrypt
import jwt
from flask import request
from requests_oauthlib import OAuth2Session

from source.api.utilities import db_helper, queries
from source.common import config

logger = logging.getLogger('app')


class UnauthorizedError(Exception):
    """Exception raised for unauthorized requests."""

    def __init__(self, message="Unauthorized Error!."):
        self.message = message
        super().__init__(self.message)


def token_required(f):
    from functools import wraps
    from flask import jsonify
    import jwt

    @wraps(f)
    def decorated(*args, **kwargs):
        token = None

        if 'Authorization' in request.headers:
            token = request.headers['Authorization'].split(" ")[1]
        else:
            token = request.args.get('token')

        if not token:
            return jsonify({'message': 'Token is missing!'}), 401
        
        logger.debug(f"Token obtained")
        try:
            data = jwt.decode(token, config.JWT_SECRET, algorithms=["HS256"])
            request.context = data
            
            user_id = data['user_id']
            if user_id is not None:
                is_admin = db_helper.find_one(queries.V2_FIND_USER_ADMIN_BY_USER_ID, user_id)['is_admin']
                if is_admin is None:
                    is_admin = 0
                request.context['is_admin'] = is_admin

            if 'organization-id' in request.headers:
                organization_id = request.headers['organization-id']
                # organization_name = get_organization_name_from_organization_id(organization_id)
                organization = db_helper.find_one(queries.FIND_ORGANIZATION_BY_ORGANIZATION_ID, organization_id)
                organization_name = organization['org_name']
                request.context['organization_id'] = organization_id
                request.context['organization_name'] = organization_name
        except jwt.ExpiredSignatureError as ese:
            logger.error(ese)
            return jsonify({'message': 'Token has expired!', 'error': str(ese)}), 401
        except jwt.InvalidTokenError as ite:
            logger.error(ite)
            return jsonify({'message': 'Token is invalid!', 'error': str(ite)}), 401
        except RuntimeError as re:
            logger.error(re)
            return jsonify({'message': str(re), 'error': str(re)}), 500
        except Exception as e:
            logger.error(e)
            return jsonify({'message': 'Token is invalid!'}), 401

        return f(*args, **kwargs)

    return decorated

#Intended to authorise Data Owners. Best to change the term Super Users to Data Admins
def authorised(f):
    from functools import wraps
    from flask import jsonify

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            if 'organization-id' not in request.headers:
                raise UnauthorizedError("Unauthorised Access!")
            if 'user_id' not in request.context:
                raise UnauthorizedError("Unauthorised Access!")
            organization_id = request.headers['organization-id']
            user_id = request.context['user_id']
            user_organization = db_helper.find_one(queries.FIND_USER_ORGANIZATION_BY_ORGANIZATION_ID_AND_USER_ID,
                                                   organization_id, user_id)
            user_role = user_organization['role']
            if user_role != "SUPER_USER":
                raise UnauthorizedError("Unauthorised Access!")
        except UnauthorizedError as ue:
            return jsonify({'message': str(ue), 'error': str(ue)}), 401
        except RuntimeError as re:
            logger.error(re)
            return jsonify({'message': str(re), 'error': str(re)}), 500
        except Exception as e:
            logger.error(e)
            return jsonify({'message': "Unauthorised Access!"}), 401

        return f(*args, **kwargs)

    return decorated

#Intended to authorise Org Admins, who can add new Users to the org, and assign roles to them etc in future (not used as of now)
def authorised_orgadmin(f):
    from functools import wraps
    from flask import jsonify

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            if 'organization-id' not in request.headers:
                raise UnauthorizedError("Unauthorised Access!")
            if 'user_id' not in request.context:
                raise UnauthorizedError("Unauthorised Access!")
            organization_id = request.headers['organization-id']
            user_id = request.context['user_id']
            user_organization = db_helper.find_one(queries.FIND_USER_ORGANIZATION_BY_ORGANIZATION_ID_AND_USER_ID,
                                                   organization_id, user_id)
            user_role = user_organization['role']
            if user_role != "SYSTEM_ADMIN":
                raise UnauthorizedError("Unauthorised Access!")
        except UnauthorizedError as ue:
            return jsonify({'message': str(ue), 'error': str(ue)}), 401
        except RuntimeError as re:
            logger.error(re)
            return jsonify({'message': str(re), 'error': str(re)}), 500
        except Exception as e:
            logger.error(e)
            return jsonify({'message': "Unauthorised Access!"}), 401

        return f(*args, **kwargs)

    return decorated

#Intended for System Admins, who can add new Orgs, and assign modules to them etc.
def authorised_sysadmin(f):
    from functools import wraps
    from flask import jsonify

    @wraps(f)
    def decorated(*args, **kwargs):
        try:
            if 'user_id' not in request.context:
                raise UnauthorizedError("Unauthorised Access! No user_id in context.")
            user_id = request.context['user_id']
            #use queries.V2_FIND_USER_ADMIN_BY_USER_ID to get the is_admin value
            is_admin = db_helper.find_one(queries.V2_FIND_USER_ADMIN_BY_USER_ID, user_id)['is_admin']
            if is_admin != 1:     #is_admin = 1 means user is System Admin
                raise UnauthorizedError("Unauthorised Access! Not is_admin")
        except UnauthorizedError as ue:
            return jsonify({'message': str(ue), 'error': str(ue)}), 401
        except RuntimeError as re:
            logger.error(re)
            return jsonify({'message': str(re), 'error': str(re)}), 500
        except Exception as e:
            logger.error(e)
            return jsonify({'message': "Unauthorised Access!"}), 401

        return f(*args, **kwargs)

    return decorated

def validate_user(username, plain_password):
    try:
        # user = find_user_by_username(username)
        user = db_helper.find_one(queries.FIND_USER_BY_USERNAME, username)

        if user:
            stored_hashed_password = user['password_hash']
            return bcrypt.checkpw(plain_password.encode('utf-8'), stored_hashed_password.encode('utf-8')), user['id']
        return False, None
    except Exception as e:
        logger.error(e)
        raise e


def validate_user_for_oauth2(email):
    try:
        # user = find_user_by_email(email)
        user = db_helper.find_one(queries.FIND_USER_BY_EMAIL, email)

        if user:
            return True, user['id']
        return False, None
    except Exception as e:
        logger.error(e)
        raise e


def login():
    try:
        username = request.json['username']
        password = request.json['password']
        is_user_valid, user_id = validate_user(username, password)
        if is_user_valid:

            payload = {
                'user_id': user_id,
                'iss': config.JWT_ISS,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=240),  # token will expire after 24 hours

                # 'aud': ['org_user']
            }
            encoded_jwt = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
            user = db_helper.find_one(queries.FIND_USER_BY_USER_ID, user_id)

            logger.debug(f"############################User Id: {user_id}")
            return encoded_jwt, {"sysadmin": f"{user['is_admin']}"}
        else:
            raise UnauthorizedError("Invalid user credentials!")
    except Exception as e:
        logger.error(e)
        raise e


def oauth2_login():
    try:
        # OAuth2 config
        client_id = os.getenv('MSAUTH_CLIENT_ID')
        client_secret = os.getenv('MSAUTH_CLIENT_SECRET')
        redirect_uri = os.getenv('MSAUTH_REDIRECT_URI')
        authority = os.getenv('MSAUTH_AUTHORITY')
        # authorize_url = f"{authority}/oauth2/v2.0/authorize"
        token_url = f"{authority}/oauth2/v2.0/token"
        microsoft = OAuth2Session(client_id, state=request.args.get('state'), redirect_uri=redirect_uri,
                                  scope=['openid', 'email', 'profile', 'User.Read'])
        token = microsoft.fetch_token(token_url, client_secret=client_secret, authorization_response=request.url)
        user_info = microsoft.get('https://graph.microsoft.com/v1.0/me').json()
        email_id = user_info.get('mail')
        is_user_valid, user_id = validate_user_for_oauth2(email_id)
        if is_user_valid:
            payload = {
                'user_id': user_id,
                'iss': config.JWT_ISS,
                'iat': datetime.utcnow(),
                'exp': datetime.utcnow() + timedelta(hours=24),  # token will expire after 24 hours

                # 'aud': ['org_user']
            }
            encoded_jwt = jwt.encode(payload, config.JWT_SECRET, algorithm="HS256")
            user = db_helper.find_one(queries.FIND_USER_BY_USER_ID, user_id)

            logger.debug(f"############################User Id: {user_id}")
            return encoded_jwt, user['username'], {"sysadmin": f"{user['is_admin']}"}
        else:
            raise UnauthorizedError("Invalid user credentials!")
    except Exception as e:
        logger.error(e)
        raise e


def get_user_info():
    try:
        if 'organization_id' not in request.context:
            raise RuntimeError('Organization Id is required!')
        organization_id = request.context.get('organization_id')
        user_id = request.context.get('user_id')
        user = db_helper.find_one(queries.FIND_USER_BY_USER_ID, user_id)
        user_organizations = db_helper.find_many(queries.FIND_USER_ORGANIZATION_BY_ORGANIZATION_ID_AND_USER_ID,
                                                 organization_id, user_id)
        roles = [user_organization.get('role') for user_organization in user_organizations]
        if user.get('is_admin') == 1:
            roles.append("ADMIN")
        user_info = dict(username=user.get('username'), email=user.get('email'), first_name=user.get('first_name'),
                         last_name=user.get('last_name'), roles=roles)
        return user_info
    except Exception as e:
        logger.error(e)
        raise e
