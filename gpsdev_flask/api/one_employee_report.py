from trajectory_report.map import MapMovements
from flask import Blueprint
from flask import jsonify, request
from trajectory_report.exceptions import ReportException
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import MapMovementsSchema
from gpsdev_flask.api.error_responses import (report_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required


one_employee_report = Blueprint('one_employee_report', __name__)


@one_employee_report.route('/', methods=['POST'])
@api_login_required
def report():
    try:
        report_request = MapMovementsSchema(exclude=['latitude', 'longitude'])\
            .load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = MapMovements(**report_request)
    except ReportException as e:
        return report_error_422(str(e))
    return jsonify(r.as_json_dict)
