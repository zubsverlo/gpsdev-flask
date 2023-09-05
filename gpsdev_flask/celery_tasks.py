import sqlalchemy.exc

from gpsdev_flask.celery_app import app_celery
from gpsdev_flask import db_session, redis_session
from sqlalchemy import text
import pandas as pd
from trajectory_report.report.ConstructReport import CachedReportDataGetter
import datetime as dt
import bz2
import pickle


@app_celery.task
def statements_task(tasks):
    db_session.rollback()
    print(db_session.info)
    for task in tasks:
        db_session.execute(text(task))
    db_session.commit()
    update_redis_cache.delay('statements')


@app_celery.task
def update_redis_cache(table):
    cache_date_from = \
        ((dt.date.today().replace(day=1) - dt.timedelta(days=1))
         .replace(day=1))
    try:
        res = db_session.execute(CachedReportDataGetter.CACHED_SELECTS[table](
                date_from=cache_date_from)).all()
        res = pd.DataFrame(res)
    except sqlalchemy.exc.OperationalError:
        redis_session.delete(table)
        return
    redis_session.set(table, bz2.compress(pickle.dumps(res)))
    return


@app_celery.task
def update_json_cache(table, json_response):
    redis_session.set(table, json_response)


@app_celery.task
def clear_json_cache(table):
    redis_session.delete(table)
