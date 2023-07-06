from flask import Blueprint, request, abort, jsonify
from flask_login import logout_user
from gpsdev_flask.ma_schemas import LoginSchema
from marshmallow import ValidationError
from gpsdev_flask.api.error_responses import validation_error_422


auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    try:
        LoginSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    # todo: redirect to home page
    return jsonify({}), 200


@auth_bp.route('/logout', methods=['GET'])
def logout():
    logout_user()
    # todo: redirect to login page
    return jsonify({}), 200
