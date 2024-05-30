from trajectory_report.models import OwnTracksCluster, OwnTracksLocation
from sqlalchemy import select, func, delete
from sqlalchemy.exc import OperationalError
from trajectory_report.database import DB_ENGINE, REDIS_CONN
import datetime as dt
from typing import List
import pandas as pd
from trajectory_report.report.ClusterGenerator import prepare_clusters
from trajectory_report.config import (STAY_LOCATIONS_CONFIG_OWNTRACKS,
                                      CLUSTERS_CONFIG_OWNTRACKS)
from numpy import datetime64


def get_dates_range() -> List[dt.date]:
    """Получить список дат, по которым нужно произвести кластеры.
    Если кластеров нет вообще - выдаст список из дат за последние 2 месяца."""
    with DB_ENGINE.connect() as conn:
        # Дата последних произведенных кластеров
        date = conn.execute(func.max(OwnTracksCluster.date)).scalar()
        if not date:
            # Если кластеры ещё не производились - задать день 2 месяца назад
            date = dt.date.today() - dt.timedelta(days=60)
        # Список дат, по которым нужно произвести кластеры координат.
        return [
            date + dt.timedelta(days=i)
            for i in range(1, (dt.date.today() - date).days)
        ]


def get_coordinates(date: dt.date) -> pd.DataFrame:
    """Собирает все координаты за указанный день"""
    sel = (
        select(
            OwnTracksLocation.employee_id.label('uid'),
            OwnTracksLocation.created_at,
            OwnTracksLocation.tst,
            OwnTracksLocation.lon.label('lng'),
            OwnTracksLocation.lat,
        )
        .where(OwnTracksLocation.created_at > date)
        .where(OwnTracksLocation.created_at < date + dt.timedelta(days=1))
    )
    with DB_ENGINE.connect() as conn:
        locations = pd.read_sql(sel, conn)
    
    tst = locations\
        .rename(columns={'tst': 'datetime'})\
        .drop_duplicates(['uid', 'datetime'], keep='last')
    created_at = locations\
        .rename(columns={'created_at': 'datetime'})\
        .drop_duplicates(['uid', 'datetime'], keep='last')
    locations = pd.concat([tst, created_at])\
        .drop_duplicates(['uid', 'datetime'])\
        .sort_values(['uid', 'datetime'])\
        .loc[:, ['uid', 'datetime', 'lng', 'lat']]
    locations = locations[locations['datetime'] > datetime64(date)]
    return locations


def remake_clusters():
    """Удаление кластеров за определенный день и формирование заново
    В случае, если локации по сотруднику пришли с запозданием, дата локации
    попадает в Redis для того, чтобы переформировать созданные кластеры.
    Фукнция удаляет кластеры по каждой из дат в этом списке и формирует заново
    """
    dates = []
    while True:
        date = REDIS_CONN.spop("owntracks_cluster_dates")
        print(date)
        if not date:
            break
        date = dt.date.fromisoformat(date.decode())
        stmt = delete(OwnTracksCluster).where(OwnTracksCluster.date == date)
        try:
            with DB_ENGINE.connect() as conn:
                conn.execute(stmt)
                conn.commit()
            dates.append(date)
        except OperationalError:
            REDIS_CONN.sadd("owntracks_cluster_dates", str(date))
    if dates:
        make_clusters_owntracks(dates)


def make_clusters_owntracks(dates: list[dt.date] | None = None):
    # Получить список дат для формирования кластеров
    if not dates:
        dates = get_dates_range()
    print(dates)
    for date in dates:
        # Получить координаты
        coords = get_coordinates(date)
        # Сформировать кластеры
        clusters = prepare_clusters(
            coords,
            **STAY_LOCATIONS_CONFIG_OWNTRACKS,
            **CLUSTERS_CONFIG_OWNTRACKS
        )
        clusters = clusters.rename(
            columns={
                "uid": "employee_id",
                "lng": "longitude",
                "lat": "latitude"
            }
        )
        clusters['date'] = clusters.datetime.apply(lambda x: x.date())
        # Сохранить кластеры в БД
        clusters.to_sql(
            OwnTracksCluster.__tablename__,
            DB_ENGINE,
            if_exists="append",
            index=False,
        )
        print(f"Clusters for {date} have been uploaded.")


if __name__ == "__main__":
    make_clusters_owntracks()
    remake_clusters()
