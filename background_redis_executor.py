from redis import Redis


def run_executor():
    redis_session = Redis('redis')

    while True:
        task = redis_session.brpop('queue_redis', 30)
        if not task:
            continue
        task = task[1]
        while task:
            task = task.decode('utf-8')
            task = task.split(',')
            val = task.pop()
            key = ','.join(task)
            if val == "":
                redis_session.hdel('statements', key)
            else:
                redis_session.hset('statements', key, val)

            task = redis_session.rpop('queue_redis')


if __name__ == '__main__':
    run_executor()
