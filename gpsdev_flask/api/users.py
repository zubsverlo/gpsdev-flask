from gpsdev_flask.models import User
from flask import Blueprint, jsonify, request
from gpsdev_flask import db_session
from sqlalchemy import update, delete
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import UserSchema
from gpsdev_flask.api.error_responses import (not_found_404,
                                              validation_error_422,
                                              not_allowed_403)
from gpsdev_flask.api import api_login_required
from gpsdev_flask.celery_tasks import update_json_cache, clear_json_cache
from gpsdev_flask import redis_session
import json


users = Blueprint('users', __name__)


@users.route('/', methods=['GET', 'POST'])
@users.route('/<int:user_id>', methods=['GET', 'PATCH', 'DELETE'])
@api_login_required
def default_user(user_id=None):
    if current_user.rang_id != 1:
        return not_allowed_403()
    if request.method == "POST":
        schema = UserSchema()
        u = schema.load(request.get_json())
        user = User(**u)
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        clear_json_cache.delay('users')
        return jsonify(schema.dump(user)), 201
    if request.method == 'GET' and user_id:
        res = db_session.query(User).filter_by(id=user_id).first()
        if not res:
            return not_found_404()
        schema = UserSchema()
        return jsonify(schema.dump(res))
    if request.method == 'GET':
        cached = redis_session.get('users')
        if cached:
            return jsonify(json.loads(cached))
        res = db_session.query(User).all()
        schema = UserSchema(many=True)
        res = schema.dump(res)
        update_json_cache.delay('users', json.dumps(res))
        return jsonify(res)
    if request.method == 'PATCH':
        user_db = db_session.get(User, user_id)
        if not user_db:
            return not_found_404()
        schema = UserSchema(partial=True)
        try:
            user = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)
        if 'access' in user:
            user_db.access = user.get('access')
            del user['access']
        db_session.execute(
            update(User)
            .filter_by(id=user_id)
            .values(**user)
        )

        db_session.commit()
        db_session.refresh(user_db)
        clear_json_cache.delay('users')
        return jsonify(schema.dump(user_db))
    if request.method == 'DELETE':
        db_session.execute(
            delete(User)
            .filter_by(id=user_id)
        )
        db_session.commit()
        clear_json_cache.delay('users')
        return jsonify({}), 204
