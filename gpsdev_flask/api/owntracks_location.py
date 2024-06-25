from flask import Blueprint
from gpsdev_flask import redis_session
from gpsdev_flask.models import OwnTracksLocation
from flask import jsonify, request
from marshmallow import ValidationError, EXCLUDE
from gpsdev_flask.api.error_responses import (
    validation_error_422,
    not_allowed_403,
)
from gpsdev_flask.ma_schemas import OwnTracksLocationSchema
from jose import jwt, JWTError
import datetime as dt
from gpsdev_flask import config
from gpsdev_flask import main_logger
from sqlalchemy.sql import insert


owntracks_location = Blueprint("owntracks_location", __name__)
# openssl -hex 32


@owntracks_location.route("/", methods=["POST"])
def post_location():
    auth = request.authorization
    try:
        payload = jwt.decode(auth.password, key=config.JWT_SECRET_KEY)
    except JWTError:
        return not_allowed_403()
    if not payload.get("sub") == auth.username:
        return not_allowed_403()
    schema = OwnTracksLocationSchema(unknown=EXCLUDE)
    try:
        obj = schema.load(request.get_json())
    except ValidationError as e:
        main_logger.info("validation owntrack location error")
        main_logger.info(e.messages)
        main_logger.info(request.get_json())
        main_logger.info(auth)
        # return validation_error_422(e.messages)
        return jsonify({})
    # компиляция insert в строку и добавление в очередь на исполнение в redis
    insert_statement = insert(OwnTracksLocation)\
        .values(**obj, employee_id=auth.username)\
        .compile(compile_kwargs={"literal_binds": True})
    if obj.get('created_at').date() < dt.date.today():
        # переформировать кластеры, если локации пришли позже
        redis_session.sadd(
            "owntracks_cluster_dates", str(obj.get('created_at').date())
        )
    main_logger.info(f"owntracks from {auth.username}: {obj}")
    redis_session.lpush('queue_sql', str(insert_statement))
    return jsonify({})
