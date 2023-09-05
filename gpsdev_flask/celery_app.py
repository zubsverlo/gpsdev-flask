from celery import Celery

app_celery = Celery('gpsdev_flask',
                    broker='redis://redis',
                    include=["gpsdev_flask.celery_tasks"])

if __name__ == "__main__":
    app_celery.start()
