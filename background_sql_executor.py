from redis import Redis
from sqlalchemy import create_engine, text, exc
import time
from config import get_config


def run_executor():
    config = get_config()
    redis_session = Redis("redis")

    engine = create_engine(config.DB,
                           echo=False,
                           pool_size=1,
                           pool_recycle=300,
                           pool_timeout=10,
                           )

    while True:
        task = redis_session.brpop('queue_sql', 30)
        if not task:
            continue
        task = task[1]

        try:
            connection = engine.connect()
        except exc.DBAPIError:
            redis_session.rpush('queue_sql', task)
            time.sleep(2)
            continue

        while task:
            try:
                connection.execute(text(task.decode('utf-8')))
                connection.commit()
            except exc.DBAPIError:
                redis_session.lpush('queue_sql_emergency', task)
            task = redis_session.rpop('queue_sql')
        connection.close()


if __name__ == '__main__':
    run_executor()
