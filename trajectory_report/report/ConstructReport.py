# (основной запрос отчетов)
import pandas as pd
from trajectory_report.report import construct_select as cs
from trajectory_report.database import DB_ENGINE, ASYNC_DB_ENGINE, REDIS_CONN
import datetime as dt
from trajectory_report.report.ClusterGenerator import prepare_clusters
from typing import Optional, List, Union, Any
from trajectory_report.exceptions import ReportException
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from sqlalchemy.orm import Session
from trajectory_report.models import Statements, Division, Employees
import pickle
import bz2
import json
from asyncio import create_task, gather
import asyncio
from dataclasses import dataclass


class CachedReportDataGetter:
    CACHED_SELECTS = {
        "statements": cs.statements_only,
        "employees": cs.employees,
        "schedules": cs.employee_schedules,
        "objects": cs.objects,
        "journal": cs.journal,
        "serves": cs.serves,
        "clusters": cs.clusters,
        "divisions": cs.divisions,
        "current_locations": cs.current_locations_mts,
        "comment": cs.comment,
        "frequency": cs.frequency,
    }

    def __init__(self):
        self.__current_db_connection = None
        self._r_conn = REDIS_CONN

        # statements expire date
        one_month = relativedelta(months=1, day=1, hour=0, minute=0, second=0)
        one_day = relativedelta(days=1, hour=0, minute=0, second=0)
        self.__next_month_midnight: int = int(
            (dt.datetime.now() + one_month).timestamp()
        )
        self.__eight_hours: int = int(
            (dt.datetime.now() + dt.timedelta(hours=8)).timestamp()
        )
        self.__prev_month: dt.date = dt.date.today() - one_month
        self.__current_month = (dt.date.today() + one_month) - dt.timedelta(
            days=1
        )
        self.__current_day = int((dt.datetime.now() + one_day).timestamp())
        self.expire_time_dict = {
            "employees": self.__eight_hours,
            "schedules": self.__eight_hours,
            "objects": self.__eight_hours,
            "journal": self.__current_day,
            "serves": self.__eight_hours,
            "clusters": self.__current_day,
            "divisions": self.__eight_hours,
            "current_locations": dt.datetime.now() + dt.timedelta(seconds=200),
            "statements": self.__next_month_midnight,
            "comment": self.__current_day,
            "frequency": self.__current_day,
        }

    @property
    def _connection(self):
        if not self.__current_db_connection:
            self._current_db_connection = DB_ENGINE.connect()
            return self._current_db_connection
        if (
            not self.__current_db_connection.connection.connection.is_connected()
        ):
            self.__current_db_connection.connection.connection.reconnect()
        return self.__current_db_connection

    def _connection_close(self):
        # после инициализации закрыть соединение с бд, если оно есть:
        if self.__current_db_connection:
            self.__current_db_connection.close()

    def get_data(
        self,
        date_from: Union[dt.date, str],
        date_to: Union[dt.date, str],
        division: Optional[Union[int, str]] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
    ) -> dict:
        self._date_from = dt.date.fromisoformat(str(date_from))
        self._date_to = dt.date.fromisoformat(str(date_to))

        includes_current_date: bool = dt.date.today() <= self._date_to

        divisions: dict = self.__get_divisions()
        if isinstance(division, str):
            division = divisions.get(division)

        stmts = self.__get_statements(division, name_ids, object_ids)
        name_ids = stmts.name_id.unique().tolist()

        journal = self.__get_journal(name_ids)
        subs_ids = journal.subscriberID.unique().tolist()

        schedules = self.__get_schedules(name_ids)

        serves = self.__get_serves(name_ids)

        clusters = self.__get_clusters(subs_ids, includes_current_date)

        comment = self.__get_comment(name_ids)
        frequency = self.__get_frequency(name_ids)

        self._connection_close()

        data = dict()
        data["_stmts"] = stmts
        data["_journal"] = journal
        data["_schedules"] = schedules
        data["_serves"] = serves
        data["_clusters"] = clusters
        data["_comment"] = comment
        data["_frequency"] = frequency
        return data

    def __get_divisions(self) -> dict:
        fetched = self._r_conn.get("divisions")
        if not fetched:
            res = self._connection.execute(
                select(Division.id, Division.division)
            ).all()
            fetched = json.dumps({i.division: i.id for i in res})
            self._r_conn.set("divisions", fetched)
            self._r_conn.expireat("divisions", self.__current_day)
        return json.loads(fetched)

    def __get_clusters(self, subs_ids, includes_current_date) -> pd.DataFrame:
        clusters = self.__get_cached_or_updated("clusters")
        clusters = clusters[clusters["subscriberID"].isin(subs_ids)]
        clusters = clusters[clusters["date"] >= self._date_from]
        clusters = clusters[clusters["date"] <= self._date_to]

        if includes_current_date:
            curr_locs = self.__get_cached_or_updated("current_locations")
            curr_locs = curr_locs[curr_locs["subscriberID"].isin(subs_ids)]
            curr_locs["date"] = curr_locs["locationDate"].apply(
                lambda x: x.date()
            )
            try:
                clusters = pd.concat([clusters, prepare_clusters(curr_locs)])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        return clusters

    def __get_serves(self, name_ids) -> pd.DataFrame:
        serves = self.__get_cached_or_updated("serves")
        serves = serves[serves["name_id"].isin(name_ids)]
        serves = serves[serves["date"] >= self._date_from]
        serves = serves[serves["date"] <= self._date_to]
        return serves

    def __get_schedules(self, name_ids) -> pd.DataFrame:
        schedules = self.__get_cached_or_updated("schedules")
        schedules = schedules[schedules["name_id"].isin(name_ids)]
        return schedules

    def __get_journal(self, name_ids) -> pd.DataFrame:
        journal = self.__get_cached_or_updated("journal")
        journal = journal[journal["name_id"].isin(name_ids)]
        journal.loc["period_end"] = journal["period_end"].fillna(
            dt.date.today()
        )
        return journal

    def __get_statements(
        self,
        division: Optional[int] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
    ) -> pd.DataFrame:
        cached = self._r_conn.hgetall("statements")
        if not cached:
            db_res = self._connection.execute(
                select(
                    Statements.division,
                    Statements.name_id,
                    Statements.object_id,
                    Statements.date,
                    Statements.statement,
                ).where(Statements.date >= self.__prev_month)
            ).all()
            res = {}
            for i in db_res:
                key = (
                    f"{i.division},{i.name_id},"
                    f"{i.object_id},{i.date.isoformat()}"
                ).encode()
                val = i.statement.encode()
                res[key] = val

            self._r_conn.hmset("statements", res)
            self._r_conn.expireat(
                "statements", self.expire_time_dict["statements"]
            )
            cached = res
        cached = {
            tuple(k.decode().split(",")): v.decode() for k, v in cached.items()
        }
        index = pd.MultiIndex.from_tuples(
            cached.keys(), names=["division", "name_id", "object_id", "date"]
        )
        statements = pd.DataFrame(
            list(cached.values()), index=index, columns=["statement"]
        ).reset_index()
        statements[["division", "name_id", "object_id"]] = statements[
            ["division", "name_id", "object_id"]
        ].astype(int)
        statements["date"] = statements.date.apply(
            lambda x: dt.date.fromisoformat(x)
        )

        if division:
            statements = statements[statements["division"] == division]
        if name_ids:
            statements = statements[statements["name_id"].isin(name_ids)]
        if object_ids:
            statements = statements[statements["name_id"].isin(object_ids)]

        statements = statements[
            (statements["date"] >= self._date_from)
            & (statements["date"] <= self._date_to)
        ]

        if not len(statements):
            raise ReportException(
                f"Не найдено заявленных выходов в период "
                f"с {self._date_from} до {self._date_to}"
            )

        objects = self.__get_cached_or_updated("objects")
        employees = self.__get_cached_or_updated("employees")

        statements = pd.merge(statements, objects, on=["object_id"])
        statements = pd.merge(statements, employees, on=["name_id"])
        return statements[
            [
                "name_id",
                "object_id",
                "name",
                "object",
                "longitude",
                "latitude",
                "date",
                "statement",
                "division",
            ]
        ]

    def __get_comment(self, name_ids: List[int]):
        comment = self.__get_cached_or_updated("comment")
        comment = comment[comment["name_id"].isin(name_ids)]
        return comment

    def __get_frequency(self, name_ids: List[int]):
        frequency = self.__get_cached_or_updated("frequency")
        frequency = frequency[frequency["name_id"].isin(name_ids)]
        return frequency

    def __get_cached_or_updated(self, key):
        res = self.__get_from_redis(key)
        if res is None:
            res = pd.read_sql(
                CachedReportDataGetter.CACHED_SELECTS[key](
                    date_from=self.__prev_month
                ),
                self._connection,
            )
            self.__send_to_redis(key, res)
        return res

    def __get_from_redis(self, key: str) -> Any:
        """ "Fetch from redis by key, decompress and unpickle"""
        fetched = self._r_conn.get(key)
        if not fetched:
            return None
        return pickle.loads(bz2.decompress(fetched))

    def __send_to_redis(self, key: str, obj: Any) -> bool:
        """Compress, pickle and set as a key"""
        self._r_conn.set(key, bz2.compress(pickle.dumps(obj)))
        self._r_conn.expireat(key, self.expire_time_dict.get(key))
        return True


