import os
from dotenv import load_dotenv


load_dotenv()


class Config(object):
    FLASK_ENV = 'development'
    DEBUG = False
    TESTING = False
    SECRET_KEY = os.getenv('SECRET_KEY')
    DATABASE_ECHO = False
    DB = os.getenv('DATABASE_DEVELOPMENT')


class ProductionConfig(Config):
    FLASK_ENV = 'production'
    DB = os.getenv('DATABASE_PRODUCTION')


class DevelopmentConfig(Config):
    DEBUG = True
    DATABASE_ECHO = True


class TestingConfig(Config):
    TESTING = True


def get_config():
    env = os.getenv('ENV')
    if env == 'production':
        return ProductionConfig()
    elif env == 'testing':
        return TestingConfig()
    else:
        return DevelopmentConfig()