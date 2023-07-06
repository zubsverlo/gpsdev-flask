from flask import Blueprint
from gpsdev_flask import db_session
from gpsdev_flask.models import ObjectsSite, Division
from sqlalchemy import select, update
from flask import jsonify, request, g
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import ObjectSchema
from gpsdev_flask.api.error_responses import (not_found_404,
                                              validation_error_422)
from gpsdev_flask.api import api_login_required


objects = Blueprint('objects', __name__)


@objects.route('/', methods=['GET', 'POST'])
@api_login_required
def objects_many():
    if request.method == "GET":
        if 'active' in request.args.keys() \
                and request.args.get('active') != 'false':
            sel = select(ObjectsSite.object_id,
                         ObjectsSite.name,
                         ObjectsSite.address,
                         ObjectsSite.division,
                         Division.division.label('division_name')
                         ).join(Division) \
                .where(ObjectsSite.division.in_(current_user.access_list)) \
                .where(ObjectsSite.active == True)
            res = db_session.execute(sel).all()
            return jsonify(ObjectSchema(partial=True, many=True).dump(res))

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


@objects.route('/<int:object_id>', methods=['GET', 'PATCH'])
@api_login_required
def objects_one(object_id=None):
    if request.method == "GET":
        obj = db_session.query(ObjectsSite)\
            .filter_by(object_id=object_id)\
            .filter(ObjectsSite.division.in_(current_user.access_list))\
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
        return jsonify(obj)
