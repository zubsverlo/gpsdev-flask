# ~~ЖУРНАЛ ИСПОЛЬЗОВАНИЯ ID~~
# этот модуль предназначен для отслеживания, в какой период времени
# и кем использовался конкретный ID (subscriberID в МТС).
# модуль редактирует записи владельца ID в БД и добавляет новые.
# журнал реагирует на изменения в MTS, поэтому регулярно запрашивает
# по API актуальный список абонентов.
# ~АЛГОРИТМ РАБОТЫ~
# Запрашивается список абонентов из мтс
# Из БД запрашивается список неуволенных сотрудников
# И словарь из актуальных записей journal.
# Сотрудники без subscriberID образуют список неотслеживаемых
# Сотрудники, которые были уволены, но ещё отслеживаются,
# дополняют список на удаление, как и сотрудники,
# которых и в помине нет.
# По остальным нужно сравнить subscriberID. Если он не совпадает - значит
# было изменение. Текущую запись в БД нужно завершить, а затем открыть новую,
# с тем же именем и с текущей даты.

"""Нужно добавить метод, который возващает сотрудников из списка уволенных
в список актуальных, если оказалось, что после "У" появились другие выходы.
Нужно анализировать таблицу statements, запросить их для всех уволенных
сотрудников и проанализировать.

Ещё, когда сотрудник перестает отслеживаться в мтс, нужно закрывать период
в journal.
Ещё хотелось бы видеть подразделение, в котором работал сотрудник, когда его
нужно удалить из отслеживания, если его можно получить.
"""

from trajectory_report.api.mts import get_subscribers
from trajectory_report.database import DB_ENGINE, REDIS_CONN
import datetime as dt
from trajectory_report.models import Employees, Statements, Journal, Division
from sqlalchemy import select, update, insert, and_
from sqlalchemy.orm import Session
import pandas as pd
from collections import defaultdict
from numpy import nan
from sqlalchemy import func, distinct
from time import perf_counter
from typing import Any
import pickle
import bz2


