from flask import request, flash, redirect
from flask_admin import expose
from flask_admin.helpers import get_redirect_target
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_login import current_user
from sqlalchemy import Boolean, String

from odp.admin.views.base import AdminModelView
from odp.db.models import Institution, User


class UserModelView(AdminModelView):
    """
    User model view.
    """
    can_create = False  # users may only be created via signup
    action_disallowed_list = ['delete']  # disallow deletion of multiple users at once

    column_list = ['id', 'email', 'verified', 'active', 'superuser', 'institutions']
    column_default_sort = 'email'
    column_formatters = {
        'institutions': lambda vw, ctx, model, prop: ', '.join(sorted([i.name for i in model.institutions]))
    }

    form_columns = ['id', 'email', 'active', 'institutions']
    form_args = {
        'institutions': dict(
            get_label='name',
            query_factory=lambda: Institution.query.order_by('name'),
        )
    }
    form_widget_args = {
        'id': dict(
            disabled=True,
            style='color: black; width: 30%',
        ),
        'email': dict(
            disabled=True,
            style='color: black; width: 30%',
        ),
    }
    form_optional_types = (Boolean, String)  # force email field to be non-mandatory
    edit_template = 'user_edit.html'

    @expose('/edit/', methods=('GET', 'POST'))
    def edit_view(self):
        id = get_mdict_item_or_list(request.args, 'id')
        if id is not None:
            user = User.query.get(id)
            if user and user.superuser and not current_user.superuser:
                flash("Only superusers may perform this action.")
                return redirect(get_redirect_target())
        return super().edit_view()

    @expose('/delete/', methods=('POST',))
    def delete_view(self):
        id = request.form.get('id')
        if id is not None:
            user = User.query.get(id)
            if user and user.superuser and not current_user.superuser:
                flash("Only superusers may perform this action.")
                return redirect(get_redirect_target())
        return super().delete_view()
