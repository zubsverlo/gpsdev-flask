from flask import Flask
from flask_bcrypt import Bcrypt
from gpsdev_flask.database import create_db_session
from flask_login import LoginManager
from flask import json
from gpsdev_flask.models import User
from gpsdev_flask.query_handler import BackgroundQueriesHandler, TASKS_QUEUE
from redis import Redis
from config import get_config
import logging


main_logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)
# from gpsdev_flask.models import Base

config = get_config()
db_session = create_db_session(config)
login_manager = LoginManager()
bcrypt = Bcrypt()
redis_session = Redis(config.REDIS)
# Base.metadata.create_all(db_session.get_bind())


def create_app():
    app = Flask(__name__)
    app.config.from_object(config)
    app.url_map.strict_slashes = False
    # Чтобы json выдавал не выдавал кириллицу в формате \u9437 - нужно
    # отключить ensure_ascii
    json.provider.DefaultJSONProvider.ensure_ascii = False

    @app.teardown_appcontext
    def shutdown_session(exception=None):
        db_session.remove()

    login_manager.init_app(app)
    login_manager.login_view = "/login"

    @login_manager.user_loader
    def load_user(user_id):
        return db_session.get(User, int(user_id))

    bcrypt.init_app(app)

    # Прокинуть все routes:
    from gpsdev_flask.routes import register_blueprints

    register_blueprints(app)

    return app
