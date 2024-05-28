from flask import Blueprint
from flask import jsonify, request
from trajectory_report.exceptions import ReportException
from gpsdev_flask.ma_schemas import CoordinatesAnalysisSchema
from marshmallow import ValidationError
from gpsdev_flask.api.error_responses import (report_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required
from trajectory_report.coordinates_analysis_report import get_report


analysis = Blueprint('analysis', __name__)


@analysis.route('/', methods=['POST'])
@api_login_required
def get_report_analysis():
    try:
        report_request = CoordinatesAnalysisSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = get_report(**report_request)
    except ReportException as e:
        return report_error_422(str(e))
    return jsonify(r)
