from gpsdev_flask import bcrypt
from marshmallow import Schema, fields, ValidationError
import datetime as dt
import re
from flask_login import current_user, login_user
from marshmallow import (validates,
                         validates_schema,
                         validate,
                         post_load,
                         post_dump,
                         pre_load)
from gpsdev_flask import db_session
from gpsdev_flask.models import ObjectsSite, Employees, Division, User
from flask import g
from sqlalchemy import text, or_


class PhoneNumber(fields.Field):
    def _deserialize(self, value, attr, data, **kwargs):
        return ''.join(re.findall(r"[0-9]", value))


class RangSchema(Schema):
    id = fields.Integer()
    rang = fields.String()


class ScheduleSchema(Schema):
    schedule = fields.String()


class DivisionSchema(Schema):
    id = fields.Integer()
    division = fields.String()


class EmployeesSchema(Schema):
    name_id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(max=100))
    hire_date = fields.Date(load_default=dt.date.today())
    quit_date = fields.Date()
    division_name = fields.Pluck(
        DivisionSchema, 'division', attribute='division_ref', dump_only=True
    )
    schedule_name = fields.Pluck(
        ScheduleSchema, 'schedule', attribute='schedule_ref', dump_only=True
    )
    phone = fields.String(required=True)
    address = fields.String()
    division = fields.Integer(required=True)
    schedule = fields.Integer(load_default=1)

    @validates('name')
    def validate_name(self, name):
        if g.get('name_id') and db_session.query(Employees) \
                .filter_by(name=name) \
                .filter(Employees.name_id != g.name_id) \
                .first():
            raise ValidationError(f"{name} already exists")
        if not g.get('name_id') and db_session.query(Employees)\
                .filter_by(name=name)\
                .first():
            raise ValidationError(f"{name} already exists")

    @validates('division')
    def validate_division(self, division):
        if division not in current_user.access_list:
            raise ValidationError(
                "You are not allowed to add to this division")

    @validates('schedule')
    def validate_schedule(self, schedule):
        if schedule not in (1, 2):
            raise ValidationError('Schedule should be 1 or 2')

    @validates('phone')
    def validate_phone(self, phone):
        if len(phone) != 11:
            raise ValidationError(f'Phone number should be exactly 11 digits, '
                                  f'you provided {phone} ({len(phone)})')

    @pre_load
    def load_phone(self, data, **kwargs):
        if data.get('phone'):
            data['phone'] = ''.join(re.findall(r"[0-9]", data['phone']))
        return data


class ObjectSchema(Schema):
    object_id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(max=100))
    address = fields.String(required=True)
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    division = fields.Integer(required=True)
    phone = fields.String(validate=validate.Length(max=200))
    no_payments = fields.Boolean(load_default=False)
    active = fields.Boolean(load_default=True)
    division_name = fields.Pluck(
        DivisionSchema, 'division', attribute='division_ref', dump_only=True
    )

    @validates('division')
    def validate_division(self, value):
        if value not in current_user.access_list:
            raise ValidationError("You are not allowed to use this division")

    @validates_schema
    def validate_unique_name(self, data, **kwargs):
        existing_objects = None
        if not g.get('p_object'):
            existing_objects = db_session.query(ObjectsSite) \
                .filter_by(name=data['name'], division=data['division']) \
                .all()
            if existing_objects:
                raise ValidationError(
                    "Duplicated names in the same group are not allowed"
                )
            return None
        if data.get('division') and data.get('name'):
            existing_objects = db_session.query(ObjectsSite) \
                .filter_by(name=data['name'], division=data['division']) \
                .filter(ObjectsSite.object_id != g.p_object.object_id) \
                .all()
        elif data.get('name'):
            existing_objects = db_session.query(ObjectsSite) \
                .filter_by(name=data['name'], division=g.p_object.division) \
                .filter(ObjectsSite.object_id != g.p_object.object_id) \
                .all()
        elif data.get('division'):
            existing_objects = db_session.query(ObjectsSite) \
                .filter_by(name=g.p_object.name, division=data['division']) \
                .filter(ObjectsSite.object_id != g.p_object.object_id) \
                .all()
        if existing_objects:
            raise ValidationError(
                "Duplicated names in the same group are not allowed"
            )


class JournalSchema(Schema):
    id = fields.Integer(dump_only=True)
    name_id = fields.Integer()
    subscriberID = fields.Integer()
    period_init = fields.Date()
    period_end = fields.Date()
    name = fields.Pluck(
        EmployeesSchema, 'name', attribute='name', dump_only=True
    )
    division_name = fields.Pluck(
        EmployeesSchema, 'division_name', attribute='name', dump_only=True
    )

    @validates_schema
    def validate_periods(self, data, **kwargs):
        subscriber = data.get('subscriberID', g.record.subscriberID)
        init = data.get('period_init', g.record.period_init)
        end = data.get('period_end', g.record.period_end)
        if init > end:
            raise ValidationError("period_init can't be more than period_end")
        sel = text(
            f"select * from journal_site where "
            f"subscriberID = {subscriber} and "
            f"((period_init >= '{init}' and period_end <= '{end}') or "
            f"(period_init >= '{init}' and period_init <= '{end}' and "
            f"period_end is NULL) or "
            f"('{init}' between period_init and period_end) or "
            f"('{end}' between period_init and period_end)) and "
            f"id != '{g.record.id}'"
        )
        records_in_sum = db_session.execute(sel).all()
        if records_in_sum:
            raise ValidationError(f"Can't proceed. Check for other entries "
                                  f"with {subscriber} subscriberID")


