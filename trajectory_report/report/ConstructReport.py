# (основной запрос отчетов)
import pandas as pd
from trajectory_report.report import construct_select as cs
from trajectory_report.database import DB_ENGINE, REDIS_CONN
import datetime as dt
from trajectory_report.report.ClusterGenerator import prepare_clusters
from typing import Optional, List, Union, Any
from trajectory_report.exceptions import ReportException
from dateutil.relativedelta import relativedelta
from sqlalchemy import select
from trajectory_report.models import Statements, Division
import redis
import pickle
import bz2
import json


class CachedReportDataGetter:
    CACHED_SELECTS = {
        'statements': cs.statements_only,
        'employees': cs.employees,
        'schedules': cs.employee_schedules,
        'objects': cs.objects,
        'journal': cs.journal,
        'serves': cs.serves,
        'clusters': cs.clusters,
        'divisions': cs.divisions,
        'current_locations': cs.current_locations,
        'comment': cs.comment,
        'frequency': cs.frequency
    }

    def __init__(self):
        self.__current_db_connection = None
        self._r_conn = REDIS_CONN

        # statements expire date
        one_month = relativedelta(months=1, day=1, hour=0, minute=0, second=0)
        one_day = relativedelta(days=1, hour=0, minute=0, second=0)
        self.__next_month_midnight: int = int((dt.datetime.now() +
                                               one_month).timestamp())
        self.__eight_hours: int = int(
            (dt.datetime.now()+dt.timedelta(hours=8)).timestamp()
        )
        self.__prev_month: dt.date = dt.date.today() - one_month
        self.__current_month = ((dt.date.today() + one_month)
                                - dt.timedelta(days=1))
        self.__current_day = int((dt.datetime.now()+one_day).timestamp())
        self.expire_time_dict = {
            'employees': self.__eight_hours,
            'schedules': self.__eight_hours,
            'objects': self.__eight_hours,
            'journal': self.__current_day,
            'serves': self.__eight_hours,
            'clusters': self.__current_day,
            'divisions': self.__eight_hours,
            'current_locations': dt.datetime.now()+dt.timedelta(seconds=200),
            'statements': self.__next_month_midnight,
            'comment': self.__current_day,
            'frequency': self.__current_day
        }

    @property
    def _connection(self):
        if not self.__current_db_connection:
            self._current_db_connection = DB_ENGINE.connect()
            return self._current_db_connection
        if not self.__current_db_connection.connection.connection.is_connected():
            self.__current_db_connection.connection.connection.reconnect()
        return self.__current_db_connection

    def _connection_close(self):
        # после инициализации закрыть соединение с бд, если оно есть:
        if self.__current_db_connection:
            self.__current_db_connection.close()

    def get_data(self,
                 date_from: Union[dt.date, str],
                 date_to: Union[dt.date, str],
                 division: Optional[Union[int, str]] = None,
                 name_ids: Optional[List[int]] = None,
                 object_ids: Optional[List[int]] = None
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
        data['_stmts'] = stmts
        data['_journal'] = journal
        data['_schedules'] = schedules
        data['_serves'] = serves
        data['_clusters'] = clusters
        data['_comment'] = comment
        data['_frequency'] = frequency
        return data

    def __get_divisions(self) -> dict:
        fetched = self._r_conn.get('divisions')
        if not fetched:
            res = self._connection.execute(select(Division.id, Division.division)).all()
            fetched = json.dumps({i.division: i.id for i in res})
            self._r_conn.set('divisions', fetched)
            self._r_conn.expireat('divisions', self.__current_day)
        return json.loads(fetched)

    def __get_clusters(self, subs_ids, includes_current_date) -> pd.DataFrame:
        clusters = self.__get_cached_or_updated('clusters')
        clusters = clusters[clusters['subscriberID'].isin(subs_ids)]
        clusters = clusters[clusters['date'] >= self._date_from]
        clusters = clusters[clusters['date'] <= self._date_to]

        if includes_current_date:
            curr_locs = self.__get_cached_or_updated('current_locations')
            curr_locs = curr_locs[curr_locs['subscriberID'].isin(subs_ids)]
            curr_locs['date'] = (curr_locs['locationDate']
                                 .apply(lambda x: x.date()))
            try:
                clusters = pd.concat([clusters, prepare_clusters(curr_locs)])
            except (TypeError, AttributeError):
                print("Кластеры по текущим локациям не были сформированы. "
                      "Возможно, из-за недостатка кол-ва локаций.")
        return clusters

    def __get_serves(self, name_ids) -> pd.DataFrame:
        serves = self.__get_cached_or_updated('serves')
        serves = serves[serves['name_id'].isin(name_ids)]
        serves = serves[serves['date'] >= self._date_from]
        serves = serves[serves['date'] <= self._date_to]
        return serves

    def __get_schedules(self, name_ids) -> pd.DataFrame:
        schedules = self.__get_cached_or_updated('schedules')
        schedules = schedules[schedules['name_id'].isin(name_ids)]
        return schedules

    def __get_journal(self, name_ids) -> pd.DataFrame:
        journal = self.__get_cached_or_updated('journal')
        journal = journal[journal['name_id'].isin(name_ids)]
        journal.loc['period_end'] = journal['period_end'].fillna(
            dt.date.today())
        return journal

    def __get_statements(self,
                         division: Optional[int] = None,
                         name_ids: Optional[List[int]] = None,
                         object_ids: Optional[List[int]] = None
                         ) -> pd.DataFrame:
        cached = self._r_conn.hgetall('statements')
        if not cached:
            db_res = self._connection.execute(select(
                Statements.division,
                Statements.name_id,
                Statements.object_id,
                Statements.date,
                Statements.statement
            ).where(Statements.date >= self.__prev_month)).all()
            res = {}
            for i in db_res:
                key = (f"{i.division},{i.name_id},"
                       f"{i.object_id},{i.date.isoformat()}").encode()
                val = i.statement.encode()
                res[key] = val

            self._r_conn.hmset('statements', res)
            self._r_conn.expireat('statements',
                                  self.expire_time_dict['statements'])
            cached = res
        cached = {
            tuple(k.decode().split(',')): v.decode()
            for k, v in cached.items()
        }
        index = pd.MultiIndex.from_tuples(
            cached.keys(),
            names=['division', 'name_id', 'object_id', 'date']
        )
        statements = pd.DataFrame(
            list(cached.values()),
            index=index, columns=['statement']
        ).reset_index()
        statements[['division', 'name_id', 'object_id']] = statements[
            ['division', 'name_id', 'object_id']].astype(int)
        statements['date'] = statements.date.apply(lambda x: dt.date.fromisoformat(x))

        if division:
            statements = statements[statements['division'] == division]
        if name_ids:
            statements = statements[statements['name_id'].isin(name_ids)]
        if object_ids:
            statements = statements[statements['name_id'].isin(object_ids)]

        statements = statements[(statements['date'] >= self._date_from) &
                                (statements['date'] <= self._date_to)]

        if not len(statements):
            raise ReportException(f'Не найдено заявленных выходов в период '
                                  f'с {self._date_from} до {self._date_to}')

        objects = self.__get_cached_or_updated('objects')
        employees = self.__get_cached_or_updated('employees')

        statements = pd.merge(statements, objects, on=['object_id'])
        statements = pd.merge(statements, employees, on=['name_id'])
        return statements[['name_id', 'object_id', 'name', 'object',
                           'longitude', 'latitude', 'date', 'statement',
                           'division']]

    def __get_comment(self, name_ids: List[int]):
        comment = self.__get_cached_or_updated('comment')
        comment = comment[comment['name_id'].isin(name_ids)]
        return comment

    def __get_frequency(self, name_ids: List[int]):
        frequency = self.__get_cached_or_updated('frequency')
        frequency = frequency[frequency['name_id'].isin(name_ids)]
        return frequency

    def __get_cached_or_updated(self, key):
        res = self.__get_from_redis(key)
        if res is None:
            res = pd.read_sql(
                CachedReportDataGetter.CACHED_SELECTS[key](
                    date_from=self.__prev_month),
                self._connection
                )
            self.__send_to_redis(key, res)
        return res

    def __get_from_redis(self, key: str) -> Any:
        """"Fetch from redis by key, decompress and unpickle"""
        fetched = self._r_conn.get(key)
        if not fetched:
            return None
        return pickle.loads(bz2.decompress(fetched))

    def __send_to_redis(self, key: str, obj: Any) -> bool:
        """Compress, pickle and set as a key"""
        self._r_conn.set(key, bz2.compress(pickle.dumps(obj)))
        self._r_conn.expireat(key, self.expire_time_dict.get(key))
        return True


class DatabaseReportDataGetter:

    @staticmethod
    def get_data(
            date_from: Union[dt.date, str],
            date_to: Union[dt.date, str],
            division: Optional[Union[int, str]] = None,
            name_ids: Optional[List[int]] = None,
            object_ids: Optional[List[int]] = None
    ) -> dict:
        """Формирует select и запрашивает их из БД"""
        date_from = dt.date.fromisoformat(str(date_from))
        date_to = dt.date.fromisoformat(str(date_to))
        includes_current_date: bool = dt.date.today() <= date_to

        """ПОЛУЧЕНИЕ НЕОБХОДИМЫХ ТАБЛИЦ ИЗ БД"""
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(cs.statements(
                date_from=date_from,
                date_to=date_to,
                division=division,
                name_ids=name_ids,
                object_ids=object_ids
            ), conn)
            if not len(stmts):
                raise ReportException(f'Не найдено заявленных выходов в период '
                                      f'с {date_from} до {date_to}')
            name_ids = stmts.name_id.unique().tolist()

            journal = pd.read_sql(cs.journal(name_ids), conn)
            journal['period_end'] = journal['period_end'].fillna(
                dt.date.today())
            subs_ids = journal.subscriberID.unique().tolist()

            schedules = pd.read_sql(cs.employee_schedules(name_ids), conn)
            serves = pd.read_sql(cs.serves(date_from, date_to, name_ids), conn)
            clusters = pd.read_sql(cs.clusters(date_from, date_to, subs_ids),
                                   conn)
            if includes_current_date:
                current_locations = pd.read_sql(
                    cs.current_locations(subs_ids),
                    conn
                )
                current_locations['date'] = current_locations['locationDate'] \
                    .apply(lambda x: x.date())
            comment = pd.read_sql(cs.comment(division, name_ids), conn)
            frequency = pd.read_sql(cs.frequency(division, name_ids), conn)

        if includes_current_date:
            try:
                clusters_from_locations = prepare_clusters(current_locations)
                clusters = pd.concat([clusters,
                                      clusters_from_locations])
            except (TypeError, AttributeError):
                print("Кластеры по текущим локациям не были сформированы. "
                      "Возможно, из-за недостатка кол-ва локаций.")
        data = dict()
        data['_stmts'] = stmts
        data['_journal'] = journal
        data['_schedules'] = schedules
        data['_serves'] = serves
        data['_clusters'] = clusters
        data['_comment'] = comment
        data['_frequency'] = frequency
        return data


class OneEmployeeReportDataGetter:

    def __init__(self,
                 name_id: int,
                 date: Union[dt.date, str],
                 division: Union[int, str],
                 ) -> None:
        date = dt.date.fromisoformat(str(date))
        (self._stmts,
         self.clusters,
         self._locations) = self._query_data(name_id, division, date)

    @staticmethod
    def _query_data(name_id: int, division: Union[int, str], date: dt.date):
        with DB_ENGINE.connect() as conn:
            stmts = pd.read_sql(cs.statements_one_emp(date, name_id, division),
                                conn)
            journal = pd.read_sql(cs.journal_one_emp(name_id), conn)
            journal['period_end'] = journal['period_end'].fillna(
                dt.date.today())
            journal = journal \
                .loc[(journal['period_init'] <= date)
                     & (date <= journal['period_end'])]
            try:
                subscriber_id = int(journal.subscriberID.iloc[0])
            except IndexError:
                raise ReportException(
                    f"За сотрудником не закреплено ни одного "
                    f"устройства в этот день ({date})")

            locations = pd.read_sql(cs.locations_one_emp(date, subscriber_id),
                                    conn)
            valid_locations = locations[pd.notna(locations['locationDate'])]
            if not len(locations) or not len(valid_locations):
                raise ReportException(f"По данному сотруднику не обнаружено "
                                      f"локаций за {date}.")
            clusters = prepare_clusters(valid_locations)
            return stmts, clusters, locations


def report_data_factory(date_from: Union[dt.date, str], *args, use_cache=True,
                        **kwargs
                        ) -> dict:
    try:
        redis_available = REDIS_CONN.ping()
    except redis.ConnectionError:
        redis_available = False

    date_from = dt.date.fromisoformat(str(date_from))
    cache_date_from = \
       ((dt.date.today().replace(day=1)) - dt.timedelta(days=1)).replace(day=1)
    if date_from >= cache_date_from and redis_available and use_cache:
        data = CachedReportDataGetter().get_data(date_from, *args, **kwargs)
    else:
        data = DatabaseReportDataGetter().get_data(date_from, *args, **kwargs)
    return data



