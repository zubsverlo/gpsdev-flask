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

fields.Field.default_error_messages["required"] = "Обязательное поле"
fields.Field.default_error_messages["null"] = "Поле не может быть null"
fields.Field.default_error_messages["validator_failed"] = "Некорретное значение"


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
    name = fields.String(required=True, validate=validate.Length(
        max=100,
        error="Имя должно быть в пределах 100 символов")
    )
    hire_date = fields.Date(load_default=dt.date.today())
    quit_date = fields.Date(allow_none=True)
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
    no_tracking = fields.Boolean(load_default=False)
    bath_attendant = fields.Boolean(load_default=False)
    staffer = fields.Boolean(load_default=False)

    @validates('name')
    def validate_name(self, name):
        if g.get('name_id') and db_session.query(Employees) \
                .filter_by(name=name) \
                .filter(Employees.name_id != g.name_id) \
                .first():
            raise ValidationError(f"{name} уже существует")
        if not g.get('name_id') and db_session.query(Employees)\
                .filter_by(name=name)\
                .first():
            raise ValidationError(f"{name} уже существует")

    @validates('division')
    def validate_division(self, division):
        if division not in current_user.access_list:
            raise ValidationError(
                "Вы не можете использовать указанное подразделение")

    @validates('schedule')
    def validate_schedule(self, schedule):
        if schedule not in (1, 2):
            raise ValidationError('Должность должна быть 1 или 2')

    @validates('phone')
    def validate_phone(self, phone):
        if len(phone) != 11:
            raise ValidationError('Номер не должен превышать 11 символов')

    @pre_load
    def load_phone(self, data, **kwargs):
        if data.get('phone'):
            data['phone'] = ''.join(re.findall(r"[0-9]", data['phone']))
        return data
    
    @pre_load
    def load_name(self, data, **kwargs):
        name = data.get('name')
        if name:
            data['name'] = " ".join(name.split())
        return data


class ObjectSchema(Schema):
    object_id = fields.Integer(dump_only=True)
    name = fields.String(required=True, validate=validate.Length(
        max=100, error="Имя должно быть в пределах 100 символов"))
    address = fields.String(required=True)
    latitude = fields.Float(required=True)
    longitude = fields.Float(required=True)
    division = fields.Integer(required=True)
    phone = fields.String(
        validate=validate.Length(
            max=200,
            error="Контактные данные должны быть в пределах 200 символов"
        )
    )
    no_payments = fields.Boolean(load_default=False)
    income = fields.Float(allow_none=True)
    active = fields.Boolean(load_default=True)
    admission_date = fields.Date(allow_none=True)
    denial_date = fields.Date(allow_none=True)
    apartment_number = fields.String(
        validate=validate.Length(
            max=50,
            error='Нужно уложиться в 50 символов для номера квартиры'
            )
        )
    personal_service_after_revision = fields.String(
        validate=validate.Length(
            max=70,
            error='Нужно уложиться в 70 символов'
        )
    )
    division_name = fields.Pluck(
        DivisionSchema, 'division', attribute='division_ref', dump_only=True
        )
    comment = fields.String(
        validate=validate.Length(
            max=200,
            error="Комментарий быть в пределах 200 символов"
        )
    )

    @validates('division')
    def validate_division(self, value):
        if value not in current_user.access_list:
            raise ValidationError("Вы не можете использовать "
                                  "указанное подразделение")

    @validates_schema
    def validate_unique_name(self, data, **kwargs):
        existing_objects = None
        if not g.get('p_object'):
            existing_objects = db_session.query(ObjectsSite) \
                .filter_by(name=data['name'], division=data['division']) \
                .all()
            if existing_objects:
                raise ValidationError(
                    "Уже используется в указанном подразделении"
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
                "Уже используется в указанном подразделении"
            )
    
    @pre_load
    def load_name(self, data, **kwargs):
        name = data.get('name')
        if name:
            data['name'] = " ".join(name.split())
        return data


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
            raise ValidationError("period_init не может быть позже period_end")
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

        if 'access_set' in data.keys():
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
    comment = fields.String(validate=validate.Length(
        max=200, error="Комментарий не должен превышать 200 символов"),
                            required=True)
    approval = fields.Integer(load_default=3, validate=validate.OneOf([1, 3]))
    address = fields.String(validate=validate.Length(
        max=255, error="Адрес не должен превышать 255 символов"))
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
            raise ValidationError('Вы не можете подтверждать служебки!')
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
        if data['value'] in "БОУН" and data['value']:
            data['object_id'] = 1
        return data
    
    @validates_schema
    def validate_value(self, data, **kwargs):
        if data['value'] == "В" and data['object_id'] == 1:
            raise ValidationError("Нельзя проставить В для "
                                  "БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ.")

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
            raise ValidationError("Конечная дата должна быть больше начальной "
                                  "даты, или они должны быть идентичны.")

    @validates_schema
    def validate_params(self, data, **kwargs):
        if data.get('division') and \
                (data.get('name_ids') or data.get('object_ids')):
            raise ValidationError("Указывая список сотрудников или объектов, "
                                  "вы не можете указать подразделение.")


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
            raise ValidationError("Вы пытаетесь запросить отчет за день, "
                                  "который ещё не наступил.")


