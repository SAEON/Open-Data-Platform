from odp.admin.views.base import SysAdminModelView, KeyField
from odp.db.models import Scope


class RoleModelView(SysAdminModelView):
    """
    Role model view.
    """
    column_list = ['name', 'key', 'scopes']
    column_default_sort = 'name'
    column_formatters = {
        'scopes': lambda vw, ctx, model, prop: ', '.join(sorted([s.key for s in model.scopes]))
    }

    form_columns = ['name', 'key', 'scopes']
    form_overrides = {
        'key': KeyField
    }
    form_args = {
        'scopes': dict(
            get_label='key',
            query_factory=lambda: Scope.query.order_by('key'),
        )
    }
    create_template = 'role_create.html'
    edit_template = 'role_edit.html'