class JournalManager:

    def __init__(self):
        self.session = Session(DB_ENGINE)
        # Работающие на текущий момент сотрудники
        self.emps = self.get_employees_actual()
        # Список сотрудников из МТС
        mts = get_subscribers()
        self.mts = {i["name"]: i["subscriberID"] for i in mts}
        # self.company_dict = {i['subscriberID']: i['company'] for i in mts}
        self.company_dict = defaultdict(list)
        for i in mts:
            self.company_dict[i["company"]].append(i["subscriberID"])
        # получить открытые записи из журнала:
        self.journal_db = self.get_journal_actual()

        self.trackable = set.intersection(
            set(self.mts.keys()), set([i["name"] for i in self.emps])
        )
        # self.divisions_dict = self.get_divisions_dict()
        pass

    def set_quit_date(self):
        """Проставляет дату увольнения сотрудникам, которые попадают под
        критерий: в шахматке проставлено "У" или последняя информация в
        statements была более 28 дней назад.
        """
        sel = select(Employees.name_id).where(Employees.quit_date == None)
        not_fired = self.session.execute(sel).all()
        not_fired = [i.name_id for i in not_fired]

        sel = (
            select(Statements.name_id, Statements.date, Statements.statement)
            .where(
                Statements.date >= (dt.date.today() - dt.timedelta(days=45))
            )
            .where(Statements.name_id.in_(not_fired))
        )
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        res = pd.DataFrame(res)

        def last_day(x):
            x = x.sort_values(by="date", ascending=False)
            return x.iloc[0]

        res = res.groupby(by=["name_id"], as_index=False).apply(
            lambda x: last_day(x)
        )

        res["quit_date"] = res.apply(
            lambda x: (
                x.date
                if x.statement == "У"
                or (dt.date.today() - x.date) > dt.timedelta(days=28)
                else nan
            ),
            axis=1,
        )
        res = res[res["quit_date"].notna()]
        res = res[["name_id", "quit_date"]].to_dict(orient="records")
        for i in res:
            sel = (
                update(Employees)
                .where(Employees.name_id == i["name_id"])
                .values(quit_date=i["quit_date"])
            )
            self.session.execute(sel)
        self.session.commit()
        print("allright, employees now are fired:", len(res))

    def get_employees_actual(self):
        """Получить список словарей со всеми сотрудниками,
        которые не были уволены"""
        sel = (
            select(
                Employees.name,
                Employees.name_id,
                Employees.phone,
                Division.division,
            )
            .join(Division)
            .where(Employees.quit_date == None)
        )
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        return res

    @property
    def untrackable(self):
        """Добавленные, но не подключенные сотрудники
        [{name, name_id, phone, division}]"""
        names = set([i["name"] for i in self.emps]) - set(self.mts.keys())
        return [i for i in self.emps if i["name"] in names]

    def get_journal_actual(self):
        """Получить из БД список subscriberID по всем текущим записям
        отслеживания"""
        sel = select(Journal.name_id, Journal.subscriberID).where(
            Journal.period_end == None
        )
        self.session.execute(sel)
        return {
            i.name_id: i.subscriberID for i in self.session.execute(sel).all()
        }

    def journal_usage_close(self, subscriber_id, name_id):
        """Закрытие периода владения устройством"""
        sel = (
            update(Journal)
            .where(
                Journal.subscriberID == subscriber_id,
                Journal.name_id == name_id,
                Journal.period_end == None,
            )
            .values(period_end=dt.date.today() - dt.timedelta(days=1))
        )
        self.session.execute(sel)

    def journal_usage_open(self, sub_id, name_id):
        """Открытие периода владения устройством"""
        self.session.add(
            Journal(
                subscriberID=sub_id,
                name_id=name_id,
                period_init=dt.date.today(),
            )
        )

    def update_journal(self):
        """Обновление journal. По добавляются записи по новеньким,
        проставляются изменения по стареньким."""
        for i in self.emps:
            i["subscriberID"] = self.journal_db.get(i["name_id"])
        trackable_dict = {}
        for i in self.emps:
            if i["name"] in list(self.trackable):
                trackable_dict[i["name"]] = dict(
                    subs_id=i["subscriberID"], name_id=i["name_id"]
                )
        for name in self.trackable:
            # отслеживаемые сотрудники
            if trackable_dict[name]["subs_id"] != self.mts[name]:
                # если не совпадают subscriberID
                if trackable_dict[name]["subs_id"] is None:
                    # если нет текущего отслеживаемого устройства,
                    # добавляем запись
                    self.journal_usage_open(
                        self.mts.get(name), trackable_dict[name]["name_id"]
                    )
                else:
                    # в ином случае - закрываем текущую и открываем новую
                    self.journal_usage_close(
                        trackable_dict[name]["subs_id"],
                        trackable_dict[name]["name_id"],
                    )
                    self.journal_usage_open(
                        self.mts.get(name), trackable_dict[name]["name_id"]
                    )
        self.session.commit()

    def get_divisions_dict(self):
        """Словарь с учреждениями по name_id,
        показывает, в каких учреждениях был сотрудник"""
        sel = select(Statements.name_id, Statements.division).group_by(
            Statements.division, Statements.name_id
        )
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        res = (
            pd.DataFrame(res)
            .groupby("name_id")
            .agg(list)
            .to_dict()["division"]
        )
        return res

    def get_company_by_subscriberID(self, subscriberID) -> str | None:
        """Получить название компании по subscriberID"""
        for company, list_of_subs in self.company_dict.items():
            if subscriberID in list_of_subs:
                return company

    @property
    def removable(self):
        """Сотрудники на удаление, но с возможностью уточнить subscriberID
        и компанию
        [{name, subscriberID}]"""
        removable = set(self.mts.keys()) - set([i["name"] for i in self.emps])
        return [
            {
                "name": k,
                "subscriberID": v,
                "company": self.get_company_by_subscriberID(v),
            }
            for k, v in self.mts.items()
            if k in removable
        ]


