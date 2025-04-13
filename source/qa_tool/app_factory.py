from datetime import timezone, timedelta, datetime

from flask import Flask, redirect, request, render_template
from passlib.apache import HtpasswdFile

from source.common.flask_sqlachemy import db
from source.qa_tool import flask_config
from source.qa_tool.auth import auth
from source.qa_tool.lib import db_helper
from source.qa_tool.lib.threads_helper import get_all_threads_for_user


def create_app():
    app = Flask(__name__)

    app.config.from_object(flask_config.Config)

    db.init_app(app)

    users_file = HtpasswdFile('internal-users.htpasswd')

    @auth.verify_password
    def verify_password(username, password):
        return users_file.check_password(username, password)

    @app.route('/logout')
    def logout():
        scheme = request.scheme
        host = request.host
        return redirect(f"{scheme}://logout:logout@{host}")

    @app.route('/')
    @auth.login_required
    def index():
        return render_template('index.html')

    @app.route('/threads')
    @auth.login_required
    def threads():
        username = request.args.get('username', '')
        user_id = db_helper.find_one(
            "SELECT id FROM users WHERE username = %s", username)
        if user_id is not None:
            user_id = user_id.get('id', None)
        week_starting_date = request.args.get('week_starting_date', None)
        # convert week_starting_date to date and find the date 7 days after and then convert back to str to assign to end_date
        start_date = None
        end_date = None
        if week_starting_date:
            start_date = datetime.strptime(week_starting_date, "%Y-%m-%d")
            start_date = start_date.replace(tzinfo=timezone.utc)  # Ensure start_date has timezone info
            end_date = start_date + timedelta(days=7)
            end_date = end_date.replace(tzinfo=timezone.utc)

        threads = get_all_threads_for_user(user_id, start_date, end_date)

        usernames = db_helper.find_many("SELECT id, username, email FROM users where is_active = 1")

        # Create a dictionary mapping user_id to username
        user_id_to_username = {user['id']: user['username'] for user in usernames}

        # Add username to each thread
        for thread in threads:
            thread['username'] = user_id_to_username.get(thread['user_id'], 'Unknown')

        return render_template('threads.html', active_page='/threads', threads=threads, usernames=usernames)

    return app
