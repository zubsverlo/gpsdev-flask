from gpsdev_flask.celery_app import app_celery
from gpsdev_flask import redis_session
from trajectory_report.gather.coordinates import fetch_coordinates
from trajectory_report.gather.clusters_mts import make_clusters_mts
from trajectory_report.gather.clusters_owntracks import (
    remake_clusters,
    make_clusters_owntracks,
)
from trajectory_report.gather.journal import update_journal
from celery.schedules import crontab
from trajectory_report.notificators.telegram import empty_locations_notify
from trajectory_report.gather.coordinates_analysis import analyze_coordinates


@app_celery.task
def invalidate_cache(table):
    redis_session.expire(table, 0)


@app_celery.task
def set_json_cache(table, json_response):
    redis_session.set(table, json_response)


def update_coordinates():
    fetch_coordinates()
    redis_session.expireat("current_locations", 0)


@app_celery.task(name="clusters")
def clusters():
    make_clusters_mts()
    redis_session.expireat("clusters", 0)


@app_celery.task(name="clusters_owntracks")
def clusters_owntracks():
    make_clusters_owntracks()


@app_celery.task(name="remake_clusters_owntracks")
def remake_clusters_owntracks():
    remake_clusters()


@app_celery.task(name="journal")
def journal():
    update_journal()
    redis_session.expireat("journal", 0)


@app_celery.task(name="no_locations_notify")
def no_locations_notify():
    empty_locations_notify()


@app_celery.task(name="coordinates_analysis")
def coordinates_analysis():
    analyze_coordinates()


app_celery.conf.beat_schedule = {
    "fetch-coords-every-2-mins": {
        "task": "update_coordinates",
        "schedule": crontab(minute="*/2"),
    },
    "fetch-clusters-every-three-hours": {
        "task": "clusters",
        "schedule": crontab(minute="30", hour="*/3"),
    },
    "fetch-clusters-owntracks-every-three-hours": {
        "task": "clusters_owntracks",
        "schedule": crontab(minute="35", hour="*/3"),
    },
    "remake-clusters-owntracks-every-four-hours": {
        "task": "remake_clusters_owntracks",
        "schedule": crontab(minute="50", hour="*/4"),
    },
    "update-journal-every-10-mins": {
        "task": "journal",
        "schedule": crontab(minute="*/10"),
    },
    "empty-locations-notify-every-hour": {
        "task": "no_locations_notify",
        "schedule": crontab(minute="0", hour="9-22"),
    },
    "analyze-coordinates-every-three-hours": {
        "task": "coordinates_analysis",
        "schedule": crontab(minute="30", hour="*/3"),
    },
}
