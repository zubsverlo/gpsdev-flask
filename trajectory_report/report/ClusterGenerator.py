# (для формирования кластеров)
import pandas as pd
from skmob import TrajDataFrame
from skmob.preprocessing import detection, clustering
from trajectory_report.config import (
    STAY_LOCATIONS_CONFIG_MTS,
    STAY_LOCATIONS_CONFIG_OWNTRACKS,
    CLUSTERS_CONFIG_MTS,
    CLUSTERS_CONFIG_OWNTRACKS,
)


def prepare_clusters(
    coordinates: pd.DataFrame, owntracks: bool = False
) -> pd.DataFrame:
    """
    Формирование остановок из DataFrame с координатами.
    """

    # Чтобы указать правильные столбцы для формирования tdf, в зависимости от
    # источника локаций, используется dict
    # По умолчанию это МТС
    extension_dict = {
        "user_id": "subscriberID",
        "datetime": "locationDate",
        "latitude": "latitude",
        "longitude": "longitude",
    }
    stay_locations_config = STAY_LOCATIONS_CONFIG_MTS
    clusters_confing = CLUSTERS_CONFIG_MTS

    if owntracks:
        extension_dict = {
            "user_id": "employee_id",
            "datetime": "created_at",
            "latitude": "lat",
            "longitude": "lon",
        }
        stay_locations_config = STAY_LOCATIONS_CONFIG_OWNTRACKS
        clusters_confing = CLUSTERS_CONFIG_OWNTRACKS

    tdf = TrajDataFrame(
        coordinates,
        latitude=extension_dict["latitude"],
        longitude=extension_dict["longitude"],
        user_id=extension_dict["user_id"],
        datetime=extension_dict["datetime"],
    )

    if tdf.empty:
        return TrajDataFrame(
            pd.DataFrame(
                columns=[
                    extension_dict["user_id"],
                    "date",
                    "datetime",
                    "longitude",
                    "latitude",
                    "leaving_datetime",
                    "cluster",
                ]
            )
        )

    # Формирование остановок. Самый важный этап, настройки влияют
    # на итоговый отчет. Уменьшение spatial_radius с 0.8 до 0.3 показало
    # большую точность, в связке с уменьшением радиуса ПСУ до 650 метров
    tdf = detection.stay_locations(tdf, **stay_locations_config)
    # добавляет колонку с номерами кластеров, не влияет на кол-во остановок
    if not len(tdf):
        return TrajDataFrame(
            pd.DataFrame(
                columns=[
                    extension_dict["user_id"],
                    "date",
                    "datetime",
                    "longitude",
                    "latitude",
                    "leaving_datetime",
                    "cluster",
                ]
            )
        )
    tdf = clustering.cluster(tdf, **clusters_confing)
    if len(tdf) < 2:
        tdf = tdf.rename(
            columns={
                "uid": extension_dict["user_id"],
                "lng": "longitude",
                "lat": "latitude",
            }
        )
        tdf["date"] = tdf["datetime"].apply(lambda x: x.date())
        return tdf

    tdf = tdf.rename(
        columns={
            "uid": extension_dict["user_id"],
            "lng": "longitude",
            "lat": "latitude",
        }
    )
    tdf["date"] = tdf["datetime"].apply(lambda x: x.date())
    tdf = tdf[
        [
            extension_dict["user_id"],
            "date",
            "datetime",
            "longitude",
            "latitude",
            "leaving_datetime",
            "cluster",
        ]
    ]
    return pd.DataFrame(tdf)
