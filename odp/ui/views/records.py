import json

from flask import Blueprint, render_template, request, flash, redirect, url_for
from flask_login import current_user

from odp import ODPScope
from odp.ui import api
from odp.ui.auth import authorize
from odp.ui.forms import RecordForm, RecordTagQCForm
from odp.ui.views import utils

bp = Blueprint('records', __name__)


@bp.route('/')
@authorize(ODPScope.RECORD_READ)
@api.wrapper
def index():
    records = api.get('/record/')
    return render_template('record_list.html', records=records)


@bp.route('/<id>')
@authorize(ODPScope.RECORD_READ)
@api.wrapper
def view(id):
    record = api.get(f'/record/{id}')
    return render_template('record_view.html', record=record)


@bp.route('/new', methods=('GET', 'POST'))
@authorize(ODPScope.RECORD_CREATE)
@api.wrapper
def create():
    form = RecordForm(request.form)
    utils.populate_collection_choices(form.collection_id, include_none=True)
    utils.populate_schema_choices(form.schema_id, 'metadata')

    if request.method == 'POST' and form.validate():
        record = api.post('/record/', dict(
            doi=(doi := form.doi.data) or None,
            sid=(sid := form.sid.data) or None,
            collection_id=form.collection_id.data,
            schema_id=form.schema_id.data,
            metadata=json.loads(form.metadata.data),
        ))
        flash(f'Record {doi or sid} has been created.', category='success')
        return redirect(url_for('.view', id=record['id']))

    return render_template('record_edit.html', form=form)


@bp.route('/<id>/edit', methods=('GET', 'POST'))
@authorize(ODPScope.RECORD_MANAGE)
@api.wrapper
def edit(id):
    record = api.get(f'/record/{id}')

    form = RecordForm(request.form, data=record)
    utils.populate_collection_choices(form.collection_id)
    utils.populate_schema_choices(form.schema_id, 'metadata')

    if request.method == 'POST' and form.validate():
        api.put(f'/record/{id}', dict(
            doi=(doi := form.doi.data) or None,
            sid=(sid := form.sid.data) or None,
            collection_id=form.collection_id.data,
            schema_id=form.schema_id.data,
            metadata=json.loads(form.metadata.data),
        ))
        flash(f'Record {doi or sid} has been updated.', category='success')
        return redirect(url_for('.view', id=id))

    return render_template('record_edit.html', record=record, form=form)


@bp.route('/<id>/delete', methods=('POST',))
@authorize(ODPScope.RECORD_MANAGE)
@api.wrapper
def delete(id):
    api.delete(f'/record/{id}')
    flash(f'Record {id} has been deleted.', category='success')
    return redirect(url_for('.index'))


@bp.route('/<id>/tag/qc', methods=('GET', 'POST'))
@authorize(ODPScope.RECORD_TAG_QC)
@api.wrapper
def tag_qc(id):
    record = api.get(f'/record/{id}')

    # separate get/post form instantiation to resolve
    # ambiguity of missing vs false boolean field
    if request.method == 'POST':
        form = RecordTagQCForm(request.form)
    else:
        record_tag = next(
            (tag for tag in record['tags']
             if tag['tag_id'] == 'Record-QC' and tag['user_id'] == current_user.id),
            None
        )
        form = RecordTagQCForm(data=record_tag['data'] if record_tag else None)

    if request.method == 'POST' and form.validate():
        api.post(f'/record/{id}/tag', dict(
            tag_id='Record-QC',
            data={
                'pass_': form.pass_.data,
                'comment': form.comment.data,
            },
        ))
        flash(f'Record-QC tag has been set.', category='success')
        return redirect(url_for('.view', id=record['id']))

    return render_template('record_tag_qc.html', record=record, form=form)


@bp.route('/<id>/untag/qc', methods=('POST',))
@authorize(ODPScope.RECORD_TAG_QC)
@api.wrapper
def untag_qc(id):
    api.delete(f'/record/{id}/tag/Record-QC')
    flash(f'Record-QC tag has been removed.', category='success')
    return redirect(url_for('.view', id=id))
