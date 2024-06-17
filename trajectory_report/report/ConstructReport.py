# (основной запрос отчетов)
import datetime as dt
from dataclasses import dataclass

import pandas as pd
from numpy import datetime64

from gpsdev_flask import main_logger
from trajectory_report.config import CLUSTERS_MTS, CLUSTERS_OWNTRACKS
from trajectory_report.database import DB_ENGINE
from trajectory_report.exceptions import ReportException
from trajectory_report.report import construct_select as cs
from trajectory_report.report.ClusterGenerator import prepare_clusters
from trajectory_report.report.coords_clusters_getter import (
    get_clusters,
    get_concatinated_coordinates,
    get_journal,
)


class OneEmployeeReportDataGetter:
    def __init__(
        self,
        name_id: int,
        date: dt.date | str,
        division: int | str,
    ) -> None:
        date = dt.date.fromisoformat(str(date))
        self.name_id = name_id
        self.division = division
        self.date = date

    def get_data(self):
        """
        if locations.empty:
            raise ReportException(
                f"За {self.date} нет локаций. Устройство отключено!"
            )

        """
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(
                cs.statements_one_emp(self.date, self.name_id, self.division),
                conn,
            )
            journal = pd.read_sql(cs.journal_one_emp(self.name_id), conn)
            journal["period_end"] = journal["period_end"].fillna(dt.date.today())
            journal = journal.loc[
                (journal["period_init"] <= self.date)
                & (self.date <= journal["period_end"])
            ]
            if journal.empty:
                raise ReportException(
                    f"Не подключен к отслеживанию в этот день ({self.date})"
                )
            # clusters and locations start
            locations = get_concatinated_coordinates(
                name_ids=[self.name_id],
                date=self.date,
                conn=conn,
                journal=journal,
            )
            if locations.empty:
                raise ReportException(
                    f"За {self.date} нет локаций. Устройство отключено!"
                )
            clusters = get_clusters(
                name_ids=[self.name_id],
                date_from=self.date,
                conn=conn,
                coords=locations,
                journal=journal,
            )
            owntracks = locations.owntracks.any()
            data = {
                "_stmts": stmts,
                "clusters": clusters,
                "_locations": locations,
                "owntracks": owntracks,
            }
            return data


