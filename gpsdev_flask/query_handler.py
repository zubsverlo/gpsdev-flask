# данный скрипт задуман как фоновый сервис, предназначенный для
# выполнения скопленных задач на выполнение в базе данных.
# задача в том, чтобы ускорить обработку изменений в таблице выходов сотрудников
# задачи на выполнение могут приходить в неограниченном размере и неограниченно
# маленький промежуток времени. основной сервер для обр
import queue
import threading
import time
import logging

TASKS_QUEUE = queue.Queue()


class BackgroundQueriesHandler(threading.Thread):
    def __init__(self, db, **kwargs):
        super().__init__(**kwargs)
        self._stop_event = threading.Event()
        self.db_session = db
        self.i = 0
        logging.info('BQH инициирован')

    def stop(self) -> None:
        self._stop_event.set()

    def _stopped(self) -> bool:
        return self._stop_event.is_set()

    def run(self) -> None:
        logging.info('BQH run запущен')
        logging.info(f"BQH состояние self._stopped: {self._stopped()}")
        while not self._stopped():
            self.handle()

    def handle(self) -> None:
        try:
            task = TASKS_QUEUE.get(block=False)
            if task == "commit":
                # self.db.session.commit()
                pass
            else:
                self.db_session.execute(task)
                self.i += 1

        except queue.Empty:
            time.sleep(0.5)
            if self.i > 0:
                self.db_session.commit()
                print(f'handler executed {int(self.i)} tasks')
                self.i = 0
