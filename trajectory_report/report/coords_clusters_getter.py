import datetime as dt
from dataclasses import dataclass

import pandas as pd
from numpy import datetime64
from sqlalchemy import Connection, Select, select

from gpsdev_flask import main_logger
from trajectory_report.config import CLUSTERS_MTS, CLUSTERS_OWNTRACKS
from trajectory_report.database import DB_ENGINE
from trajectory_report.exceptions import ReportException
from trajectory_report.models import (
    Clusters,
    Coordinates,
    Journal,
    OwnTracksCluster,
    OwnTracksLocation,
    Statements,
)
from trajectory_report.report.ClusterGenerator import prepare_clusters

# Вместе с кластерами и локациями всегда должен запрашиваться журнал,
# так как он определяет, к чему был подключен сотрудник и какой у него
# subscriberID. В связи с этим любые процедуры с journal можно перенести
# в этот модуль, который отвечает за запрос локаций. Так как локации могут
# запрашиваться одновременно с кластерами, логично разделить один журнал.
# Поэтому journal будет запрашиваться опционально, если не был предоставлен.


def get_journal(name_ids: list[int] | int, conn: Connection) -> pd.DataFrame:
    """
    Получить journal по name_ids или одному name_id
    Столбцы: name_id, subscriberID, period_init, period_end, owntracks
    """
    sel: Select = select(
        Journal.name_id.label("uid"),
        Journal.subscriberID,
        Journal.period_init,
        Journal.period_end,
        Journal.owntracks,
    )
    if isinstance(name_ids, int):
        sel = sel.where(Journal.name_id == name_ids)
    else:
        sel = sel.where(Journal.name_id.in_(name_ids))

    journal = pd.read_sql(sel, conn)
    journal["period_end"] = journal["period_end"].fillna(dt.date.today())
    return journal


def coordinates_mts(
    date: dt.date,
    conn: Connection,
    journal: pd.DataFrame,
) -> pd.DataFrame:
    """
    Столбцы на выходе: uid, datetime, lat, lng, owntracks(false)
    """
    subscriber_ids = journal[pd.notna(journal["subscriberID"])].subscriberID
    subscriber_ids = subscriber_ids.unique().tolist()
    sel: Select = (
        select(
            Coordinates.subscriberID,
            Coordinates.locationDate.label("datetime"),
            Coordinates.longitude.label("lng"),
            Coordinates.latitude.label("lat"),
        )
        .where(Coordinates.requestDate > date)
        .where(Coordinates.requestDate < date + dt.timedelta(days=1))
        .where(Coordinates.locationDate != None)
        .where(Coordinates.subscriberID.in_(subscriber_ids))
    )
    coordinates = pd.read_sql(sel, conn)
    coordinates = pd.merge(coordinates, journal, how="left", on="subscriberID")
    if coordinates.empty:
        return pd.DataFrame(
            columns=["uid", "datetime", "lat", "lng", "owntracks"],
        )
    return coordinates[["uid", "datetime", "lat", "lng", "owntracks"]]


def coordinates_owntracks(
    date: dt.date,
    conn: Connection,
    journal: pd.DataFrame,
) -> pd.DataFrame:
    """
    Столбцы на выходе: uid, datetime, lat, lng, owntracks(true)
    """
    employee_ids = journal[journal["owntracks"] == True].uid.unique().tolist()
    sel: Select = (
        select(
            OwnTracksLocation.employee_id.label("uid"),
            OwnTracksLocation.created_at,
            OwnTracksLocation.tst,
            OwnTracksLocation.lon.label("lng"),
            OwnTracksLocation.lat,
        )
        .where(OwnTracksLocation.created_at > date)
        .where(OwnTracksLocation.created_at < date + dt.timedelta(days=1))
        .where(OwnTracksLocation.employee_id.in_(employee_ids))
    )
    coords = pd.read_sql(sel, conn)
    coords["owntracks"] = True
    tst = coords.rename(
        columns={"tst": "datetime"},
    ).drop_duplicates(
        ["uid", "datetime"],
        keep="last",
    )
    created_at = coords.rename(
        columns={"created_at": "datetime"},
    ).drop_duplicates(
        ["uid", "datetime"],
        keep="last",
    )
    coords = (
        pd.concat([tst, created_at])
        .drop_duplicates(["uid", "datetime"])
        .sort_values(["uid", "datetime"])
        .loc[:, ["uid", "datetime", "lng", "lat"]]
    )

    coords = coords[coords["datetime"] > datetime64(date)]
    coords["owntracks"] = True
    return coords


