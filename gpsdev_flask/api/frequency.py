from flask import Blueprint
from flask import request, jsonify
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import FrequencySchema
from gpsdev_flask.api.error_responses import validation_error_422
from gpsdev_flask.api import api_login_required
from gpsdev_flask import db_session
from sqlalchemy import text


frequency = Blueprint('frequency', __name__)


@frequency.route('/', methods=['POST'])
@api_login_required
def frequency_post():
    schema = FrequencySchema()
    try:
        obj = schema.load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)

    sql = (
        f"replace into frequency"
        f"(division_id, employee_id, object_id, frequency) "
        f"values('{obj['division_id']}', '{obj['employee_id']}', "
        f"'{obj['object_id']}', '{obj['frequency']}')"
    )

    db_session.execute(text(sql))
    return jsonify({}), 201
