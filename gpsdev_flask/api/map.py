from flask import Blueprint
from flask import jsonify, request
from trajectory_report.map.movements import MapObjectsOnly
from trajectory_report.exceptions import ReportException
from gpsdev_flask.ma_schemas import ReportSchema
from marshmallow import ValidationError
from gpsdev_flask.api.error_responses import (report_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required


map = Blueprint('map', __name__)


@map.route('/objects', methods=['POST'])
@api_login_required
def get_objects_map():
    try:
        report_request = ReportSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        objects_map = MapObjectsOnly(**report_request).map_html
    except ReportException as e:
        return report_error_422(str(e))
    return jsonify({"map": objects_map})