class AsyncReportDataGetter:
    def get_data(self, *args, **kwargs):
        return asyncio.run(self.trigger(*args, **kwargs))

    async def trigger(
        self,
        date_from: Union[dt.date, str],
        date_to: Union[dt.date, str],
        division: Optional[Union[int, str]] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
    ) -> dict:
        """Формирует select и запрашивает их из БД"""
        date_from = dt.date.fromisoformat(str(date_from))
        date_to = dt.date.fromisoformat(str(date_to))
        includes_current_date: bool = dt.date.today() <= date_to
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(
                cs.statements(
                    date_from=date_from,
                    date_to=date_to,
                    division=division,
                    name_ids=name_ids,
                    object_ids=object_ids,
                ),
                conn,
            )
            journal = pd.read_sql(cs.journal(name_ids), conn)
            conn.close()
        if not len(stmts):
            raise ReportException(
                f"Не найдено заявленных выходов в период "
                f"с {date_from} до {date_to}"
            )
        name_ids = stmts.name_id.unique().tolist()
        journal["period_end"] = journal["period_end"].fillna(dt.date.today())
        subs_ids = journal.subscriberID.unique().tolist()
        tasks = []
        selects = {
            "schedules": cs.employee_schedules(name_ids),
            "serves": cs.serves(date_from, date_to, name_ids),
            "clusters": cs.clusters(date_from, date_to, subs_ids),
            "comment": cs.comment(division, name_ids),
            "frequency": cs.frequency(division, name_ids),
            "current_locations": cs.current_locations_mts(subs_ids),
        }
        selects_cols = {
            k: [i.name for i in v.selected_columns] for k, v in selects.items()
        }
        tasks.extend(
            [
                create_task(
                    self.async_fetch(selects["schedules"]), name="schedules"
                ),
                create_task(
                    self.async_fetch(selects["serves"]), name="serves"
                ),
                create_task(
                    self.async_fetch(selects["clusters"]), name="clusters"
                ),
                create_task(
                    self.async_fetch(selects["comment"]), name="comment"
                ),
                create_task(
                    self.async_fetch(selects["frequency"]), name="frequency"
                ),
            ]
        )
        if includes_current_date:
            tasks.append(
                create_task(
                    self.async_fetch(selects["current_locations"]),
                    name="current_locations",
                )
            )
        await gather(*tasks)
        await ASYNC_DB_ENGINE.dispose()
        results = {
            t.get_name(): pd.DataFrame(
                t.result(), columns=selects_cols[t.get_name()]
            )
            for t in tasks
        }
        pass

        if includes_current_date:
            try:
                current_locations = results["current_locations"]
                current_locations["date"] = current_locations[
                    "locationDate"
                ].apply(lambda x: x.date())
                clsters_from_locs = prepare_clusters(current_locations)
                results["clusters"] = pd.concat(
                    [results["clusters"], clsters_from_locs]
                )
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        data = dict()
        data["_stmts"] = stmts
        data["_journal"] = journal
        data["_schedules"] = results["schedules"]
        data["_serves"] = results["serves"]
        data["_clusters"] = results["clusters"]
        data["_comment"] = results["comment"]
        data["_frequency"] = results["frequency"]
        return data

    @staticmethod
    async def async_fetch(sel):
        async with ASYNC_DB_ENGINE.connect() as conn:
            cursor_result = await conn.execute(sel)
            return cursor_result.fetchall()


