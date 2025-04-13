import os
from flask import Blueprint, jsonify, make_response
from source.api.utilities.externalapi_helpers import auth_helper

auth = Blueprint('auth', __name__)


@auth.route('/login', methods=['POST'])
def api_login_post():
    try:
        jwt_token, sysadmin = auth_helper.login()
        return make_response(jsonify({'data': {'token': jwt_token, 'sysadmin': sysadmin.get('sysadmin','0')}}), 200)
    except RuntimeError as re:
        return make_response(jsonify({'message': str(re), 'error': str(re)}), 401)
    except auth_helper.UnauthorizedError as ue:
        return make_response(jsonify({'message': str(ue), 'error': str(ue)}), 401)
    except Exception as e:
        return make_response(jsonify({'message': 'Oops! something went wrong.', 'error': str(e)}), 500)


@auth.route('/loginms365')
def login_ms365():
    try:
        import os
        from requests_oauthlib import OAuth2Session
        from flask import redirect
        # OAuth2 config
        client_id = os.getenv('MSAUTH_CLIENT_ID')
        redirect_uri = os.getenv('MSAUTH_REDIRECT_URI')
        authority = os.getenv('MSAUTH_AUTHORITY')
        authorize_url = f"{authority}/oauth2/v2.0/authorize"
        microsoft = OAuth2Session(client_id, redirect_uri=redirect_uri,
                                  scope=['openid', 'email', 'profile', 'User.Read'])
        authorization_url, state = microsoft.authorization_url(authorize_url)
        return redirect(authorization_url)
    except Exception as e:
        print(e)


@auth.route('/login/msoauth/callback', methods=['GET'])
def api_oauth2_login():
    from flask import redirect
    try:
        jwt_token, username, sysadmin = auth_helper.oauth2_login()
        return redirect(f'{os.getenv("FRONTEND_URL")}/auth/msauth?token={jwt_token}&sysadmin={sysadmin.get("sysadmin","0")}&username={username}')
    except Exception as e:
        print(e)
        return redirect(f'{os.getenv("FRONTEND_URL")}/auth/msauth?token=')


@auth.route('/user', methods=['GET'])
@auth_helper.token_required
def get_user_info():
    try:
        user_info = auth_helper.get_user_info()
        return jsonify(dict(data=user_info, message='User info fetched successfully!')), 200
    except Exception as e:
        print(e)
        return jsonify(dict(message='Oops! something went wrong.', error=str(e))), 500

@auth.route('/token/validate', methods=['GET'])
@auth_helper.token_required
def validate_token():
    try:        
        return make_response(jsonify({
            'valid': True,
        }), 200)
    except Exception as e:
        print(e)
        return make_response(jsonify({'valid': False, 'message': 'Oops! something went wrong.', 'error': str(e)}), 500)