@dataclass
class OwntracksMtsReportDataGetter:
    date_from: dt.date | str = dt.date.today()
    date_to: dt.date | str | None = None
    division: int | str | None = None
    name_ids: list[int] | None = None
    object_ids: list[int] | None = None

    def __post_init__(self):
        self.date_from = dt.date.fromisoformat(str(self.date_from))
        if self.date_to:
            self.date_to = dt.date.fromisoformat(str(self.date_to))
        else:
            self.date_to = self.date_from
        if self.date_from == self.date_to:
            self.coords_date = self.date_to
        elif dt.date.today() <= self.date_to:
            self.coords_date = dt.date.today()
        else:
            self.coords_date = None
        self.conn = DB_ENGINE.connect()

    def get_data(self) -> dict:
        """Запрашивает данные для формирования отчета из БД.

        objects_with_address - дополнительно запросить адреса ПСУ для
        отображения на карте

        check_for_empty_locations - дополнительно проверить, есть ли сотрудники
        без локаций за последнее время, о которых нужно уведомить
        """

        stmts = pd.read_sql(
            cs.statements_extended(
                date_from=self.date_from,
                date_to=self.date_to,
                division=self.division,
                name_ids=self.name_ids,
                object_ids=self.object_ids,
            ),
            self.conn,
        )
        if stmts.empty:
            raise ReportException(
                f"Не заполнена таблица выходов в период "
                f"с {self.date_from} до {self.date_to}"
            )

        self.name_ids = stmts.uid.unique().tolist()
        self.object_ids = stmts.object_id.unique().tolist()

        self.employees = pd.read_sql(cs.employees(self.name_ids), self.conn)

        serves = pd.read_sql(
            cs.serves(self.date_from, self.date_to, self.name_ids), self.conn
        )

        # Комментарии в таблице
        comment = pd.read_sql(cs.comment(self.division, self.name_ids), self.conn)
        # Частота посещений псу в таблице
        frequency = pd.read_sql(cs.frequency(self.division, self.name_ids), self.conn)

        self.objects = pd.read_sql(cs.objects(self.object_ids), self.conn)

        # Подопечные, которых нужно посещать по выходным
        holiday_attend_needed = [
            i
            for i in self.conn.execute(
                cs.holiday_attend_needed(self.object_ids)
            ).scalars()
        ]

        # Журнал определяет иточник локаций и кластеров
        # сотрудника в определенный период
        self.journal = get_journal(self.name_ids, self.conn)
        # Локации и кластеры
        coords = None
        if self.coords_date:
            coords = get_concatinated_coordinates(
                self.name_ids,
                self.coords_date,
                self.conn,
                self.journal,
            )
        clusters = get_clusters(
            name_ids=self.name_ids,
            date_from=self.date_from,
            date_to=self.date_to,
            conn=self.conn,
            coords=coords,
            journal=self.journal,
        )

        staffers = (
            self.employees.loc[self.employees["staffer"] == True].uid.unique().tolist()
        )

        self.conn.close()

        data = {}
        data["_stmts"] = stmts
        data["_serves"] = serves
        data["_clusters"] = clusters
        data["_employees"] = self.employees
        data["_objects"] = self.objects
        data["_comment"] = comment
        data["_frequency"] = frequency
        data["_staffers"] = staffers
        data["_holiday_attend_needed"] = holiday_attend_needed
        data["_coordinates"] = coords
        return data

    def mts_empty_locations(self) -> list[int] | list:
        """Чтобы собрать информацию о сотрудниках, у которых отключен телефон,
        нужно извлечь информацию из coordinates, затем, при помощи journal,
        определить принадлежность subscriberID к конкретному сотруднику.

        Returns:
            list[int]: Список name_id, у которых на момент запроса выключен
            телефон в течение определенного кол-ва минут
        """
        if not self.includes_current_date:
            return []
        empty_locations = list(self.conn.execute(cs.empty_locations()).scalars())
        today = dt.date.today()
        mask = (
            (today >= self.journal["period_init"])
            & (today <= self.journal["period_end"])
            & (self.journal["subscriberID"].isin(empty_locations))
        )
        return list(self.journal[mask].name_id.unique())

    def owntracks_empty_locations(self) -> list[int] | list:
        """
        Чтобы получить список сотрудников с owntracks без локаций за
        последний час, нужно получить список всех активных сотрудников и
        убрать их из всех остальных сотрудников с owntracks, кто отслеживается
        за текущий день.
        """
        if not self.includes_current_date:
            return []
        empty_locations = set(
            self.conn.execute(cs.empty_locations_owntracks()).scalars()
        )
        today = dt.date.today()
        mask = (
            (today >= self.journal["period_init"])
            & (today <= self.journal["period_end"])
            & (self.journal["owntracks"] == True)
        )
        empty_locations = set(self.journal[mask].name_id.unique()) - empty_locations
        return list(empty_locations)

    def mts_clusters(self) -> pd.DataFrame:
        subs_ids = self.journal.subscriberID.dropna().unique().tolist()
        # here, if no subs_ids, just return an empty df with columns
        if not subs_ids:
            return pd.DataFrame(
                columns=[
                    "uid",
                    "date",
                    "datetime",
                    "leaving_datetime",
                    "lng",
                    "lat",
                    "cluster",
                ]
            )
        journal = self.journal.copy()
        journal = journal[journal["owntracks"] == False]

        clusters = pd.read_sql(
            cs.clusters(self.date_from, self.date_to, subs_ids), self.conn
        )
        if self.includes_current_date:
            current_locations = pd.read_sql(
                cs.current_locations_mts(subs_ids), self.conn
            )
            try:
                locs_clusters = prepare_clusters(
                    current_locations,
                    **CLUSTERS_MTS,
                    **CLUSTERS_MTS,
                )
                dates = locs_clusters["datetime"].apply(lambda x: x.date())
                locs_clusters["date"] = dates
                clusters = pd.concat([clusters, locs_clusters])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        clusters = pd.merge(
            clusters, journal, how="left", right_on="subscriberID", left_on="uid"
        )

        clusters["j_exist"] = (clusters["date"] >= clusters["period_init"]) & (
            clusters["date"] <= clusters["period_end"]
        )
        clusters = clusters[clusters["j_exist"]]
        clusters["uid"] = clusters["name_id"]
        return clusters[
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

    def owntracks_clusters(self) -> pd.DataFrame:
        clusters = pd.read_sql(
            cs.clusters_owntracks(
                self.date_from, self.date_to, employee_ids=self.name_ids
            ),
            self.conn,
        )
        if self.includes_current_date:
            curr_owntracks = pd.read_sql(
                cs.current_locations_owntracks(employee_ids=self.name_ids),
                self.conn,
            )
            tst = curr_owntracks.rename(columns={"tst": "datetime"}).drop_duplicates(
                ["uid", "datetime"], keep="last"
            )
            created_at = curr_owntracks.rename(
                columns={"created_at": "datetime"}
            ).drop_duplicates(["uid", "datetime"], keep="last")
            curr_owntracks = (
                pd.concat([tst, created_at])
                .drop_duplicates(["uid", "datetime"])
                .sort_values(["uid", "datetime"])
                .loc[:, ["uid", "datetime", "lng", "lat"]]
            )

            curr_owntracks = curr_owntracks[
                curr_owntracks["datetime"] > datetime64(dt.date.today())
            ]
            try:
                locs_clusters = prepare_clusters(
                    curr_owntracks, **CLUSTERS_OWNTRACKS, **CLUSTERS_OWNTRACKS
                )
                dates = locs_clusters["datetime"].apply(lambda x: x.date())
                locs_clusters["date"] = dates

                clusters = pd.concat([clusters, locs_clusters])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )

        clusters = pd.merge(
            clusters, self.journal, how="left", left_on="uid", right_on="name_id"
        )
        clusters["j_exist"] = (
            (clusters["date"] >= clusters["period_init"])
            & (clusters["date"] <= clusters["period_end"])
            & (clusters["owntracks"] == True)
        )
        clusters = clusters[clusters["j_exist"]]
        return clusters[
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


def report_data_factory(*args, **kwargs) -> dict:
    data = OwntracksMtsReportDataGetter(*args, **kwargs).get_data()
    return data


def one_employee_report_data_factory(*args, **kwargs) -> dict:
    data = OneEmployeeReportDataGetter(*args, **kwargs).get_data()
    return data


if __name__ == "__main__":
    a = OwntracksMtsReportDataGetter("2024-05-01", "2024-05-31", "ПВТ1").get_data()
    # e = OneEmployeeReportDataGetter(1293, "2024-04-26", 2).get_data()
    # e = OneEmployeeReportDataGetter(898, "2024-02-02", 3).get_data()
    # print(a)
    pass
