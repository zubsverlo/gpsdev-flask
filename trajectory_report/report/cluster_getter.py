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


class ClusterGetter:
    def __init__(
        self,
        name_ids: list[int],
        date_from: dt.date | None = dt.date.today(),
        date_to: dt.date | None = None,
        conn: Connection | None = None,
    ):
        if not date_to:
            date_to = date_from
        if not conn:
            self.conn = DB_ENGINE.connect()
        self.journal = get_journal(name_ids, self.conn)

        current_clusters = None
        date = None
        if date_from == date_to:
            date = date_to
        elif date_to >= dt.date.today():
            date = dt.date.today()
