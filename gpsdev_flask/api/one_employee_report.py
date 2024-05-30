from trajectory_report.map import MapMovements
from flask import Blueprint
from flask import jsonify, request
from trajectory_report.exceptions import ReportException
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import MapMovementsSchema, EmployeesSchema
from gpsdev_flask.api.error_responses import (report_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required
from gpsdev_flask import db_session
from gpsdev_flask.models import Employees, Journal


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
        r = MapMovements(**report_request).as_json_dict
    except ReportException as e:
        return report_error_422(str(e))
    entry = db_session.query(Journal)\
        .filter_by(name_id=report_request.get('name_id'))\
        .filter_by(period_end=None)\
        .first()
    if not entry:
        tracking_type = 'Не отслеживается'
    elif entry.owntracks:
        tracking_type = 'owntracks'
    else:
        tracking_type = 'MTS'
    r['tracking_type'] = tracking_type
    return jsonify(r)
