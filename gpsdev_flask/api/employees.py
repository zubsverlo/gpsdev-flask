from flask import Blueprint, send_file
from gpsdev_flask import db_session
from gpsdev_flask.models import Employees, Journal, Statements
from sqlalchemy import update, delete, select, insert
from sqlalchemy import func
from flask import jsonify, request, g
from flask_login import current_user
from marshmallow import ValidationError
from gpsdev_flask.ma_schemas import EmployeesSchema
from gpsdev_flask.api.error_responses import (not_found_404,
                                              not_allowed_403,
                                              validation_error_422,
                                              mts_error_422)
from gpsdev_flask.api import api_login_required
import datetime as dt
from trajectory_report.api.mts import update_name
from jose import jwt, JWTError
from gpsdev_flask import config
from trajectory_report.exceptions import MtsException
import io
from owntracks_config import OWNTRACKS_CONFIG
import json
from gpsdev_flask import main_logger


employees = Blueprint('employees', __name__)


@employees.route('/', methods=['GET', 'POST'])
@api_login_required
def employees_many():
    if request.method == "GET":
        res = db_session.query(Employees)\
            .filter(Employees.division.in_(current_user.access_list))\
            .all()
        if not res:
            return not_found_404()
        res = EmployeesSchema(many=True).dump(res)
        return jsonify(res)

    if request.method == "POST":
        schema = EmployeesSchema()
        try:
            new_emp = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)
        new_emp_db = Employees(**new_emp)

        db_session.add(new_emp_db)
        db_session.commit()
        db_session.refresh(new_emp_db)
        return jsonify(schema.dump(new_emp_db)), 201


@employees.route('/<int:name_id>', methods=['GET', 'PATCH', 'DELETE'])
@api_login_required
def employees_one(name_id):
    if request.method == "GET":
        res = db_session.query(Employees)\
            .filter(Employees.division.in_(current_user.access_list)) \
            .filter_by(name_id=name_id) \
            .first()
        if not res:
            return not_found_404()
        res = EmployeesSchema().dump(res)
        entry = db_session.query(Journal)\
            .filter_by(name_id=name_id)\
            .filter_by(period_end=None)\
            .first()
        if not entry:
            tracking_type = 'Не отслеживается'
        if entry.owntracks:
            tracking_type = 'owntracks'
        else:
            tracking_type = 'MTS'
        res['tracking_type'] = tracking_type
        return jsonify(res)

    if request.method == "PATCH":
        g.name_id = name_id
        schema = EmployeesSchema(partial=True)

        try:
            employee = schema.load(request.get_json())
        except ValidationError as e:
            return validation_error_422(e.messages)

        employee_from_db = db_session.query(Employees)\
            .filter(Employees.division.in_(current_user.access_list)) \
            .filter_by(name_id=name_id) \
            .first()

        if employee['name'] != employee_from_db.name:
            # если сотрудник отслеживается - переименовать в МТС
            sel = select(Journal.subscriberID)\
                .where(Journal.name_id == name_id)\
                .where(Journal.period_end == None)
            subscriber_id = db_session.execute(sel).scalar_one_or_none()
            if subscriber_id:
                update_name(subscriber_id, employee['name'])

        db_session.execute(
            update(Employees)
            .filter_by(name_id=name_id)
            .values(**employee)
        )
        db_session.commit()
        updated_employee = db_session.get(Employees, name_id)
        return jsonify(schema.dump(updated_employee))

    if request.method == "DELETE":
        emp = db_session.get(Employees, name_id)
        if not emp:
            return not_found_404()
        if current_user.rang_id != 1:
            return not_allowed_403(
                "You are not allowed to delete employees")
        delete_stmt = delete(Journal).where(Journal.name_id == emp.name_id)
        db_session.execute(delete_stmt)
        db_session.delete(emp)
        db_session.commit()
        return jsonify({}), 204


@employees.route("/fire/<int:name_id>", methods=['GET'])
@api_login_required
def fire_employee(name_id: int):
    emp = db_session.query(Employees)\
        .filter(Employees.division.in_(current_user.access_list)) \
        .filter_by(name_id=name_id) \
        .first()
    if not emp:
        return not_found_404()
    subq = select(func.max(Statements.date).label('date'))\
        .where(Statements.name_id == name_id)\
        .as_scalar()
    sel = select(Statements.division, Statements.date)\
        .where(Statements.name_id == name_id)\
        .where(Statements.date == subq)\
        .limit(1)
    division_and_date = db_session.execute(sel).fetchone()
    division = division_and_date.division
    date = division_and_date.date+dt.timedelta(days=1)

    ins = insert(Statements)\
        .values(
            division=division,
            name_id=name_id,
            date=date,
            object_id=1,
            statement="У"
    )
    db_session.execute(ins)
    db_session.commit()
    return jsonify({}), 200


@employees.route("/owntracks/connect/<int:name_id>", methods=['GET'])
@api_login_required
def owntracks_connect(name_id: int):
    # jwt generation here
    jwt_str = jwt.encode(
        {"sub": str(name_id)},
        algorithm=config.JWT_ALGORITHM,
        key=config.JWT_SECRET_KEY
    )
    config_file = OWNTRACKS_CONFIG.copy()
    config_file['password'] = jwt_str
    config_file['username'] = str(name_id)
    config_file = json.dumps(config_file)
    # write config to a file
    config_file = io.BytesIO(config_file.encode())

    emp = db_session.query(Employees)\
        .filter(Employees.division.in_(current_user.access_list)) \
        .filter_by(name_id=name_id) \
        .first()
    if not emp:
        return not_found_404()

    # get journal and check wether the emp is connected
    # if connected to owntracks - return 422 ALREADY CONNECTED or file
    # (depends on nofile parameter)
    # if connected to mts - delete from mts and open a new journal record
    # if not connected at all - just add a new journal record

    # journal manipulations here
    sel = select(
        Journal.id,
        Journal.name_id,
        Journal.subscriberID,
        Journal.owntracks,
        Journal.period_init,
        Journal.period_end,
    ).where(Journal.name_id == name_id).where(Journal.period_end == None)
    journal = db_session.execute(sel).fetchone()
    # new employee to connect, just add a journal entry
    if not journal:
        db_session.add(
            Journal(
                name_id=name_id,
                owntracks=True,
                period_init=dt.date.today(),
            )
        )
        db_session.commit()

    # the employee is connected to MTS. rename in MTS and, close journal period
    # and add a new journal entry with owntracks
    elif not journal.owntracks:
        try:
            update_name(journal.subscriberID, emp.name+" (owntracks зам.)")
        except MtsException as e:
            return mts_error_422(str(e))
        db_session.execute(
            update(Journal)
            .filter_by(id=journal.id)
            .values(period_end=dt.date.today()-dt.timedelta(days=1))
        )
        db_session.add(
            Journal(
                name_id=name_id,
                owntracks=True,
                period_init=dt.date.today(),
            )
        )
        db_session.commit()

    # if employee is already connected, just send a file
    # return if nofile argument
    if request.args.get('nofile'):
        return jsonify({}), 200

    # sending a config file here (optionally)
    return send_file(
        config_file,
        mimetype="text/plain",
        download_name=f"config_{name_id}.otrc",
    )