class DatabaseReportDataGetter:

    @staticmethod
    def get_data(
        date_from: Union[dt.date, str],
        date_to: Union[dt.date, str],
        division: Optional[Union[int, str]] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
        objects_with_address: bool = False,  # отображ. адресов на карте
        # уведомл. об отсут. локац.
        check_for_empty_locations: bool = False,
    ) -> dict:
        """Запрашивает данные для формирования отчета из БД.

        objects_with_address - дополнительно запросить адреса ПСУ для
        отображения на карте

        check_for_empty_locations - дополнительно проверить, есть ли сотрудники
        без локаций за последнее время, о которых нужно уведомить
        """
        date_from = dt.date.fromisoformat(str(date_from))
        date_to = dt.date.fromisoformat(str(date_to))
        includes_current_date: bool = dt.date.today() <= date_to

        """ПОЛУЧЕНИЕ НЕОБХОДИМЫХ ТАБЛИЦ ИЗ БД"""
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(
                cs.statements(
                    date_from=date_from,
                    date_to=date_to,
                    division=division,
                    name_ids=name_ids,
                    object_ids=object_ids,
                    objects_with_address=objects_with_address,
                ),
                conn,
            )
            if not len(stmts):
                raise ReportException(
                    f"Не заполнена таблица выходов в период "
                    f"с {date_from} до {date_to}"
                )

            name_ids = stmts.name_id.unique().tolist()
            object_ids = stmts.object_id.unique().tolist()

            journal = pd.read_sql(cs.journal(name_ids), conn)
            journal["period_end"] = journal["period_end"].fillna(
                dt.date.today()
            )
            subs_ids = journal.subscriberID.unique().tolist()

            schedules = pd.read_sql(cs.employee_schedules(name_ids), conn)
            serves = pd.read_sql(cs.serves(date_from, date_to, name_ids), conn)

            clusters = pd.read_sql(
                cs.clusters(date_from, date_to, subs_ids), conn
            )
            if includes_current_date:
                current_locations = pd.read_sql(
                    cs.current_locations_mts(subs_ids), conn
                )
                current_locations["date"] = current_locations[
                    "locationDate"
                ].apply(lambda x: x.date())

            staffers = [
                i for i in conn.execute(cs.staffers(name_ids)).scalars()
            ]

            comment = pd.read_sql(cs.comment(division, name_ids), conn)
            frequency = pd.read_sql(cs.frequency(division, name_ids), conn)
            income = pd.read_sql(cs.income(object_ids), conn)
            no_payments = [
                i for i in conn.execute(cs.no_payments(object_ids)).scalars()
            ]
            empty_locations: list = []
            employees_with_phone: pd.DataFrame = pd.DataFrame(
                columns=["name_id", "name", "phone"]
            )
            if check_for_empty_locations and includes_current_date:
                empty_locations = [
                    i for i in conn.execute(cs.empty_locations()).scalars()
                ]
                employees_with_phone = pd.read_sql(
                    cs.employees_with_nameid_name_phone(name_ids), conn
                )

        if includes_current_date:
            try:
                clusters_from_locations = prepare_clusters(current_locations)
                clusters = pd.concat([clusters, clusters_from_locations])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        data = dict()
        data["_stmts"] = stmts
        data["_journal"] = journal
        data["_schedules"] = schedules
        data["_serves"] = serves
        data["_clusters"] = clusters
        data["_comment"] = comment
        data["_frequency"] = frequency
        data["_income"] = income
        data["_no_payments"] = no_payments
        data["_empty_locations"] = empty_locations
        data["_employees_with_phone"] = employees_with_phone
        data["_staffers"] = staffers
        return data


