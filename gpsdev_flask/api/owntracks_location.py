import datetime as dt

from flask import Blueprint, jsonify, request
from jose import JWTError, jwt
from marshmallow import EXCLUDE, ValidationError
from owntracks_config import OWNTRACKS_CONFIG
from sqlalchemy.sql import insert

from gpsdev_flask import config, main_logger, redis_session
from gpsdev_flask.api.error_responses import not_allowed_403
from gpsdev_flask.ma_schemas import OwnTracksLocationSchema
from gpsdev_flask.models import OwnTracksLocation

owntracks_location = Blueprint("owntracks_location", __name__)
STATUS_EXPIRE_SECONDS = 4 * 60 * 60


@owntracks_location.route("/", methods=["POST"])
def post_location():
    auth = request.authorization

    configuration_json = {
        "_type": "cmd",
        "action": "setConfiguration",
        "configuration": OWNTRACKS_CONFIG,
    }
    request_status = {
        "_type": "cmd",
        "action": "status",
    }

    # Если нужно кому-то индивидуально поменять настройки,
    # можно прокинуть это здесь
    # exceptional_user_config = OWNTRACKS_CONFIG.copy()
    # exceptional_user_config['username'] = ""
    # exceptional_user_config['password'] = ""
    # exceptional_user_config = {
    #     "_type": "cmd",
    #     "action": "setConfiguration",
    #     "configuration": exceptional_user_config
    # }
    employee_ids_with_status: list[str] = redis_session.hkeys("status")
    main_logger.info(request.get_json())

    if request.get_json().get("_type") == "status":
        status_result = None
        bo = request.get_json().get("android").get("bo") == 0
        loc = request.get_json().get("android").get("loc") == 0
        main_logger.info((bo, loc))
        match (bo, loc):
            case [True, True]:
                status_result = "ok"
            case [False, True]:
                status_result = "batt"
            case [True, False]:
                status_result = "loc"
            case [False, False]:
                status_result = "batt, loc"
        redis_session.hset("status", auth.username, status_result)
        redis_session.hexpire("status", STATUS_EXPIRE_SECONDS, auth.username)
        return jsonify({})

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
        return jsonify(configuration_json)
    # компиляция insert в строку и добавление в очередь на исполнение в redis
    insert_statement = (
        insert(OwnTracksLocation)
        .values(**obj, employee_id=auth.username)
        .compile(compile_kwargs={"literal_binds": True})
    )
    try:
        if obj.get("created_at").date() < dt.date.today():
            # переформировать кластеры, если локации пришли позже
            redis_session.sadd(
                "owntracks_cluster_dates", str(obj.get("created_at").date())
            )
    except AttributeError:
        main_logger.info("AttributeError on created_at")
    main_logger.info(f"owntracks from {auth.username}: {obj}")
    redis_session.lpush("queue_sql", str(insert_statement))
    tls_connection = request.headers.get("X-Forwarded-Proto") == "https"
    main_logger.info(f"tls_connection: {tls_connection}")
    if obj.get("m", None) != 1 or not tls_connection:
        return jsonify(configuration_json)
    if auth.username.encode() not in employee_ids_with_status:
        redis_session.hset("status", auth.username, "waiting")
        redis_session.hexpire("status", STATUS_EXPIRE_SECONDS, auth.username)
        return jsonify(request_status)
    return jsonify({})
