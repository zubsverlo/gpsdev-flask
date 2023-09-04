from redis import Redis
from sqlalchemy import create_engine, text
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
        task = redis_session.rpop('queue_sql')
        if not task:
            time.sleep(0.5)
            continue
        with engine.connect() as connection:
            while task:
                connection.execute(text(task.decode('utf-8')))
                connection.commit()
                task = redis_session.rpop('queue_sql')
            connection.close()


if __name__ == '__main__':
    run_executor()