class OneEmployeeReportDataGetter:

    def __init__(
        self,
        name_id: int,
        date: Union[dt.date, str],
        division: Union[int, str],
    ) -> None:
        date = dt.date.fromisoformat(str(date))
        (self._stmts, self.clusters, self._locations) = self._query_data(
            name_id, division, date
        )

    @staticmethod
    def _query_data(name_id: int, division: Union[int, str], date: dt.date):
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(
                cs.statements_one_emp(date, name_id, division), conn
            )
            journal = pd.read_sql(cs.journal_one_emp(name_id), conn)
            journal["period_end"] = journal["period_end"].fillna(
                dt.date.today()
            )
            journal = journal.loc[
                (journal["period_init"] <= date)
                & (date <= journal["period_end"])
            ]
            try:
                subscriber_id = int(journal.subscriberID.iloc[0])
            except IndexError:
                raise ReportException(
                    f"Не подключен к отслеживанию в этот день ({date})"
                )

            locations = pd.read_sql(
                cs.locations_one_emp(date, subscriber_id), conn
            )
            valid_locations = locations[pd.notna(locations["locationDate"])]
            if not len(locations) or not len(valid_locations):
                raise ReportException(
                    f"За {date} нет локаций. Устройство отключено!"
                )
            clusters = prepare_clusters(valid_locations)
            return stmts, clusters, locations