class UserSchema(Schema):
    id = fields.Integer(dump_only=True)
    rang_id = fields.Integer(required=True)
    name = fields.String(validate=validate.Length(max=50), required=True)
    phone = fields.String(validate=validate.Length(max=11), required=True)
    access_set = fields.List(fields.Raw(), load_only=True, required=True)
    access = fields.List(fields.Raw(), required=True, dump_only=True)
    password = fields.String(validate=validate.Length(max=60), load_only=True,
                             required=True)
    rang = fields.Pluck(RangSchema, 'rang', attribute='rang', dump_only=True)

    @post_load
    def load_password_and_access(self, data, **kwargs):
        if data.get('password'):
            new_password = data['password']
            pswd = bcrypt.generate_password_hash(new_password).decode('utf-8')
            data['password'] = pswd

        if data.get('access_set'):
            access = data['access_set']
            res = db_session.query(Division)\
                .filter(
                or_(Division.id.in_(access),
                    Division.division.in_(access)
                    )
                ).all()
            del data['access_set']
            data['access'] = res

        return data

    @post_dump
    def dump_access(self, data, **kwargs):
        if data.get('access'):
            access = data['access']
            access_processed = [{"division_id": i.id,
                                 "division": i.division} for i in access]
            data['access'] = access_processed
        return data


class ServesSchema(Schema):
    id = fields.Integer(dump_only=True)
    name_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    comment = fields.String(validate=validate.Length(max=200), required=True)
    approval = fields.Integer(load_default=3, validate=validate.OneOf([1, 3]))
    name = fields.Pluck(
        EmployeesSchema(only=['name']),
        'name', attribute='employee', dump_only=True
    )
    object = fields.Pluck(
        ObjectSchema(only=['name']),
        'name', attribute='object', dump_only=True
    )

    @post_load
    def post_load(self, data, **kwargs):
        if current_user.rang_id not in (1, 2) and data.get('approval') == 1:
            raise ValidationError('You are not allowed to approve serves!')
        return data


class StatementsSchema(Schema):
    name_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    division = fields.Integer(required=True)
    date = fields.Date(required=True)
    value = fields.String(
        required=True,
        validate=validate.OneOf(["", "В", "Б", "О", "У", "Н"])
    )

    @post_load
    def change_object_id(self, data, **kwargs):
        if data['value'] in "БОУН":
            data['object_id'] = 1
        return data

    @validates('division')
    def validate_division(self, division):
        if division not in g.loaded_accessed_divisions:
            raise ValidationError(
                "You are not allowed to change statements of this division")


class ReportSchema(Schema):
    date_from = fields.Date(required=True)
    date_to = fields.Date(required=True)
    division = fields.Raw(required=True)
    name_ids = fields.List(fields.Integer)
    object_ids = fields.List(fields.Integer)
    counts = fields.Boolean(default=False)

    @validates('division')
    def validate_division(self, value):
        if value not in current_user.access_list:
            raise ValidationError(f'You should use actual division number or '
                                  f'name, which is accessible for this user. '
                                  f'You provided: {value}')

    @validates_schema
    def validate_dates(self, data, **kwargs):
        if data['date_from'] > data['date_to']:
            raise ValidationError('date_to must be higher than date_from, '
                                  'or they must be equal')

    @validates_schema
    def validate_params(self, data, **kwargs):
        if data.get('division') and \
                (data.get('name_ids') or data.get('object_ids')):
            raise ValidationError('You can not provide division with '
                                  'name_ids or object_ids. ')


class MapMovementsSchema(Schema):
    name_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    division = fields.Raw(required=True)
    longitude = fields.Float(required=True)
    latitude = fields.Float(required=True)

    # @validates('division')
    # def validate_division(self, value):
    #     if value not in current_user.access_list:
    #         raise ValidationError(f'division is not accessible for user')

    @validates('date')
    def validate_date(self, value):
        if value > dt.date.today():
            raise ValidationError("future date cannot be processed")


class ServesWithCoordinatesSchema(Schema):
    name_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    division = fields.Integer(required=True)
    longitude = fields.Float(required=True)
    latitude = fields.Float(required=True)
    comment = fields.String(validate=validate.Length(max=200), required=True)
    address = fields.String(validate=validate.Length(max=200))


class LoginSchema(Schema):
    phone = fields.Integer(required=True)
    password = fields.String(required=True)
    remember = fields.Boolean()

    @validates_schema
    def check_password_and_login(self, data, **kwargs):
        user = db_session.query(User).filter_by(phone=data['phone']).first()
        if not user:
            raise ValidationError('wrong phone number or password')
        if not bcrypt.check_password_hash(user.password, data['password']):
            raise ValidationError('wrong phone number or password')
        login_user(user, remember=data.get('remember', False))
        return data