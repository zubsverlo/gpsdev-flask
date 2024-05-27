from flask import Blueprint, jsonify, request, g
from gpsdev_flask import db_session
from gpsdev_flask.models import Journal
from sqlalchemy import update, text, select
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.api import api_login_required
from gpsdev_flask.ma_schemas import JournalSchema
from gpsdev_flask.api.error_responses import (not_allowed_403,
                                              not_found_404,
                                              validation_error_422)
from gpsdev_flask import main_logger


journal = Blueprint('journal', __name__)


@journal.route('/', methods=['GET'])
@journal.route('/<int:row_id>', methods=['GET', 'DELETE', 'PATCH'])
@api_login_required
def journal_main(row_id=None):
    if current_user.rang_id != 1:
        return not_allowed_403('You are not allowed to journal')

    if request.method == 'GET':
        if not row_id:
            res = db_session.query(Journal).all()
            schema = JournalSchema(many=True)
        else:
            res = db_session.query(Journal).filter_by(id=row_id).first()
            schema = JournalSchema()
        if not res:
            return not_found_404("No journal records found")
        return jsonify(schema.dump(res))

    if request.method == 'PATCH':
        rec = db_session.get(Journal, row_id)
        if not rec:
            return not_found_404("No journal recs found")
        # g.rec = rec
        schema = JournalSchema(partial=True)
        try:
            new_record = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        db_session.execute(
            update(Journal)
            .filter_by(id=row_id)
            .values(**new_record)
        )
        db_session.commit()
        return jsonify(schema.dump(new_record))

    if request.method == 'DELETE':
        record = db_session.get(Journal, row_id)
        if not record:
            return not_found_404("No journal records found")
        db_session.delete(record)
        db_session.commit()
        return jsonify({}), 204
