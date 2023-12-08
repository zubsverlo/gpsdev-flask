from trajectory_report.config import TOKENS_MTS
from trajectory_report.exceptions import MtsException
import requests


# Основной домен API
apiHttp = 'http://api.mpoisk.ru'
# Группы
apiSubscriberGroups = '/v6/api/subscriberManagement/subscriberGroups'
# Сотрудники
apiSubscribers = '/v6/api/subscriberManagement/subscribers'
# Запрос координат
apiGetLocs = '/v6/api/mobilePositioningManagement/locations'


def get_subscribers():
    """Возвращает список сотрудников.
       Получаем компанию, id сотрудника, id группы, имя сотрудника. Пример:
       [{'company': 'ГССП', 'subscriberID': 2490055,
         'subscriberGroupID': 208897, 'name': 'Пачулия Рита Нуревна'}, ...]"""
    subscribers = []  # все ответы списком

    for company, token in TOKENS_MTS.items():
        headers = {'Authorization': token}
        request = requests.get(apiHttp+apiSubscribers, headers=headers)

        dic = []  # в этом списке ответы по конкретной компании
        # Из всего json собираем только необходимые значения:
        for i in request.json():
            x = {'company': company,  # x - временный словарь
                 'subscriberID': i['subscriberID'],
                 'subscriberGroupID': i['subscriberGroupID'],
                 'name': i['name']}
            dic.append(x)
        subscribers.extend(dic)
    return subscribers


def get_subs_by_token(token):
    """Запрашивает список из subscriberID по токену. На входе токен (str),
       на выходе получаем список ID. """
    header = {'Authorization': token}
    # Запрос к Api
    request = requests.get(apiHttp+apiSubscribers, headers=header)
    # список ID сотрудников
    subscribers = [i['subscriberID'] for i in request.json()]
    return subscribers


def delete_by_subscriberID(subscriberID, token):
    """Удаляет покнкретного пользователя по конкретному токену"""
    header = {'Authorization': token}
    r = requests.delete(
        apiHttp +
        f"/v6/api/subscriberManagement/subscribers/{subscriberID}",
        headers=header)
    if r.status_code != 204:
        raise MtsException('Удалить сотрудника не получилось, попробуйте ещё.')


def delete_subs(subs_to_remove: list):
    """Удаляет абонентов из МТС по списку.
    На входе нужен список с subscriberID.
    По очереди запрашивает сотрудников по разным токенам,
    затем ищет среди этих сотрудников полученные subscriberID.
    Если находит - удаляет."""
    for token in TOKENS_MTS.values():
        subscribers = get_subs_by_token(token)
        for sub in subscribers:
            if sub in subs_to_remove:
                delete_by_subscriberID(sub, token)


def update_name(subscriberID: int, new_name):
    """Обновляет имя сотрудника по subscriberID.
    Нужно передать subscriberID и строку с новым имененем"""
    for token in TOKENS_MTS.values():
        subscribers = get_subs_by_token(token)
        for sub in subscribers:
            if subscriberID == sub:
                print('found')
                header = {'Authorization': token,
                          'Content-Type': 'application/json'}
                params = {'name': new_name}
                r = requests.patch(
                    apiHttp +
                    f"/v6/api/subscriberManagement/subscribers/{subscriberID}",
                    json=params,
                    headers=header,
                    )
                if r.status_code != 200:
                    raise MtsException(r.text)
                break
