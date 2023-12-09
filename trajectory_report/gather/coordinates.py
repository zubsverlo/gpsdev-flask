from trajectory_report.config import TOKENS_MTS
import asyncio
import aiohttp
from trajectory_report.api.mts import get_subs_by_token, apiHttp, apiGetLocs
import datetime as dt
from trajectory_report.models import Coordinates
from trajectory_report.database import DB_ENGINE
from sqlalchemy import func, insert, select
from sqlalchemy.orm import sessionmaker, Session
from collections import defaultdict


"""
Задача - сформировать список запросов для асинхронного выполнения, результаты
обработать и сохранить в БД.

Для формирования списка запросов нужно сначала запросить список всех абонентов,
затем определить, с какого момента нужно делать запрос координат 
(если их не было вообще - запросить за последние n дней).

Ответы нужно записать в один общий dataframe, обработать результат
(отсеить ошибки, перевести в нужный формат и т.д.).

Затем выгрузить в бд.

 
"""


# Модуль для заполнения БД локациями из МТС
# Реализовано два подхода. Первый заполняет БД с самого начала,
# параллельно запрашивая локации по одному сотруднику.
# Второй подход - регулярное заполнение параллельно по всем сотрудникам,
# но запрос за непродолжительное время (с момента последней записи)

# Session = sessionmaker(db_engine)


def subscribers_last_location():
    """Берет из таблицы LastRequest даты последних запрошенных локаций
        по каждому из сотрудников."""
    with DB_ENGINE.connect() as conn:
        sel = select(
            Coordinates.subscriberID,
            func.max(Coordinates.requestDate).label('requestDate')
            )\
            .group_by(Coordinates.subscriberID)
        query = conn.execute(sel)
        res = {i.subscriberID: i.requestDate for i in query.all()
                if i.subscriberID and i.requestDate}
    return res


def ret(x):
    return dt.datetime.fromisoformat(x[:19]) \
        if str(type(x)) == "<class 'str'>" else None


def ret_str(x):
    return str(dt.datetime.fromisoformat(x[:19])) \
        if str(type(x)) == "<class 'str'>" else None


def append_coordinates(data):
    with Session(DB_ENGINE) as session:
        with session.begin():
            for data_list in data:
                for dic in data_list:
                    dic.setdefault('longitude', None)
                    dic.setdefault('latitude', None)
                    dic.setdefault('locationDate', None)
                    session.add(Coordinates(
                        requestDate=ret(dic['requestDate']),
                        subscriberID=dic['subscriberID'],
                        locationDate=ret(dic['locationDate']),
                        longitude=dic['longitude'],
                        latitude=dic['latitude']
                        )
                    )
        # из-за .begin() здесь будет автокоммит
    # session закрывается


def append_coordinates_directly(data):
    list_to_append = []
    for data_list in data:
        for dic in data_list:
            x = {'requestDate': dic.get('requestDate'),
                 'locationDate': dic.get('locationDate'),
                 'longitude': dic.get('longitude'),
                 'latitude': dic.get('latitude'),
                 'subscriberID': dic.get('subscriberID')}

            x['requestDate'] = ret_str(x.get('requestDate'))
            x['locationDate'] = ret_str(x.get('locationDate'))

            list_to_append.append(x)

    with DB_ENGINE.connect() as conn:
        conn.execute(
                insert(Coordinates.__table__),
                [dic for dic in list_to_append]
        )
    conn.commit()


def get_dates_list(last_d):
    """Создает список дат в isoformat для запроса локаций по API.
       Принимает начальную дату и время в datetime.
       Если рзница в днях между сегодня и входящей датой >= 1 -
       строит от неё список из дат по сегодняшний день.
       На выходе передаёт список из кортежей, последний из которых -
       даты со вчера на сегодня.
       Пример: [(дата начальная, дата+1день), ... ]
       Если дата сегодняшняя - возвращает один кортеж с промежутком
       до текущего момента."""
    # разница в днях между сегодня и входящей датой:
    last_date_days = (dt.datetime.today() - last_d).days
    dates_list = []  # Список кортежей с датами
    if last_date_days >= 1:  # если разница 1 день или больше
        # дата, дата+1 в заданном диапазоне дней:
        for i, o in zip(range(0, last_date_days), range(1, last_date_days+1)):
            dates_list.append(
                ((last_d + dt.timedelta(days=i)).isoformat(timespec='minutes'),
                 (last_d + dt.timedelta(days=o)).isoformat(timespec='minutes'))
            )
        return dates_list
    elif last_date_days == 0:  # если входная дата сегодняшняя
        dates_list.append(
            ((last_d+dt.timedelta(minutes=1)).isoformat(timespec='minutes'),
             dt.datetime.now().isoformat(timespec='minutes'))
        )
        return dates_list


