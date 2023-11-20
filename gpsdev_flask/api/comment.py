from flask import Blueprint
from flask import request, jsonify
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import CommentSchema
from gpsdev_flask.api.error_responses import validation_error_422
from gpsdev_flask.api import api_login_required
from gpsdev_flask import db_session
from sqlalchemy import text


comment = Blueprint('comment', __name__)


@comment.route('/', methods=['POST'])
@api_login_required
def comment_post():
    schema = CommentSchema()
    try:
        obj = schema.load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)

    sql = (
        f"replace into comment"
        f"(division_id, employee_id, object_id, comment) "
        f"values('{obj['division_id']}', '{obj['employee_id']}', "
        f"'{obj['object_id']}', '{obj['comment']}')"
    )

    db_session.execute(text(sql))
    db_session.commit()
    return jsonify({}), 201
