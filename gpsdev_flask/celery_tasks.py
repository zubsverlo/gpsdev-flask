from gpsdev_flask.celery_app import app_celery
from gpsdev_flask import redis_session
from trajectory_report.gather.coordinates import fetch_coordinates
from trajectory_report.gather.clusters import make_clusters
from trajectory_report.gather.journal import update_journal
from celery.schedules import crontab


@app_celery.task
def invalidate_cache(table):
    redis_session.expire(table, 0)


@app_celery.task
def set_json_cache(table, json_response):
    redis_session.set(table, json_response)


@app_celery.task(name='update_coordinates')
def update_coordinates():
    fetch_coordinates()
    redis_session.expireat('current_locations', 0)


@app_celery.task(name='clusters')
def clusters():
    make_clusters()
    redis_session.expireat('clusters', 0)


@app_celery.task(name='journal')
def journal():
    update_journal()
    redis_session.expireat('journal', 0)


app_celery.conf.beat_schedule = {
    'fetch-coords-every-2-mins': {
        'task': 'update_coordinates',
        'schedule': crontab(minute='*/2')
    },
    'fetch-clusters-every-three-hours': {
        'task': 'clusters',
        'schedule': crontab(minute='30', hour='*/3')
    },
    'update-journal-every-3-mins': {
        'task': 'journal',
        'schedule': crontab(minute='*/3')
    }
}
