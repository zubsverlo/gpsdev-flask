from trajectory_report.models import Clusters, Coordinates
from sqlalchemy import select, func
from trajectory_report.database import DB_ENGINE
import datetime as dt
from typing import List
import pandas as pd
from trajectory_report.report.ClusterGenerator import prepare_clusters
from trajectory_report.config import (
        CLUSTERS_CONFIG_MTS, STAY_LOCATIONS_CONFIG_MTS
)

def get_dates_range() -> List[dt.date]:
    """Получить список дат, по которым нужно произвести кластеры.
    Если кластеров нет вообще - выдаст список из дат за последние 2 месяца."""
    with DB_ENGINE.connect() as conn:
        # Дата последних произведенных кластеров
        date = conn.execute(func.max(Clusters.date)).scalar()
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
            Coordinates.subscriberID.label("uid"),
            Coordinates.locationDate.label("datetime"),
            Coordinates.longitude.label("lng"),
            Coordinates.latitude.label("lat"),
        )
        .where(Coordinates.requestDate > date)
        .where(Coordinates.requestDate < date + dt.timedelta(days=1))
        .where(Coordinates.locationDate != None)
    )
    return pd.read_sql(sel, DB_ENGINE.connect())


def make_clusters_mts():
    # Получить список дат для формирования кластеров
    dates = get_dates_range()
    print(dates)
    for date in dates:
        # Получить координаты
        coords = get_coordinates(date)
        # Сформировать кластеры
        clusters = prepare_clusters(
            coords,
            **CLUSTERS_CONFIG_MTS,
            **STAY_LOCATIONS_CONFIG_MTS
        )
        # Сохранить кластеры в БД
        clusters = clusters.rename(
            columns={
                "uid": "subscriberID",
                "lng": "longitude",
                "lat": "latitude",
            }
        )
        clusters['date'] = clusters['datetime'].apply(lambda x: x.date())
        clusters.to_sql(
            Clusters.__tablename__, DB_ENGINE, if_exists="append", index=False
        )
        print(f"Clusters for {date} have been uploaded.")


if __name__ == "__main__":
    make_clusters_mts()
