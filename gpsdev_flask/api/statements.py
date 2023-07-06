from gpsdev_flask import TASKS_QUEUE
from flask import Blueprint
from sqlalchemy import text
from flask import request, jsonify, g
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import StatementsSchema
from gpsdev_flask.api.error_responses import validation_error_422
from gpsdev_flask.api import api_login_required


statements = Blueprint('statements', __name__)


@statements.route('/', methods=['POST'])
@api_login_required
def statements_main():
    g.loaded_accessed_divisions = current_user.access_list
    try:
        stmts = StatementsSchema(many=True).load(request.json)
    except ValidationError as e:
        return validation_error_422(e.messages)
    for stmt in stmts:
        if stmt.get('value'):
            TASKS_QUEUE.put(text(
                f"replace into statements_site"
                f"(division, name_id, object_id, date, statement) "
                f"values('{stmt['division']}', '{stmt['name_id']}', "
                f"'{stmt['object_id']}', '{stmt['date']}', '{stmt['value']}')"
            ))
        else:
            TASKS_QUEUE.put(text(
                f"delete from statements_site where "
                f"division = '{stmt['division']}' "
                f"and name_id = '{stmt['name_id']}' "
                f"and object_id = '{stmt['object_id']}' "
                f"and date = '{stmt['date']}'"))

    return jsonify({}), 201