class HrManager:
    """
    HrManager управляет сотрудниками:
      Отслеживает новых без подключения
      Предлагает отключить удаленных
      Контролирует Journal таблицу, закрывая периоды пользования
      Возвращает удаленных сотрудников, если по ним снова есть выходы.
      В целом, хотелось бы от такого объекта получать исчерпанную информацию:
        Есть ли проблемы с локациями?
        Давно ли были проставлены последние выходы?
        А что по соотношению выходов к невыходам?
      Это требования к Dashboard, а HrManager дополняет его информацией, но
      анализируя только statements, journal и инормацию с MTS.
    Мне нужна информация:
    От МТС - Имя, subsID, компания (все текущие подключенные)
    Из БД - employees (возможно, все), journal
    """

    def __init__(self) -> None:
        """
        Мне нужны данные:
            Сотрудники, которые не подключены к отслеживанию
            Сотрудники, которые подключены, но по ним не заполнены выходы
            Сотрудники, по которым последний выход был заполнен N дней назад
            Сотрудники, которых нужно удалить в связи с увольнением:
                Желательно с сортировкой по учреждениям, если такие данные есть

        Скрипт должен:
            Закрывать периоды journal, если subscriberID нет в актуальном MTS
            Добавлять запись в journal, если сотрудника подключили
            Закрывать старый период и открывать новый, если поменялись данные

        Сначала должна выполняться автоматическая часть скрипта, затем
        данные должны обновиться. И после этого можно предоставить suggest
        часть, которая содержит рекомендации к подключению/обновлению/удалению
        """
        self.session = Session(DB_ENGINE)
        self.connection = DB_ENGINE.connect()
        self.redis_connection = REDIS_CONN

    def todo_all(self) -> None:
        """
        Проделать все манипуляции с Journal и Employees, затем обновить df
        и обновить кеш hrManagerDf.
        """
        self._fill_df()
        # Проделать все автоматические операции с журналом и сотрудниками
        self._todo_del_quit_date()
        self._todo_set_quit_date()
        self._todo_close_journal_period()
        self._todo_open_journal_period()
        self._todo_open_close_journal_period()
        # commit на сессию
        self.session.commit()
        # нужно сделать commit на connection, чтобы результат запроса был свеж.
        self.connection.commit()
        # Перезаполнить df для актуализации данных
        self._fill_df()
        self.connection.close()
        # self.redis_connection.delete("hrManagerDf")
        # self.__send_to_redis("hrManagerDf", self.df)

    def __get_from_redis(self, key: str) -> Any:
        """ "Fetch from redis by key, decompress and unpickle"""
        fetched = self.redis_connection.get(key)
        if not fetched:
            return None
        return pickle.loads(bz2.decompress(fetched))

    def __send_to_redis(self, key: str, obj: Any) -> bool:
        """Compress, pickle and set as a key"""
        self.redis_connection.set(key, bz2.compress(pickle.dumps(obj)))
        self.redis_connection.expireat(
            key, int((dt.datetime.now() + dt.timedelta(minutes=3)).timestamp())
        )
        return True

    def _fill_df(self) -> None:
        # Все сотрудники (для изменений и отслеживания инфо по ним)
        self.employees = self._get_employees()

        # По каждому сотруднику все выходы за последний имеющийся день
        # вынести из last_day столбцы: последния дата выходов, есть ли в ней У
        self.last_day_statements = self._get_last_day_statements()
        # Список сотрудников, по которым не было проставлено ни одного выхода
        # вынести в отдельный столбец пометку: no_statements
        self.not_in_statements = self._get_not_existing_in_statements()

        # Список подписчиков из МТС с компаниями
        # столбец: mts_active
        # Чтобы у них был name_id для совмещения, сначала нужно собрать эти
        # данные из таблицы Employees (в какой момент времени?),
        # чтобы можно было совместить её со всеми остальными таблицами.
        # UPD: Пусть объединение будет по name сотрудника, а не name_id
        self.mts_subscribers = self._get_mts_subscribers()

        # Открытые текущие записи журнала
        # вынести в столбец: открыт ли период в journal
        self.journal_opened = self._get_journal_opened()

        self.divisions = self._get_divisions()

        # Идея: совместить всё в одну таблицу, и в ней проводить анализ
        # вынести из last_day столбцы: последния дата выходов, есть ли в ней У
        df = self.employees.copy()
        df = pd.merge(df, self.last_day_statements, on="name_id")
        df = pd.concat([df, self.not_in_statements])
        df = pd.merge(
            df,
            self.journal_opened,
            on=[
                "name_id",
                "name",
                "division",
                "hire_date",
                "quit_date",
                "no_tracking",
            ],
            how="outer",
        )
        df = pd.merge(df, self.mts_subscribers, on="name", how="outer")
        df["subscriberID_equal"] = df["subscriberID"] == df["subscriberID_mts"]
        df = df.fillna(
            value={
                "mts_active": False,
                "journal_opened": False,
                "no_statements": False,
            }
        )
        df = pd.merge(df, self.divisions, on="division", how="left")
        df["division_name"] = df["division_name_additional"]
        df = pd.merge(
            df,
            self.employees[["name_id", "phone"]],
            on=["name_id"],
            how="left",
        )
        df["phone"] = df["phone_y"]
        self.df = df

    def _todo_del_quit_date(self) -> None:
        # Удалить quit_date, когда последний выход не "У"
        # (при условии наличия выходов)
        del_quit_date = (pd.notna(self.df["quit_date"])) & (
            self.df["contains_fired_stmt"] == False
        )
        del_quit_date = self.df.loc[del_quit_date]
        name_ids = del_quit_date.name_id.to_list()
        upd = (
            update(Employees)
            .where(Employees.name_id.in_(name_ids))
            .values(quit_date=None)
        )
        self.session.execute(upd)

    def _todo_set_quit_date(self) -> None:
        # Установить quit_date, когда последний выход - это "У"
        # (при условии наличия выходов)
        set_quit_date = (pd.isna(self.df["quit_date"])) & (
            self.df["contains_fired_stmt"] == True
        )
        df = self.df.loc[set_quit_date]
        records = df.to_dict(orient="records")
        for record in records:
            upd = (
                update(Employees)
                .where(Employees.name_id == record["name_id"])
                .values(quit_date=record["last_stmt_date"])
            )
            self.session.execute(upd)

    def _todo_close_journal_period(self) -> None:
        # Если запись в журнале открыта, но в списке мтс отсутствует - значит
        # закрыть её (либо текущей датой, либо датой последнего выхода при
        # наличии выходов)
        close_journal_period = (self.df["journal_opened"] == True) & (
            self.df["mts_active"] == False
        )
        df = self.df.loc[close_journal_period]
        records = df.to_dict(orient="records")

        close_period_date = dt.date.today() - dt.timedelta(days=1)

        for record in records:
            upd = (
                update(Journal)
                .where(Journal.name_id == record["name_id"])
                .where(Journal.period_init == record["period_init"])
                .where(Journal.subscriberID == record["subscriberID"])
                .values(period_end=close_period_date)
            )
            self.session.execute(upd)

    def _todo_open_journal_period(self) -> None:
        # subscriberID для добавления в journal
        open_journal_period = (
            (self.df["mts_active"] == True)
            & (self.df["journal_opened"] == False)
            & (pd.isna(self.df["quit_date"]))
            & (pd.notna(self.df["name_id"]))
        )
        df = self.df.loc[open_journal_period]
        records = df.to_dict(orient="records")
        for record in records:
            ins = insert(Journal).values(
                name_id=record["name_id"],
                subscriberID=record["subscriberID_mts"],
                period_init=dt.date.today(),
            )
            self.session.execute(ins)

    def _todo_open_close_journal_period(self) -> None:
        # Это случаи, когда subscriberID открыт, но
        # не совпадает с актуальным в МТС.
        open_close_journal_period = (
            (self.df["mts_active"] == True)
            & (self.df["journal_opened"] == True)
            & (self.df["subscriberID_equal"] == False)
            & (pd.notna(self.df["name_id"]))
        )
        df = self.df.loc[open_close_journal_period]
        records = df.to_dict(orient="records")

        close_period_date = dt.date.today() - dt.timedelta(days=1)

        for record in records:
            upd = (
                update(Journal)
                .where(Journal.name_id == record["name_id"])
                .where(Journal.period_init == record["period_init"])
                .where(Journal.subscriberID == record["subscriberID"])
                .values(period_end=close_period_date)
            )
            ins = insert(Journal).values(
                name_id=record["name_id"],
                subscriberID=record["subscriberID_mts"],
                period_init=dt.date.today(),
            )
            self.session.execute(upd)
            self.session.execute(ins)

    def _get_employees(self) -> pd.DataFrame:
        sel = select(
            Employees.name_id,
            Employees.name,
            Employees.division,
            Employees.no_tracking,
            Employees.hire_date,
            Employees.quit_date,
            Employees.phone,
        )
        return pd.read_sql(sel, self.connection)

    def _get_divisions(self) -> pd.DataFrame:
        sel = select(
            Division.id.label("division"),
            Division.division.label("division_name_additional"),
        )
        return pd.read_sql(sel, self.connection)

    def _get_last_day_statements(self) -> pd.DataFrame:
        # ("select ta.name_id, employees_site.quit_date, ta.date, "
        #  "employees_site.name, statements_site.statement from "
        #  "(select name_id, max(date) as date from statements_site "
        #  "group by name_id) as ta join statements_site on "
        #  "ta.name_id = statements_site.name_id and ta.date = "
        #  "statements_site.date join employees_site on ta.name_id = "
        #  "employees_site.name_id order by employees_site.name;")
        subq = (
            select(
                Statements.name_id.label("name_id"),
                func.max(Statements.date).label("last_stmt_date"),
            )
            .group_by(Statements.name_id)
            .alias("subq")
        )

        sel_max_date = (
            select(
                subq.c.name_id,
                subq.c.last_stmt_date,
                Statements.statement,
                Employees.quit_date,
            )
            .join(
                Statements,
                and_(
                    (subq.c.name_id == Statements.name_id),
                    (subq.c.last_stmt_date == Statements.date),
                ),
            )
            .join(Employees, Employees.name_id == subq.c.name_id)
        )

        df = pd.read_sql(sel_max_date, self.connection)
        contains_fired_stmt = df.groupby(["name_id"]).apply(
            lambda x: "У" in list(x.statement)
        )
        df = df.set_index("name_id")
        df["contains_fired_stmt"] = contains_fired_stmt
        df = df.reset_index()
        df = df.drop_duplicates(subset="name_id")
        return df[["name_id", "last_stmt_date", "contains_fired_stmt"]]

    def _get_not_existing_in_statements(self) -> pd.DataFrame:
        # (
        #     "select division.division, name_id, name, phone, hire_date, "
        #     "quit_date from employees_site join division on "
        #     "employees_site.division = division.id where name_id not in "
        #     "(select distinct name_id from statements_site) and quit_date is "
        #     "null order by division;"
        # )
        # select division.division, name_id, name, phone, hire_date, quit_date from employees_site join division on employees_site.division = division.id where name_id not in (select distinct name_id from statements_site) and quit_date is null order by division;
        subsel = select(distinct(Statements.name_id))
        sel = (
            select(
                Division.division.label("division_name"),
                Division.id.label("division"),
                Employees.name_id,
                Employees.name,
                Employees.hire_date,
                Employees.quit_date,
                Employees.no_tracking,
            )
            .where(Employees.name_id.not_in(subsel))
            .where(Employees.quit_date == None)
            .join(Division, Employees.division == Division.id)
        )
        df = pd.read_sql(sel, self.connection)
        df["no_statements"] = True
        return df

    def _get_journal_opened(self) -> pd.DataFrame:
        sel = (
            select(
                Journal.id,
                Journal.name_id,
                Journal.subscriberID,
                Journal.period_init,
                Journal.period_end,
                Employees.name,
                Employees.division,
                Employees.hire_date,
                Employees.quit_date,
                Employees.no_tracking,
            )
            .where(Journal.period_end == None)
            .join(Employees, Journal.name_id == Employees.name_id)
        )
        df = pd.read_sql(sel, self.connection)
        df["journal_opened"] = True
        return df[
            [
                "name_id",
                "subscriberID",
                "period_init",
                "period_end",
                "journal_opened",
                "name",
                "division",
                "quit_date",
                "hire_date",
                "no_tracking",
            ]
        ]

    def _get_mts_subscribers(self) -> pd.DataFrame:
        subscribers = get_subscribers()
        df = pd.DataFrame(subscribers)
        df["mts_active"] = True
        df = df.rename(columns={"subscriberID": "subscriberID_mts"})
        return df[["company", "subscriberID_mts", "name", "mts_active"]]

    @property
    def suggest_abandoned(self) -> pd.DataFrame:
        # проставлять увольнение по дате посл. выхода в statements
        # Таблица отображает список сотрудников, по которым давно нет выходов
        # Это таблица с предложением, она должна включать дату последнего
        # выхода, отображает, подключен ли сотрудник к МТС.
        # Кнопка "уволить" проставляет дату увольнения в соответствии с датой
        # последнего выхода
        DATE_21_DAYS_AGO = dt.date.today() - dt.timedelta(days=21)
        to_set_abandoned_quit = (
            (pd.notna(self.df["name_id"]))
            & (pd.isna(self.df["quit_date"]))
            & (self.df["contains_fired_stmt"] == False)
            & (self.df["last_stmt_date"] <= DATE_21_DAYS_AGO)
        )
        df = self.df.loc[to_set_abandoned_quit]
        df = df[
            [
                "name_id",
                "name",
                "division",
                "division_name",
                "hire_date",
                "last_stmt_date",
                "mts_active",
            ]
        ]
        df = df.sort_values(["division_name", "last_stmt_date"])
        return df

    @property
    def suggest_del_from_mts(self) -> pd.DataFrame:
        # уже уволенные сотрудники, но которые подключены к МТС. Кнопка будет
        # удалять их из МТС отслеживания.
        to_del_from_mts = (
            (pd.notna(self.df["quit_date"]))
            & (self.df["mts_active"] == True)
            & (self.df["quit_date"] <= dt.date.today())
        )
        df = self.df.loc[to_del_from_mts]
        df.loc[:, ["subscriberID"]] = df["subscriberID_mts"]
        df = df[
            [
                "name_id",
                "name",
                "division",
                "division_name",
                "hire_date",
                "quit_date",
                "company",
                "last_stmt_date",
                "subscriberID",
            ]
        ]
        df = df.sort_values(["company", "division_name", "last_stmt_date"])
        return df

    @property
    def suggest_no_statements(self) -> pd.DataFrame:
        # Это сотрудники, которые были подключены, но выходы так и не
        # были проставлены. Возможно, чтобы не проставлять "У" где попало,
        # достаточно просто удалить их из МТС и списка сотрудников сразу.
        # Или напомнить куратору, что сотрудник так и не проставлен в таблице.
        # Обязательно указывать кол-во дней с даты подключения, чтобы оценить
        # степень заброшенности сотрудника.
        no_statements = (self.df["mts_active"] == True) & (
            self.df["no_statements"] == True
        )
        df = self.df.loc[no_statements]
        df = df[
            [
                "name_id",
                "name",
                "division",
                "division_name",
                "hire_date",
                "period_init",
            ]
        ]
        df = df.sort_values(["division_name", "period_init"])
        return df

    @property
    def suggest_mts_only(self) -> pd.DataFrame:
        mts_only = pd.isna(self.df["name_id"])
        df = self.df.loc[mts_only]
        df.loc[:, ["subscriberID"]] = df["subscriberID_mts"]
        df = df[["name", "company", "subscriberID"]]
        df = df.sort_values(["company", "name"])
        return df

    @property
    def suggest_to_connect(self) -> pd.DataFrame:
        # этих нужно подключить
        # Кандидаты на подключение. Хорошо, по возможности, отображать дату
        # последнего проставленного выхода.
        to_connect = (
            (self.df["mts_active"] == False)
            & (self.df["no_tracking"] == False)
            & (pd.isna(self.df["quit_date"]))
        )
        df = self.df.loc[to_connect]
        df = df[
            [
                "name_id",
                "name",
                "division",
                "division_name",
                "hire_date",
                "no_statements",
                "phone",
                "last_stmt_date",
            ]
        ]
        df = df.sort_values(["division_name", "hire_date"])
        return df

    def get_suggests_dict(self) -> dict:
        # self.df = self.__get_from_redis('hrManagerDf')
        # if self.df is None:
        # self.todo_all()
        self.todo_all()
        abandoned = self.suggest_abandoned
        abandoned.loc[:, ["hire_date", "last_stmt_date"]] = abandoned.loc[
            :, ["hire_date", "last_stmt_date"]
        ].astype(str)
        abandoned = abandoned.to_dict(orient="records")

        del_from_mts = self.suggest_del_from_mts
        del_from_mts.loc[:, ["hire_date", "quit_date", "last_stmt_date"]] = (
            del_from_mts.loc[
                :, ["hire_date", "quit_date", "last_stmt_date"]
            ].astype(str)
        )
        del_from_mts = del_from_mts.to_dict(orient="records")

        no_statements = self.suggest_no_statements
        no_statements.loc[:, ["hire_date", "period_init"]] = no_statements.loc[
            :, ["hire_date", "period_init"]
        ].astype(str)
        no_statements = no_statements.to_dict(orient="records")

        to_connect = self.suggest_to_connect
        to_connect.loc[:, ["hire_date", "last_stmt_date"]] = to_connect.loc[
            :, ["hire_date", "last_stmt_date"]
        ].astype(str)

        to_connect["last_stmt_date"] = to_connect["last_stmt_date"].replace(
            "nan", "нет выходов"
        )

        to_connect = to_connect.to_dict(orient="records")

        mts_only = self.suggest_mts_only.to_dict(orient="records")

        suggests_dict = {}
        suggests_dict["abandoned"] = abandoned
        suggests_dict["del_from_mts"] = del_from_mts
        suggests_dict["no_statements"] = no_statements
        suggests_dict["to_connect"] = to_connect
        suggests_dict["mts_only"] = mts_only
        return suggests_dict


if __name__ == "__main__":
    j = HrManager()
    j.todo_all()
    j.get_suggests_dict()
    pass
