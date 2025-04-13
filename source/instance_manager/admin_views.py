from flask_admin import BaseView, expose
from sqlalchemy import func, select

from source.common.flask_sqlachemy import db
from source.common.models import Organization, User
from source.common.models.models import OrganizationStatus, UserOrganizationRole
from source.instance_manager.auth import auth
from source.instance_manager.lib.custom_model_view import CustomModelView


class IndexView(BaseView):
    @expose('/')
    @auth.login_required
    def index(self):
        org_count = db.session.execute(select(func.count()).select_from(Organization)).scalar_one()
        user_count = db.session.execute(select(func.count()).select_from(User)).scalar_one()

        return self.render('index.html', org_count=org_count, user_count=user_count)


index_view = IndexView(name='Home', endpoint='index')


class OrganizationsView(CustomModelView):
    can_view_details = True

    # Columns to display in the list view
    column_list = ['org_id', 'org_name', 'creation_date', 'status', 'description', 'admin_user_id']

    # Columns that can be searched
    column_searchable_list = ['org_name', 'description']

    # Columns that can be filtered
    column_filters = ['status', 'creation_date']

    # Columns that can be sorted
    column_sortable_list = ['org_id', 'org_name', 'creation_date', 'status']

    # Fields to show in create/edit forms
    form_columns = [
        'org_name',
        'description',
        'admin_user_id',
        'status',
        'logo_url',
        'home_module_function_name',
        'vector_provider'
    ]

    # Custom column labels
    column_labels = {
        'org_id': 'ID',
        'org_name': 'Name',
        'creation_date': 'Created',
        'admin_user_id': 'Admin User ID',
        'home_module_function_name': 'Home Module',
        'vector_provider': 'Vector Provider'
    }

    # Fields that should be treated as select dropdowns
    form_choices = {
        'status': [
            (status.value, status.name) for status in OrganizationStatus
        ]
    }


class OrganizationUsersView(CustomModelView):
    can_view_details = True

    # Columns to display in the list view
    column_list = ['user_id', 'org_id', 'role', 'join_date']

    # Columns that can be filtered
    column_filters = ['role', 'join_date', 'org_id', 'user_id']

    # Columns that can be sorted
    column_sortable_list = ['user_id', 'org_id', 'role', 'join_date']

    # Fields to show in create/edit forms
    form_columns = ['user_id', 'org_id', 'role']

    # Custom column labels
    column_labels = {
        'user_id': 'User ID',
        'org_id': 'Organization ID',
        'role': 'Role',
        'join_date': 'Join Date'
    }

    # Fields that should be treated as select dropdowns
    form_choices = {
        'role': [
            (role.value, role.name) for role in UserOrganizationRole
        ]
    }


class UsersView(CustomModelView):
    can_view_details = True

    # Columns to display in the list view
    column_list = ['id', 'username', 'email', 'first_name', 'last_name', 'date_joined', 'is_active', 'is_admin']

    # Columns that can be searched
    column_searchable_list = ['username', 'email', 'first_name', 'last_name']

    # Columns that can be filtered
    column_filters = ['is_active', 'is_admin', 'date_joined']

    # Columns that can be sorted
    column_sortable_list = ['id', 'username', 'email', 'date_joined', 'is_active', 'is_admin']

    # Fields to show in create/edit forms
    form_columns = [
        'username',
        'email',
        'first_name',
        'last_name',
        'date_of_birth',
        'is_active',
        'is_admin',
        'profile_picture_url',
        'phone_number'
    ]

    # Custom column labels
    column_labels = {
        'id': 'ID',
        'username': 'Username',
        'email': 'Email',
        'first_name': 'First Name',
        'last_name': 'Last Name',
        'date_of_birth': 'Birth Date',
        'date_joined': 'Join Date',
        'is_active': 'Active',
        'is_admin': 'Admin',
        'profile_picture_url': 'Profile Picture URL',
        'phone_number': 'Phone'
    }
