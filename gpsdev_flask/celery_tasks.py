from gpsdev_flask.celery_app import app_celery
from gpsdev_flask import redis_session


@app_celery.task
def invalidate_cache(table):
    redis_session.expire(table, 0)


@app_celery.task
def set_json_cache(table, json_response):
    redis_session.set(table, json_response)