class ServesWithCoordinatesSchema(Schema):
    name_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    date = fields.Date(required=True)
    division = fields.Integer(required=True)
    longitude = fields.Float(required=True)
    latitude = fields.Float(required=True)
    comment = fields.String(validate=validate.Length(
        max=200, error="Комментарий не должен превышать 200 символов"
    ), required=True)
    address = fields.String(validate=validate.Length(
        max=200, error="Комментарий не должен превышать 200 символов"))


class LoginSchema(Schema):
    phone = fields.Integer(required=True)
    password = fields.String(required=True)
    remember = fields.Boolean()

    @validates_schema
    def check_password_and_login(self, data, **kwargs):
        user = db_session.query(User).filter_by(phone=data['phone']).first()
        if not user:
            raise ValidationError('Неправильный номер или пароль')
        if not bcrypt.check_password_hash(user.password, data['password']):
            raise ValidationError('Неправильный номер или пароль')
        login_user(user, remember=data.get('remember', False))
        return data


class CommentSchema(Schema):
    division_id = fields.Integer(required=True)
    employee_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    comment = fields.String(validate=validate.Length(
        max=250, error="Комментарий не должен превышать 250 символов"
    ), required=True)

    @post_load
    def strip_comment(self, data, **kwargs):
        data['comment'] = data['comment'].strip()
        return data


class FrequencySchema(Schema):
    division_id = fields.Integer(required=True)
    employee_id = fields.Integer(required=True)
    object_id = fields.Integer(required=True)
    frequency = fields.String(
        validate=validate.Length(
            max=250, 
            error="Длина для кол-ва выходов не более 3 символов!"
            ),
        required=True,
        allow_none=True)


class OwnTracksLocationSchema(Schema):
    id = fields.Integer(dump_only=True)
    employee_id = fields.Integer(required=False)
    bssid = fields.String(validate=validate.Length(max=32), data_key="BSSID")
    ssid = fields.String(validate=validate.Length(max=32), data_key="SSID")
    acc = fields.Integer()
    batt = fields.Integer()
    bs = fields.Integer()
    conn = fields.String(validate=validate.Length(max=1))
    created_at = fields.Integer(required=False)
    lat = fields.Float(required=True)
    lon = fields.Float(required=True)
    m = fields.Integer()
    t = fields.String(validate=validate.Length(max=1))
    tst = fields.Integer(required=True)
    vel = fields.Integer()
    
    @post_dump
    def datetimes(self, data, **kwargs):
        timezone = dt.timezone(dt.timedelta(hours=2))
        if data.get('created_at'):
            data['created_at'] = dt.datetime\
                .fromtimestamp(data['created_at'], tz=timezone)\
                .isoformat()

        if data.get('tst'):
            data['tst'] = dt.datetime\
                .fromtimestamp(data['tst'], tz=timezone)\
                .isoformat()
        return data
    

class ObjectStatementPermit(Schema):
    allow = fields.Bool(required=True)
    date = fields.Date(required=True)