async def fetch(sess, url, params):
    """Обработка каждого запроса отдельно. Здесь можно поймать ошибку,
       добавить ошибку в список и запросить повторно уже после.
       Успешный запрос возвращает список. Неуспешный - тип данных ошибки
       aiohttp.client_exceptions. """
    async with sess.get(url, params=params) as response:
        if response.status == 200:
            resp = await response.json()
            if type(resp) == list:  # если передается список - запрос успешен
                return resp
        else:
            raise Exception("shit")


async def fetch_all(tokens):
    """Добавляет в список задач запросы. На входе нужен список из токенов.
       По каждому токену будет запрошен актуальный список сотрудников
       (subscriberID).
       По каждому ID из БД будет запрошена последняя дата запроса.
       Если даты нет -
       местоположения будут собраны за последний месяц.
       Если последний запрос был в течение получаса - ID объединяются по 30 шт.
       В один запрос.
       запрос списка ID - subsGather.get_subs_by_token
       запрос даты - databaseProceed.getSubscriberLastLocationDate
       запрос списка дат - get_dates_list"""
    # словарь вида ID: datetime по всем ID из БД:
    last_locs_dict = subscribers_last_location()
    # чтобы было меньше уникальных дат, нужно убрать секунды. я решил так:
    # округлить время до минут (убрать секунды)
    last_locs_dict = {
        k: dt.datetime.fromisoformat(v.isoformat(timespec='minutes'))
        for k, v in last_locs_dict.items()
    }

    for token in tokens:
        subscribers = get_subs_by_token(token)
        header = {'Authorization': token}
        # для отбора недавно полученных локаций нужен timestamp-30 мин и обычн:
        timestamp = dt.datetime.now()
        last30minutes = timestamp-dt.timedelta(minutes=30)

        async with aiohttp.ClientSession(headers=header) as session:
            tasks = []
            # здесь я пошёл на уловку, чтобы отправлять меньше запросов.
            # я создаю словарь, где ключ - это объект datetime
            # (точность до минуты). значение - список с ID.
            # все ID с последним запросом в одну и ту же минуту
            # попадают в один список.
            # чтобы проконтролировать, что ключ с датой уже создан, я создал
            # seenDatesList. и каждую дату проверяю на налич. в этом списке.

            # словарь, где дата - ключ, а список с ID - знач:
            dates_ids_dict = defaultdict(list)
            for id in subscribers:
                last_loc_date = last_locs_dict.get(
                    id, dt.datetime.today()-dt.timedelta(days=31)
                )
                if last_loc_date >= last30minutes:
                    dates_ids_dict[last_loc_date].append(id)

                else:
                    dates = get_dates_list(last_loc_date)
                    for date in dates:
                        params = [("dateFrom", date[0]),
                                  ("dateTo", date[1]),
                                  ("subscriberIDs", id),
                                  ("count", 1000)]
                        tasks.append(fetch(session,
                                           apiHttp+apiGetLocs,
                                           params))

            for uniqueDate in dates_ids_dict.keys():
                startDate = uniqueDate+dt.timedelta(minutes=1)
                startDate = startDate.isoformat(timespec='minutes')
                lastDate = timestamp.isoformat(timespec='minutes')
                # по 30 ID в запрос, если недавно было обновление
                while dates_ids_dict[uniqueDate]:
                    params = [("dateFrom", startDate),
                              ("dateTo", lastDate),
                              ("count", 1000)]
                    # aiohttp позволяет передавать один и тот же параметр
                    # с разными значениями, только если они
                    # в списке с кортежами.
                    # для этого я создаю список с основными параметрами,
                    # а затем добавляю туда кортежи по каждому ID
                    # (параметр subscriberIDs):
                    params.extend([('subscriberIDs', id)
                                   for id in dates_ids_dict[uniqueDate][:30]])
                    tasks.append(fetch(session,
                                       apiHttp+apiGetLocs,
                                       params))
                    # сформировал запрос из 30 ID, отбросил их
                    del dates_ids_dict[uniqueDate][:30]

            # ждём ответы по всем запросам:
            responses = await asyncio.gather(*tasks, return_exceptions=True)
            # отбираем запросы без ошибок (нет локаций/ошибка сервера и т.п.)
            resp_no_exceptions = [o for o in responses if type(o) != Exception]
            # чтобы не записывать ложные локации, когда есть только последнее
            # известн. местопол., я удаляю координаты из локаций
            # с кодом 4 (последнее известное)
            for locs in resp_no_exceptions:
                for loc in locs:
                    if loc['state'] == 4:
                        del loc['longitude']
                        del loc['latitude']
                        del loc['locationDate']
            append_coordinates_directly(resp_no_exceptions)


def fetch_coordinates():
    asyncio.run(fetch_all(TOKENS_MTS.values()))
    print('coordinates fetched')


if __name__ == "__main__":
    fetch_coordinates()
