from flask import Blueprint
from flask import jsonify
from flask_login import current_user
from gpsdev_flask.ma_schemas import DivisionSchema
from gpsdev_flask.api import api_login_required


divisions = Blueprint('divisions', __name__)


@divisions.route('/accessed', methods=['GET'])
@api_login_required
def divisions_all():
    schema = DivisionSchema(many=True)
    res = schema.dump(current_user.access)
    return jsonify(res)
