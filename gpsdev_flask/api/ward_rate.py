from flask import Blueprint
from flask import request, jsonify
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import WardRateSchema
from gpsdev_flask.api.error_responses import validation_error_422
from gpsdev_flask.api import api_login_required
from gpsdev_flask import db_session
from sqlalchemy import text


ward_rate = Blueprint('ward_rate', __name__)


@ward_rate.route('/', methods=['POST'])
@api_login_required
def ward_rate_post():
    schema = WardRateSchema()
    try:
        obj = schema.load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)

    sql = (
        f"replace into ward_rate"
        f"(division_id, name_id, rate) "
        f"values('{obj['division_id']}', '{obj['name_id']}', "
        f"'{obj['rate']}')"
    )

    db_session.execute(text(sql))
    db_session.commit()
    return jsonify({}), 201
