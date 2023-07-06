from flask import Blueprint, request, jsonify
from trajectory_report.api.mts import update_name, delete_subs
from trajectory_report.exceptions import MtsException
from gpsdev_flask.api.error_responses import (mts_error_422,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required


mts = Blueprint('mts', __name__)


@mts.route('/subscriber/<int:subscriber>', methods=['DELETE', 'PATCH'])
@api_login_required
def delete_subscriber(subscriber):
    if request.method == 'DELETE':
        try:
            delete_subs([subscriber])
        except MtsException as e:
            return mts_error_422(str(e))
        return jsonify({}), 204
    if request.method == 'PATCH':
        new_name = request.get_json().get('name')
        if not new_name:
            return validation_error_422('You should provide a new name')
        try:
            update_name(subscriber, new_name)
        except MtsException as e:
            return mts_error_422(str(e))
        return jsonify({}), 200
