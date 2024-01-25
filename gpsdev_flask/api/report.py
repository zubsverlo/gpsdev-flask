from flask import Blueprint
from gpsdev_flask import db_session
from gpsdev_flask.models import ObjectsSite
from sqlalchemy import select
from flask import jsonify, send_file, request
from trajectory_report.report import ReportWithAdditionalColumns
from trajectory_report.exceptions import ReportException
from gpsdev_flask.ma_schemas import ReportSchema
from marshmallow import ValidationError
from gpsdev_flask.api.error_responses import (report_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required


report = Blueprint('report', __name__)


@report.route('/', methods=['POST'])
@api_login_required
def get_report():
    try:
        report_request = ReportSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = ReportWithAdditionalColumns(**report_request)
    except ReportException as e:
        return report_error_422(str(e))
    return jsonify(r.as_json_dict)


@report.route('/download', methods=['POST'])
@api_login_required
def download():
    try:
        report_request = ReportSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = ReportWithAdditionalColumns(**report_request)
    except ReportException as e:
        return report_error_422(str(e))

    sel = select(ObjectsSite.object_id).where(ObjectsSite.no_payments == True)
    list_no_payments = [i for i in db_session.execute(sel).scalars()]

    file = r.xlsx(list_no_payments)
    return send_file(file, mimetype="application/vnd.ms-excel",
                     download_name='table.xlsx', as_attachment=True)