def get_concatinated_coordinates(
    name_ids: list[int],
    date: dt.date | None = dt.date.today(),
    conn: Connection | None = None,
    journal: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Получение координат за определенную дату (по умолчанию текущий день)
    Столбцы на выходе: uid, datetime, lat, lng, owntracks
    """
    if not conn:
        conn = DB_ENGINE.connect()
    if not isinstance(journal, pd.DataFrame):
        journal = get_journal(name_ids, conn, date)
    # filter entries by the date
    journal_mask = (date >= journal["period_init"]) & (date <= journal["period_end"])
    journal = journal[journal_mask]

    coords_mts = coordinates_mts(date, conn, journal)
    coords_owntracks = coordinates_owntracks(date, conn, journal)
    coords = pd.concat([coords_mts, coords_owntracks])
    return coords


def get_clusters_mts(
    name_ids: list[int],
    date_from: dt.date,
    date_to: dt.date,
    journal: pd.DataFrame,
    conn: Connection,
) -> pd.DataFrame:
    """
    Fetch from db
    Столбцы на выходе:
    uid, date, datetime, leaving_datetime, lng, lat, cluster, owntracks
    """
    subscriber_ids = journal[pd.notna(journal["subscriberID"])].subscriberID
    subscriber_ids = subscriber_ids.unique().tolist()
    sel: Select = (
        select(
            Clusters.subscriberID,
            Clusters.date,
            Clusters.datetime,
            Clusters.longitude.label("lng"),
            Clusters.latitude.label("lat"),
            Clusters.leaving_datetime,
            Clusters.cluster,
        )
        .where(Clusters.date >= date_from)
        .where(Clusters.date < date_to + dt.timedelta(days=1))
        .where(Clusters.subscriberID.in_(subscriber_ids))
    )
    clusters = pd.read_sql(sel, conn)
    clusters = pd.merge(
        clusters,
        journal,
        how="left",
        on="subscriberID",
    )

    clusters["j_exist"] = (clusters["date"] >= clusters["period_init"]) & (
        clusters["date"] <= clusters["period_end"]
    )
    clusters = clusters[clusters["j_exist"]]
    clusters = clusters[
        [
            "uid",
            "date",
            "datetime",
            "leaving_datetime",
            "lng",
            "lat",
            "cluster",
        ]
    ]

    clusters["owntracks"] = False
    return clusters


def get_clusters_owntracks(
    name_ids: list[int],
    date_from: dt.date,
    date_to: dt.date,
    journal: pd.DataFrame,
    conn: Connection,
) -> pd.DataFrame:
    sel: Select = (
        select(
            OwnTracksCluster.employee_id.label("uid"),
            OwnTracksCluster.date,
            OwnTracksCluster.datetime,
            OwnTracksCluster.longitude.label("lng"),
            OwnTracksCluster.latitude.label("lat"),
            OwnTracksCluster.leaving_datetime,
            OwnTracksCluster.cluster,
        )
        .where(OwnTracksCluster.date >= date_from)
        .where(OwnTracksCluster.date < date_to + dt.timedelta(days=1))
        .where(OwnTracksCluster.employee_id.in_(name_ids))
    )
    clusters = pd.read_sql(sel, conn)
    clusters = pd.merge(clusters, journal, how="left", on="uid")
    clusters["j_exist"] = (
        (clusters["date"] >= clusters["period_init"])
        & (clusters["date"] <= clusters["period_end"])
        & (clusters["owntracks"] == True)
    )
    clusters = clusters[clusters["j_exist"]]
    clusters = clusters[
        [
            "uid",
            "date",
            "datetime",
            "leaving_datetime",
            "lng",
            "lat",
            "cluster",
        ]
    ]
    clusters["owntracks"] = True
    return clusters


def get_clusters(
    name_ids: list[int],
    date_from: dt.date | None = dt.date.today(),
    date_to: dt.date | None = None,
    conn: Connection | None = None,
    coords: pd.DataFrame | None = None,
    journal: pd.DataFrame | None = None,
) -> pd.DataFrame:
    """
    Запрос кластеров по списку из name_ids.
    Если не передать дату, запрос за текущий день.

    """
    if not date_to:
        date_to = date_from
    if not conn:
        conn = DB_ENGINE.connect()
    if not isinstance(journal, pd.DataFrame):
        journal = get_journal(name_ids, conn)

    # current_clusters here if date allows
    current_clusters = None
    date = None
    if date_from == date_to:
        date = date_to
    elif date_to >= dt.date.today():
        date = dt.date.today()

    if date:
        if not isinstance(coords, pd.DataFrame):
            coords = get_concatinated_coordinates(
                name_ids,
                date,
                conn,
                journal,
            )
        # get coords, split into two types, make and concat them
        clusters_mts = prepare_clusters(
            coords[coords["owntracks"] == False],
            minutes_for_a_stop=CLUSTERS_MTS["minutes_for_a_stop"],
            no_data_for_minutes=CLUSTERS_MTS["no_data_for_minutes"],
            spatial_radius_km=CLUSTERS_MTS["spatial_radius_km"],
            cluster_radius_km=CLUSTERS_MTS["cluster_radius_km"],
        )
        clusters_mts["owntracks"] = False

        clusters_owntracks = prepare_clusters(
            coords[coords["owntracks"] == True],
            minutes_for_a_stop=CLUSTERS_OWNTRACKS["minutes_for_a_stop"],
            no_data_for_minutes=CLUSTERS_OWNTRACKS["no_data_for_minutes"],
            spatial_radius_km=CLUSTERS_OWNTRACKS["spatial_radius_km"],
            cluster_radius_km=CLUSTERS_OWNTRACKS["cluster_radius_km"],
        )
        clusters_owntracks["owntracks"] = True
        current_clusters = pd.concat([clusters_mts, clusters_owntracks])
        current_clusters["date"] = date
        # В случае, если это отчет по одному сотруднику, возможно дублирование.
        # Чтобы его избежать, остановимся только на сформированных
        # вручную кластерах.
        if date_from == date_to:
            return current_clusters

    # fetch other clusters
    clusters_mts = get_clusters_mts(
        name_ids,
        date_from,
        date_to,
        journal,
        conn,
    )
    clusters_owntracks = get_clusters_owntracks(
        name_ids,
        date_from,
        date_to,
        journal,
        conn,
    )
    clusters = pd.concat([clusters_mts, clusters_owntracks])
    # concat current and fetched clusters
    if date:
        clusters = pd.concat([clusters, current_clusters])
    return clusters


if __name__ == "__main__":
    date = dt.date(2024, 3, 1)
    date = dt.date.today()
    sel = (
        select(Statements.name_id)
        .where(Statements.division == 6)
        .where(Statements.date == date)
    )
    date_from = dt.date(2024, 5, 1)
    date_to = dt.date(2024, 6, 30)

    stmts = pd.read_sql(sel, DB_ENGINE.connect())
    name_ids = stmts.name_id.unique().tolist()
    coords = get_concatinated_coordinates(name_ids)
    clusters = get_clusters(name_ids, coords=coords)
    pass
