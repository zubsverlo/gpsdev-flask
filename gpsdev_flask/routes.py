from gpsdev_flask.api.report import report
from gpsdev_flask.api.auth import auth_bp
from gpsdev_flask.api.objects import objects
from gpsdev_flask.api.one_employee_report import one_employee_report
from gpsdev_flask.api.employees import employees
from gpsdev_flask.api.journal import journal
from gpsdev_flask.api.users import users
from gpsdev_flask.api.serves import serves
from gpsdev_flask.api.address_lookup import address_lookup
from gpsdev_flask.api.mts import mts
from gpsdev_flask.api.statements import statements
from gpsdev_flask.api.divisions import divisions
from gpsdev_flask.pages import pages
from flask_swagger_ui import get_swaggerui_blueprint
from gpsdev_flask.api.comment import comment
from gpsdev_flask.api.frequency import frequency


def register_blueprints(app):
    app.register_blueprint(report, url_prefix='/api/report')
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(objects, url_prefix='/api/objects')
    app.register_blueprint(one_employee_report,
                           url_prefix='/api/one-employee-report')
    app.register_blueprint(employees, url_prefix='/api/employees')
    app.register_blueprint(journal, url_prefix='/api/journal')
    app.register_blueprint(users, url_prefix='/api/users')
    app.register_blueprint(serves, url_prefix='/api/serves')
    app.register_blueprint(address_lookup, url_prefix='/api/address-lookup')
    app.register_blueprint(mts, url_prefix='/api/mts')
    app.register_blueprint(statements, url_prefix='/api/statements')
    app.register_blueprint(pages, url_prefix='/')
    app.register_blueprint(register_swagger(app))
    app.register_blueprint(divisions, url_prefix='/api/divisions')
    app.register_blueprint(comment, url_prefix='/api/comment')
    app.register_blueprint(frequency, url_prefix='/api/frequency')


def register_swagger(app):
    SWAGGER_URL = '/api/docs'  # URL for exposing Swagger UI (without trailing '/')
    API_URL = '/swagger.json'
    bp = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL
    )
    return bp

