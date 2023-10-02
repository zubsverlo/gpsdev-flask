# (для формирования кластеров)
import pandas as pd
from skmob import TrajDataFrame
from skmob.preprocessing import detection, clustering
from trajectory_report.config import STAY_LOCATIONS_CONFIG, CLUSTERS_CONFIG


def prepare_clusters(coordinates: pd.DataFrame) -> pd.DataFrame:
    """
    Формирование остановок из DataFrame с координатами.
    """

    tdf = TrajDataFrame(coordinates,
                        latitude='latitude',
                        longitude='longitude',
                        user_id='subscriberID',
                        datetime='locationDate')

    # Формирование остановок. Самый важный этап, настройки влияют
    # на итоговый отчет. Уменьшение spatial_radius с 0.8 до 0.3 показало
    # большую точность, в связке с уменьшением радиуса ПСУ до 650 метров
    tdf = detection.stay_locations(tdf, **STAY_LOCATIONS_CONFIG)
    # добавляет колонку с номерами кластеров, не влияет на кол-во остановок
    if not len(tdf):
        return TrajDataFrame(
            pd.DataFrame(
                columns=['subscriberID', 'date', 'datetime', 'longitude',
                         'latitude', 'leaving_datetime', 'cluster']))
    tdf = clustering.cluster(tdf, **CLUSTERS_CONFIG)
    if len(tdf) < 2:
        tdf = tdf.rename(columns={
            'uid': 'subscriberID',
            'lng': 'longitude',
            'lat': 'latitude'
        })
        tdf['date'] = tdf['datetime'].apply(lambda x: x.date())
        return tdf

    tdf = tdf.rename(columns={
        'uid': 'subscriberID',
        'lng': 'longitude',
        'lat': 'latitude'
    })
    tdf['date'] = tdf['datetime'].apply(lambda x: x.date())
    tdf = tdf[['subscriberID', 'date', 'datetime', 'longitude',
               'latitude', 'leaving_datetime', 'cluster']]
    return pd.DataFrame(tdf)
