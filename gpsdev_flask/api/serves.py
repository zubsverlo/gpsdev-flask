from flask import Blueprint
from gpsdev_flask import db_session
from gpsdev_flask.models import Serves
from sqlalchemy import update, delete
from flask import jsonify, request
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import ServesSchema, ServesWithCoordinatesSchema
from gpsdev_flask.api.error_responses import (validation_error_422,
                                              report_error_422)
from trajectory_report.map import MapMovements
from trajectory_report.exceptions import ReportException
from gpsdev_flask.api import api_login_required
from gpsdev_flask import main_logger
from flask_login import current_user
import datetime as dt


serves = Blueprint('serves', __name__)


@serves.route('/', methods=['POST', 'PATCH'])
@api_login_required
def route_main():
    if request.method == 'POST':
        schema = ServesSchema(many=True)
        try:
            new_serves = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        for serv in new_serves:
            exists = db_session.query(Serves).filter_by(
                object_id=serv['object_id'],
                name_id=serv['name_id'],
                date=serv['date'],
            ).first()
            if exists:
                return validation_error_422("Служебная записка уже добавлена")
            db_session.add(Serves(author_id=current_user.id, **serv))

        db_session.commit()
        return jsonify(schema.dump(new_serves)), 201

    if request.method == 'PATCH':
        schema = ServesSchema(many=True, exclude=['comment'])
        try:
            new_serves = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        for serv in new_serves:
            exists = db_session.query(Serves).filter_by(
                object_id=serv['object_id'],
                name_id=serv['name_id'],
                date=serv['date'],
            ).first()
            if not exists:
                return validation_error_422(f"Служебная записка отсутствует")
            db_session.execute(
                update(Serves)
                .filter_by(
                    object_id=serv['object_id'],
                    name_id=serv['name_id'],
                    date=serv['date']
                )
                .values(
                    approval=serv['approval'],
                    approver_id=current_user.id,
                    approve_tst=dt.datetime.now()
                )
            )
        db_session.commit()
        return jsonify({}), 200


@serves.route('/get', methods=['POST'])
@api_login_required
def serves_get():
    """Нужен список из объектов с параметрами: name_id, object_id, date"""
    schema = ServesSchema(many=True, only=['name_id', 'object_id', 'date'])
    try:
        requested = schema.load(request.get_json())
    except ValidationError as e:
        main_logger.info(e)
        return validation_error_422(e.messages)
    result = []
    for i in requested:
        main_logger.info(i)
        result.append(
            db_session.query(Serves).filter_by(**i).first()
        )
    main_logger.info(result)
    return jsonify(ServesSchema(many=True).dump(result))


@serves.route('/delete', methods=['POST'])
@api_login_required
def serves_delete():
    schema = ServesSchema(many=True, exclude=['comment'])
    try:
        new_serves = schema.load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)

    for serv in new_serves:
        db_session.execute(
            delete(Serves)
            .filter_by(
                object_id=serv['object_id'],
                name_id=serv['name_id'],
                date=serv['date']
            )
        )
    db_session.commit()
    return jsonify({}), 204


@serves.route('/with-coordinates', methods=['POST'])
@api_login_required
def check_coordinates():
    try:
        new_s = ServesWithCoordinatesSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = MapMovements(new_s['name_id'],
                         new_s['date'],
                         new_s['division'])
    except ReportException as e:
        return report_error_422(str(e))
    result = r.check_by_coordinates(new_s['latitude'],
                                    new_s['longitude'])
    if result:
        exists = db_session.query(Serves).filter_by(
            object_id=new_s['object_id'],
            name_id=new_s['name_id'],
            date=new_s['date'],
        ).first()
        if exists:
            return validation_error_422("Служебная записка: Уже существует")
        db_session.add(Serves(name_id=new_s['name_id'],
                              object_id=new_s['object_id'],
                              date=new_s['date'],
                              comment=new_s['comment'],
                              address=new_s['address'],
                              approver_id=current_user.id,
                              approve_tst=dt.datetime.now(),
                              author_id=current_user.id,
                              create_tst=dt.datetime.now(),
                              approval=1))

        db_session.commit()
        return jsonify({}), 201
    return validation_error_422('Адрес: Не подтверждено')
