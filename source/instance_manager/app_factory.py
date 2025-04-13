from flask import Flask, redirect, request
from flask_admin import Admin
from flask_admin.menu import MenuLink
from flask_admin.theme import Bootstrap4Theme
from passlib.apache import HtpasswdFile

from source.common.flask_sqlachemy import db
from source.common.models import Organization, UserOrganization, User
from source.instance_manager import flask_config
from source.instance_manager.admin_views import index_view, OrganizationsView, OrganizationUsersView, UsersView
from source.instance_manager.auth import auth


def create_app():
    app = Flask(__name__)

    app.config.from_object(flask_config.Config)

    db.init_app(app)

    users_file = HtpasswdFile('internal-users.htpasswd')

    @auth.verify_password
    def verify_password(username, password):
        return users_file.check_password(username, password)

    admin = Admin(
        app,
        name='Instance Manager',
        url='/',
        index_view=index_view,
        theme=Bootstrap4Theme(swatch='cosmo')
    )

    admin_views = [
        OrganizationsView(Organization, db.session, name='Orgs', category="Orgs", endpoint="orgs"),
        OrganizationUsersView(UserOrganization, db.session, name='Org Users', category="Orgs", endpoint="org-users"),
        UsersView(User, db.session, name='Users', category="Users", endpoint="users"),
    ]

    [admin.add_view(view) for view in admin_views]

    admin.add_link(MenuLink(name='Logout', url='/logout', category=''))

    @app.route('/logout')
    def logout():
        scheme = request.scheme
        host = request.host
        return redirect(f"{scheme}://logout:logout@{host}")

    return app
