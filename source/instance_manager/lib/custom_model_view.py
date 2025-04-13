from flask import redirect
from flask_admin.contrib.sqla import ModelView

from source.instance_manager.auth import auth


class CustomModelView(ModelView):
    def is_accessible(self):
        return auth.get_auth() is not None

    def inaccessible_callback(self, name, **kwargs):
        return redirect('/')

    form_excluded_columns = ['created_at']
