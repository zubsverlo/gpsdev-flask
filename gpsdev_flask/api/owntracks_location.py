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
from owntracks_config import OWNTRACKS_CONFIG


owntracks_location = Blueprint("owntracks_location", __name__)
# openssl -hex 32


@owntracks_location.route("/", methods=["POST"])
def post_location():
    auth = request.authorization

    configuration_json = {
        "_type": "cmd",
        "action": "setConfiguration",
        "configuration": OWNTRACKS_CONFIG
    }

    exceptional_user_config = OWNTRACKS_CONFIG.copy()
    exceptional_user_config['username'] = "1420"
    exceptional_user_config['password'] = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxNDIwIn0.WpHAag6dDK24Ppm3f0LTjG3oNVltH2284PmCJBb3Nqk"
    exceptional_user_config = {
        "_type": "cmd",
        "action": "setConfiguration",
        "configuration": exceptional_user_config
    }

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
        return jsonify(configuration_json)
    # компиляция insert в строку и добавление в очередь на исполнение в redis
    insert_statement = insert(OwnTracksLocation)\
        .values(**obj, employee_id=auth.username)\
        .compile(compile_kwargs={"literal_binds": True})
    try:
        if obj.get('created_at').date() < dt.date.today():
            # переформировать кластеры, если локации пришли позже
            redis_session.sadd(
                "owntracks_cluster_dates", str(obj.get('created_at').date())
            )
    except AttributeError:
        main_logger.info("AttributeError on created_at")
    main_logger.info(f"owntracks from {auth.username}: {obj}")
    redis_session.lpush('queue_sql', str(insert_statement))
    if obj.get("username", None) == "1373":
        return jsonify(exceptional_user_config)
    if obj.get('m', None) != 1:
        return jsonify(configuration_json)
    return jsonify({})
