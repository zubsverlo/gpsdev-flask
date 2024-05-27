# (для формирования кластеров)
import pandas as pd
from skmob import TrajDataFrame
from skmob.preprocessing import detection, clustering


def prepare_clusters(
    coordinates: pd.DataFrame,
    minutes_for_a_stop,
    no_data_for_minutes,
    spatial_radius_km,
    cluster_radius_km,
    **kwargs
) -> pd.DataFrame:
    """
    Формирование остановок из DataFrame с координатами.
    DF, вне зависимости от происхождения локаций, должен быть со столбцами:
    uid, lng, lat, datetime
    Столбцы на выходе:
    uid, lng, lat, datetime, leaving_datetime, cluster
    Единственная разница, имеющая значение, это конфиг для формирования
    кластеров и остановок. Его тоже нужно распаковать в эту функцию, чтобы
    для самой функции не было никакой разницы, какие кластеры здесь
    обрабатываются.
    """

    tdf = TrajDataFrame(
        coordinates,
        latitude="lat",
        longitude="lng",
        user_id="uid",
        datetime="datetime",
    )

    if tdf.empty:
        return TrajDataFrame(
            pd.DataFrame(
                columns=[
                    "uid",
                    "datetime",
                    "lng",
                    "lat",
                    "leaving_datetime",
                    "cluster",
                ]
            )
        )

    # Формирование остановок. Самый важный этап, настройки влияют
    # на итоговый отчет. Уменьшение spatial_radius с 0.8 до 0.3 показало
    # большую точность, в связке с уменьшением радиуса ПСУ до 650 метров
    tdf = detection.stay_locations(
        tdf,
        minutes_for_a_stop=minutes_for_a_stop,
        no_data_for_minutes=no_data_for_minutes,
        spatial_radius_km=spatial_radius_km,
    )
    # добавляет колонку с номерами кластеров, не влияет на кол-во остановок
    if tdf.empty:
        return TrajDataFrame(
            pd.DataFrame(
                columns=[
                    "uid",
                    "datetime",
                    "lng",
                    "lat",
                    "leaving_datetime",
                    "cluster",
                ]
            )
        )
    tdf = clustering.cluster(tdf, cluster_radius_km=cluster_radius_km)
    return pd.DataFrame(tdf)
