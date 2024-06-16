from flask import Blueprint, jsonify, request
from marshmallow import ValidationError
from trajectory_report.exceptions import ReportException
from trajectory_report.map import MapMovements

from gpsdev_flask.api import api_login_required
from gpsdev_flask.api.error_responses import (
    report_error_422,
    validation_error_422,
)
from gpsdev_flask.ma_schemas import MapMovementsSchema

one_employee_report = Blueprint("one_employee_report", __name__)


@one_employee_report.route("/", methods=["POST"])
@api_login_required
def report():
    try:
        report_request = MapMovementsSchema(
            exclude=["latitude", "longitude"],
        ).load(
            request.get_json(),
        )
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = MapMovements(**report_request)
        r_json = r.as_json_dict
    except ReportException as e:
        return report_error_422(str(e))
    tracking_type = "Owntracks" if r.owntracks else "MTS"
    r_json["tracking_type"] = tracking_type
    return jsonify(r_json)
