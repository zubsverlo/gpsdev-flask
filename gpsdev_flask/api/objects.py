from flask import Blueprint
from gpsdev_flask import db_session, redis_session
from gpsdev_flask.models import (ObjectsSite, Division, 
                                 PermitStatements, Statements)
from sqlalchemy import select, update, delete, text, func
from flask import jsonify, request, g
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import ObjectSchema, ObjectStatementPermit
from gpsdev_flask.api.error_responses import (not_found_404,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required
import json

objects = Blueprint('objects', __name__)

@objects.route('/', methods=['GET', 'POST'])
@api_login_required
def objects_many():
    if request.method == "GET":
        if 'active' in request.args.keys() \
                and request.args.get('active') != 'false':
            res = db_session.query(ObjectsSite)\
                .filter(ObjectsSite.active == True)\
                .all()
            return jsonify(ObjectSchema(
                many=True, 
                exclude=[
                    'active', 'latitude', 'longitude', 'no_payments', 'phone',
                    'admission_date', 'denial_date', 'apartment_number'
                    ]
                ).dump(res)
            )

        res = db_session.query(ObjectsSite)\
            .filter(ObjectsSite.division.in_(current_user.access_list))\
            .all()
        schema = ObjectSchema(many=True)
        return jsonify(schema.dump(res))

    if request.method == "POST":
        schema = ObjectSchema()
        try:
            obj = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        db_obj = ObjectsSite(**obj)
        db_session.add(db_obj)
        db_session.commit()
        db_session.refresh(db_obj)
        return jsonify(schema.dump(db_obj)), 201


@objects.route('/<int:object_id>', methods=['GET', 'PATCH', 'DELETE'])
@api_login_required
def objects_one(object_id=None):
    if request.method == "GET":
        obj = db_session.query(ObjectsSite)\
            .filter_by(object_id=object_id)\
            .first()
        if not obj:
            return not_found_404()
        return jsonify(ObjectSchema().dump(obj))

    if request.method == "PATCH":
        p_object = db_session.query(ObjectsSite)\
            .filter_by(object_id=object_id)\
            .first()
        if not p_object:
            return not_found_404()

        g.p_object = p_object
        
        schema = ObjectSchema(partial=True)
        try:
            obj = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        db_session.execute(
            update(ObjectsSite)
            .filter_by(object_id=object_id)
            .values(**obj)
        )
        db_session.commit()
        db_session.refresh(p_object)
        return jsonify(schema.dump(p_object))

    if request.method == 'DELETE':
        db_session.execute(
            delete(ObjectsSite).filter_by(object_id=object_id)
        )
        db_session.commit()
        return jsonify({}), 204


@objects.route('/statements-permit/<int:object_id>', methods=['POST'])
@api_login_required
def forbid_statements(object_id):
    if current_user.rang_id > 2:
        return not_allowed_403()
    obj_db = db_session.query(ObjectsSite)\
            .filter_by(object_id=object_id)\
            .first()
    if not obj_db:
        return not_found_404()
    schema = ObjectStatementPermit()
    try:
        obj = schema.load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    if obj['allow']:
        message = f"Выходы к ПСУ {obj_db.name} за {obj['date']} снова разрешены."
        db_session.execute(
            delete(PermitStatements)\
             .where(PermitStatements.object_id == object_id)\
             .where(PermitStatements.date == obj['date'])
        )
    else:
        message = (
            f"Запрещено проставлять выходы ПСУ {obj_db.name} за {obj['date']}.\n"
            f"Все выходы к подопечному за этот день удалены."
        )
        db_session.execute(
            text(
                f"replace into permit_statements"
                f"(object_id, date) "
                f"values('{object_id}', '{obj['date']}')"
            )
        )
        db_session.execute(
            delete(Statements)\
                .where(Statements.date == obj['date'])\
                .where(Statements.object_id == object_id)
        )        
    db_session.commit()
    
    # cache current permit_statements:
    permit_statements_select = select(
        PermitStatements.date, 
        func.json_arrayagg(PermitStatements.object_id).label('array')
    ).group_by(PermitStatements.date)
    permit_statements = json.dumps(
        {
            str(i.date): json.loads(i.array)
            for i in db_session.execute(permit_statements_select).all()
        }
    )
    redis_session.set('permit_statements', permit_statements)
    
    return jsonify({"message": message}), 200