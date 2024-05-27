# (основной запрос отчетов)
import pandas as pd
from trajectory_report.report import construct_select as cs
from trajectory_report.database import DB_ENGINE
import datetime as dt
from trajectory_report.report.ClusterGenerator import prepare_clusters
from trajectory_report.exceptions import ReportException
from dataclasses import dataclass
from gpsdev_flask import main_logger
from trajectory_report.config import (
    STAY_LOCATIONS_CONFIG_MTS,
    STAY_LOCATIONS_CONFIG_OWNTRACKS,
    CLUSTERS_CONFIG_MTS,
    CLUSTERS_CONFIG_OWNTRACKS,
)


class OneEmployeeReportDataGetter:
    def __init__(
        self,
        name_id: int,
        date: dt.date | str,
        division: int | str,
    ) -> None:
        date = dt.date.fromisoformat(str(date))
        self.owntracks = False
        self.name_id = name_id
        self.division = division
        self.date = date

    def get_data(self):
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(
                cs.statements_one_emp(self.date, self.name_id, self.division),
                conn
            )
            journal = pd.read_sql(cs.journal_one_emp(self.name_id), conn)
            journal["period_end"] = journal["period_end"].fillna(
                dt.date.today()
            )
            journal = journal.loc[
                (journal["period_init"] <= self.date)
                & (self.date <= journal["period_end"])
            ]
            if journal.empty:
                raise ReportException(
                    f"Не подключен к отслеживанию в этот день ({self.date})"
                )
            if journal.iloc[0].subscriberID:
                subs_id = int(journal.iloc[0].subscriberID)
                locations = pd.read_sql(
                    cs.locations_one_emp(self.date, subs_id),
                    conn,
                )
                locations = locations[
                    pd.notna(locations["datetime"])
                ]
                if locations.empty:
                    raise ReportException(
                        f"За {self.date} нет локаций. Устройство отключено!"
                    )
                clusters = prepare_clusters(
                    locations,
                    **STAY_LOCATIONS_CONFIG_MTS,
                    **CLUSTERS_CONFIG_MTS
                )
                clusters['uid'] = self.name_id
            else:
                locations = pd.read_sql(
                    cs.locations_one_emp_owntracks(self.date, self.name_id),
                    conn,
                ).sort_values("datetime")
                if locations.empty:
                    raise ReportException(
                        f"За {self.date} нет локаций. Устройство отключено!"
                    )
                self.owntracks = True
                clusters = prepare_clusters(
                    locations,
                    **STAY_LOCATIONS_CONFIG_OWNTRACKS,
                    **CLUSTERS_CONFIG_OWNTRACKS
                )
            clusters['date'] = clusters['datetime'].apply(lambda x: x.date())
            data = {
                '_stmts': stmts,
                'clusters': clusters,
                '_locations': locations,
                'owntracks': self.owntracks
            }
            return data


@dataclass
class OwntracksMtsReportDataGetter:
    date_from: dt.date | str
    date_to: dt.date | str
    division: int | str | None = None
    name_ids: list[int] | None = None
    object_ids: list[int] | None = None

    def __post_init__(self):
        self.date_from = dt.date.fromisoformat(str(self.date_from))
        self.date_to = dt.date.fromisoformat(str(self.date_to))
        self.includes_current_date: bool = dt.date.today() <= self.date_to
        self.empty_locations: list = []

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
        comment = pd.read_sql(
            cs.comment(self.division, self.name_ids), self.conn
        )
        # Частота посещений псу в таблице
        frequency = pd.read_sql(
            cs.frequency(self.division, self.name_ids), self.conn
        )

        self.objects = pd.read_sql(cs.objects(self.object_ids), self.conn)

        # Журнал определяет иточник локаций и кластеров
        # сотрудника в определенный период
        self.journal = pd.read_sql(cs.journal(self.name_ids), self.conn)
        self.journal["period_end"] = self.journal["period_end"].fillna(
            dt.date.today()
        )

        # Кластеры и отсутствующие локации
        mts_clusters = self.mts_clusters()
        owntracks_clusters = self.owntracks_clusters()
        clusters = pd.concat([mts_clusters, owntracks_clusters])

        empty_locations = (
            self.mts_empty_locations() + self.owntracks_empty_locations()
        )

        # Добавление к сотрудникам информации о пустых локациях.
        # Если использовать не только МТС, то вместо mts_empty_locations
        # нужно передать расширенный список с name_id.
        self.employees["empty_locations"] = self.employees.uid.isin(
            empty_locations
        )
        staffers = self.employees\
            .loc[self.employees['staffer'] == True]\
            .uid\
            .unique()\
            .tolist()

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
        empty_locations = list(
            self.conn.execute(cs.empty_locations()).scalars()
        )
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
        empty_locations = (
            set(self.journal[mask].name_id.unique()) - empty_locations
        )
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
        journal = journal[journal['owntracks'] == False]

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
                    **STAY_LOCATIONS_CONFIG_MTS,
                    **CLUSTERS_CONFIG_MTS,
                )
                dates = locs_clusters['datetime'].apply(lambda x: x.date())
                locs_clusters['date'] = dates
                clusters = pd.concat([clusters, locs_clusters])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        clusters = pd.merge(
            clusters,
            journal,
            how="left", right_on="subscriberID", left_on="uid"
        )

        clusters["j_exist"] = (clusters["date"] >= clusters["period_init"]) & (
            clusters["date"] <= clusters["period_end"]
        )
        clusters = clusters[clusters["j_exist"]]
        clusters['uid'] = clusters['name_id']
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
            curr_locs_owntracks = pd.read_sql(
                cs.current_locations_owntracks(employee_ids=self.name_ids),
                self.conn,
            )
            try:
                locs_clusters = prepare_clusters(
                    curr_locs_owntracks,
                    **STAY_LOCATIONS_CONFIG_OWNTRACKS,
                    **CLUSTERS_CONFIG_OWNTRACKS
                )
                dates = locs_clusters['datetime'].apply(lambda x: x.date())
                locs_clusters['date'] = dates

                clusters = pd.concat([clusters, locs_clusters])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )

        clusters = pd.merge(
            clusters, self.journal, how="left",
            left_on="uid", right_on="name_id"
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
    # a = OwntracksMtsReportDataGetter(
    #     "2024-02-01", "2024-05-31", "Коньково"
    # ).get_data()
    # e = OneEmployeeReportDataGetter(1293, "2024-04-26", 2).get_data()
    e = OneEmployeeReportDataGetter(898, "2024-02-02", 3).get_data()
    # print(a)
    pass
