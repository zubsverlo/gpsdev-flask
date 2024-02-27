from flask import Blueprint
from flask import request, jsonify, g
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import StatementsSchema
from gpsdev_flask.api.error_responses import validation_error_422
from gpsdev_flask.api import api_login_required
from gpsdev_flask import redis_session
import json


statements = Blueprint('statements', __name__)

def get_permit_statements() -> dict[str, str]:
    permit_statements = redis_session.get('permit_statements')
    if not permit_statements:
        sel = select(
            PermitStatements.date, 
            func.json_arrayagg(PermitStatements.object_id).label('array')
        ).group_by(PermitStatements.date)
        permit_statements = {
            str(i.date): i.array 
            for i in db_session.execute(sel).all()
        }
        redis_session.set('permit_statements', json.dumps(permit_statements))
        return permit_statements
    return json.loads(permit_statements)

@statements.route('/', methods=['POST'])
@api_login_required
def statements_main():
    g.loaded_accessed_divisions = current_user.access_list
    permits = get_permit_statements()
    try:
        stmts = StatementsSchema(many=True).load(request.json)
    except ValidationError as e:
        return validation_error_422(e.messages)
    
    # Если какой-то из выходов не будет проставлен из-за запрета
    # к ответу будет добавлено сообщение для уведомления
    permits_notify = False
    
    for stmt in stmts:
        if stmt.get('value'):
            line = (
                f"replace into statements_site"
                f"(division, name_id, object_id, date, statement) "
                f"values('{stmt['division']}', '{stmt['name_id']}', "
                f"'{stmt['object_id']}', '{stmt['date']}', '{stmt['value']}')"
            )
            if stmt['object_id'] in permits.get(str(stmt['date']), []):
                permits_notify = True
                continue
            redis_session.lpush('queue_sql', line)
        else:
            line = (
                f"delete from statements_site where "
                f"division = '{stmt['division']}' "
                f"and name_id = '{stmt['name_id']}' "
                f"and object_id = '{stmt['object_id']}' "
                f"and date = '{stmt['date']}'")
            redis_session.lpush('queue_sql', line)
            
    if permits_notify:
        return jsonify(
            {
                'message': ('Некоторые выходы не сохранены '
                            'из-за запрета руководителя.')
            }
        ), 201
        

    return jsonify({}), 201
