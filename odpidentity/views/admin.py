from flask_admin import AdminIndexView
from flask_admin.contrib.sqla import ModelView
from flask_login import current_user

from ..models import db
from ..models.user import User
from ..models.role import Role
from ..models.scope import Scope
from ..models.institution import Institution
from ..models.institution_registry import InstitutionRegistry
from ..lib.utils import make_object_name


class AdminHomeView(AdminIndexView):
    """
    Admin UI home page view.
    """
    def is_accessible(self):
        return current_user.is_authenticated


class AdminModelView(ModelView):
    """
    Base view for all data models.
    """
    list_template = 'admin_model_list.html'
    create_template = 'admin_model_create.html'
    edit_template = 'admin_model_edit.html'
    details_template = 'admin_model_details.html'

    def is_accessible(self):
        return current_user.is_authenticated


class UserModelView(AdminModelView):
    """
    User model view.
    """
    can_create = False
    column_list = ['id', 'email', 'active', 'confirmed_at', 'institutions']
    column_formatters = {
        'institutions': lambda vw, ctx, model, prop: ', '.join(sorted([i.title for i in model.institutions]))
    }
    form_columns = ['email', 'active', 'institutions']
    form_args = {
        'institutions': dict(
            get_label='title',
            query_factory=lambda: Institution.query.order_by('title'),
        )
    }
    edit_template = 'user_edit.html'


class StaticDataModelView(AdminModelView):
    """
    Base view for static data models.
    """
    column_default_sort = 'name'
    form_excluded_columns = ['name']
    form_args = {
        'title': dict(filters=[lambda s: s.strip() if s else s])
    }

    def on_model_change(self, form, model, is_created):
        # generate the name field from the title
        if is_created:
            model.name = make_object_name(model.title)


class RoleModelView(StaticDataModelView):
    """
    Role model view.
    """
    form_excluded_columns = ['name', 'scopes']


class ScopeModelView(StaticDataModelView):
    """
    Scope model view.
    """
    column_list = ['name', 'title', 'description', 'roles']
    column_formatters = {
        'roles': lambda vw, ctx, model, prop: ', '.join(sorted([r.title for r in model.roles]))
    }
    form_columns = ['title', 'description', 'roles']
    form_args = {
        'roles': dict(
            get_label='title',
            query_factory=lambda: Role.query.order_by('title'),
        )
    }
    create_template = 'scope_create.html'
    edit_template = 'scope_edit.html'


class InstitutionModelView(StaticDataModelView):
    """
    Institution model view.
    """
    column_list = ['name', 'title', 'description', 'parent', 'registry.title']
    column_labels = {
        'registry.title': 'Registry'
    }
    column_formatters = {
        'parent': lambda vw, ctx, model, prop: model.parent.title if model.parent else None
    }
    form_columns = ['registry', 'parent', 'title', 'description']
    form_args = {
        'registry': dict(
            get_label='title',
            query_factory=lambda: InstitutionRegistry.query.order_by('title'),
        ),
        'parent': dict(
            get_label='title',
            query_factory=lambda: Institution.query.order_by('title'),
        ),
    }


class InstitutionRegistryModelView(StaticDataModelView):
    """
    InstitutionRegistry model view.
    """
    form_excluded_columns = ['name', 'institutions']


home = AdminHomeView()

users = UserModelView(
    User, db.session,
    name='Users',
    endpoint='users',
)
roles = RoleModelView(
    Role, db.session,
    name='Roles',
    endpoint='roles',
)
scopes = ScopeModelView(
    Scope, db.session,
    name='Scopes',
    endpoint='scopes',
)
institutions = InstitutionModelView(
    Institution, db.session,
    name='Institutions',
    category='Institutions',
    endpoint='institutions',
)
institution_registries = InstitutionRegistryModelView(
    InstitutionRegistry, db.session,
    name='Institution Registries',
    category='Institutions',
    endpoint='institutions/registries',
)
