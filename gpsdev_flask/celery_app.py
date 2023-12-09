from celery import Celery
from config import get_config

app_config = get_config()
app_celery = Celery('gpsdev_flask',
                    broker='redis://'+app_config.REDIS,
                    include=["gpsdev_flask.celery_tasks"],
                    timezone="Europe/Moscow")

if __name__ == "__main__":
    app_celery.start()
