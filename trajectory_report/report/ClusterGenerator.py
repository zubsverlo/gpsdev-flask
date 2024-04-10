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
    stay_locations_config = (
        STAY_LOCATIONS_CONFIG_MTS
        if not owntracks
        else STAY_LOCATIONS_CONFIG_OWNTRACKS
    )
    clusters_confing = (
        CLUSTERS_CONFIG_MTS if not owntracks else CLUSTERS_CONFIG_OWNTRACKS
    )
    extension_dict = {
        "user_id": "subscriberID" if not owntracks else "employee_id",
        "datetime": "locationDate" if not owntracks else "created_at",
        "latitude": "latitude" if not owntracks else "lat",
        "longitude": "longitude" if not owntracks else "lon",
    }

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
