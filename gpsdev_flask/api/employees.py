from flask import Blueprint
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
                                              validation_error_422)
from gpsdev_flask.api import api_login_required
import datetime as dt
from trajectory_report.api.mts import update_name


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