@dataclass
class OneEmployeeDataGetterExtended:
    name_id: int
    date: dt.date | str
    division: int | str | None = None

    def __post_init__(self):
        self.date = dt.date.fromisoformat(str(self.date))
        self.conn = DB_ENGINE.connect()

    def get_data(self) -> dict:
        stmts = pd.read_sql(
            cs.statements_one_emp_extended(
                self.date, self.name_id, self.division
            ),
            self.conn,
        )
        # with Session(self.conn) as session:
        #     employee = session.query(Employees)\
        #         .filter_by(name_id=self.name_id)\
        #         .first()

        journal = pd.read_sql(cs.journal_one_emp(self.name_id), self.conn)
        journal["period_end"] = journal["period_end"].fillna(dt.date.today())

        journal = journal.loc[
            (journal["period_init"] <= self.date)
            & (self.date <= journal["period_end"])
        ]
        if journal.empty:
            raise ReportException(
                f"Не подключен к отслеживанию в этот день ({self.date})"
            )

        try:
            subscriber_id = int(journal.subscriberID.iloc[0])
        except IndexError:
            raise ReportException(
                f"Не подключен к отслеживанию в этот день ({self.date})"
            )

        locations = pd.read_sql(
            cs.locations_one_emp(self.date, subscriber_id), self.conn
        )
        valid_locations = locations[pd.notna(locations["locationDate"])]
        if not len(locations) or not len(valid_locations):
            raise ReportException(
                f"За {self.date} нет локаций. Устройство отключено!"
            )
        clusters = prepare_clusters(valid_locations)

        self.conn.close()

        data = {}
        data["_clusters"] = clusters
        data["_stmts"] = stmts
        data["_locations"] = locations
        return data


@dataclass
class OwntracksMtsReportDataGetter:
    date_from: Union[dt.date, str]
    date_to: Union[dt.date, str]
    division: Optional[Union[int, str]] = None
    name_ids: Optional[List[int]] = None
    object_ids: Optional[List[int]] = None

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

        self.name_ids = stmts.name_id.unique().tolist()
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

        # МТС часть, включая Журнал, кластеры и отсутствующие локации
        clusters = self.mts_clusters()
        mts_empty_locations = self.mts_empty_locations()

        # Добавление к сотрудникам информации о пустых локациях.
        # Если использовать не только МТС, то вместо mts_empty_locations
        # нужно передать расширенный список с name_id.
        self.employees["empty_locations"] = self.employees.name_id.isin(
            mts_empty_locations
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

    def mts_clusters(self) -> pd.DataFrame:
        subs_ids = self.journal.subscriberID.unique().tolist()

        clusters = pd.read_sql(
            cs.clusters(self.date_from, self.date_to, subs_ids), self.conn
        )
        if self.includes_current_date:
            current_locations = pd.read_sql(
                cs.current_locations_mts(subs_ids), self.conn
            )
            current_locations["date"] = current_locations[
                "locationDate"
            ].apply(lambda x: x.date())

        if self.includes_current_date:
            try:
                clusters_from_locations = prepare_clusters(current_locations)
                clusters = pd.concat([clusters, clusters_from_locations])
            except (TypeError, AttributeError):
                print(
                    "Кластеры по текущим локациям не были сформированы. "
                    "Возможно, из-за недостатка кол-ва локаций."
                )
        clusters = pd.merge(
            clusters, self.journal, how="left", on="subscriberID"
        )

        clusters["j_exist"] = (clusters["date"] >= clusters["period_init"]) & (
            clusters["date"] <= clusters["period_end"]
        )
        clusters = clusters[clusters["j_exist"]]
        return clusters[
            [
                "name_id",
                "date",
                "datetime",
                "leaving_datetime",
                "longitude",
                "latitude",
                "cluster",
            ]
        ]


def report_data_factory(*args, **kwargs) -> dict:
    data = OwntracksMtsReportDataGetter(*args, **kwargs).get_data()
    return data


def one_employee_data_factory(*args, **kwargs) -> dict:
    data = OneEmployeeDataGetterExtended(*args, **kwargs).get_data()
    return data


if __name__ == "__main__":
    a = OwntracksMtsReportDataGetter(
        "2024-02-01", "2024-02-27", "ПВТ1"
    ).get_data()
    # e = OneEmployeeDataGetterExtended(15, "2024-02-13", 2).get_data()
    # print(a)
    pass
