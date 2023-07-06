import os
from gpsdev_flask import create_app, db_session
from gpsdev_flask.models import Employees
import pytest
from sqlalchemy import delete


@pytest.fixture(scope='module')
def test_client():
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    os.environ['NO_BQH'] = 'true'
    flask_app = create_app()

    with flask_app.test_client() as test_client:
        with flask_app.app_context():
            yield test_client


@pytest.fixture(scope='module')
def client_authorized():
    os.environ['CONFIG_TYPE'] = 'config.TestingConfig'
    os.environ['NO_BQH'] = 'true'
    flask_app = create_app()

    with flask_app.test_client() as client_authorized:
        with flask_app.app_context():
            client_authorized.post(
                '/api/auth/login',
                json={'phone': 79999774705, 'password': 'testicles737'})
            clear_db_before_tests()
            yield client_authorized


def clear_db_before_tests():
    emps = db_session.query(Employees)\
        .filter(Employees.name.in_(['Тест Сотрудник',
                                    'Тест Сотрудник (переименован)']))\
        .all()
    for emp in emps:
        db_session.delete(emp)
    db_session.commit()
