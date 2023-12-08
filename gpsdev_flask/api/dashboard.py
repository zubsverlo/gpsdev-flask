from flask import Blueprint, jsonify, request, g
from gpsdev_flask import db_session
from flask_login import current_user
from gpsdev_flask.api import api_login_required
from gpsdev_flask.ma_schemas import JournalSchema
from gpsdev_flask.api.error_responses import (not_allowed_403,
                                              not_found_404,
                                              validation_error_422)
from trajectory_report.JournalManager import HrManager


dashboard = Blueprint('dashboard', __name__)


@api_login_required
@dashboard.route('/', methods=['GET'])
def get_tables():
    if current_user.rang_id != 1:
        return not_allowed_403('You are not allowed to Dashboard')
    j = HrManager()
    journal_tables = j.get_suggests_dict()
    return jsonify(journal_tables)
