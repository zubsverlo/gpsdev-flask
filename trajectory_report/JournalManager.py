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
        self._todo_close_journal_period_mts()
        self._todo_open_journal_period()
        self._todo_change_journal_period_from_owntracks_to_mts()
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
                "owntracks": False,
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
        # self.session.execute(upd)

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
            # self.session.execute(upd)

    def _todo_close_journal_period_mts(self) -> None:
        # Если запись в журнале открыта, но в списке мтс отсутствует - значит
        # закрыть её (либо текущей датой, либо датой последнего выхода при
        # наличии выходов)
        close_journal_period = (
            (self.df["journal_opened"] == True)
            & (self.df["mts_active"] == False)
            & (self.df["owntracks"] == False)
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
            # self.session.execute(upd)

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
            # self.session.execute(ins)

    def _todo_change_journal_period_from_owntracks_to_mts(self) -> None:
        # subscriberID для добавления в journal вместо записи owntracks
        change_journal_period = (
            (self.df["mts_active"] == True)
            & (self.df["journal_opened"] == True)
            & (self.df["owntracks"] == True)
            & (pd.isna(self.df["quit_date"]))
            & (pd.notna(self.df["name_id"]))
        )
        df = self.df.loc[change_journal_period]
        records = df.to_dict(orient="records")
        close_period_date = dt.date.today() - dt.timedelta(days=1)

        for record in records:
            upd = (
                update(Journal)
                .where(Journal.name_id == record["name_id"])
                .where(Journal.period_init == record["period_init"])
                .where(Journal.owntracks == True)
                .where(Journal.period_end == None)
                .values(period_end=close_period_date)
            )
            # self.session.execute(upd)

            ins = insert(Journal).values(
                name_id=record["name_id"],
                subscriberID=record["subscriberID_mts"],
                period_init=dt.date.today(),
            )
            # self.session.execute(ins)

    def _todo_resume_journal_period_owntracks(self) -> None:
        resume_journal_period = (
            (self.df["journal_opened"] == False)
            & (self.df["mts_active"] == False)
            & (self.df["owntracks"] == True)
            & (pd.isna(self.df["quit_date"]))
            & (pd.notna(self.df["period_end"]))
            & (pd.notna(self.df["name_id"]))
        )
        df = self.df.loc[resume_journal_period]
        records = df.to_dict(orient="records")
        close_period_date = dt.date.today() - dt.timedelta(days=1)

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
            # self.session.execute(upd)
            # self.session.execute(ins)

    def _todo_close_journal_period_owntracks(self) -> None:
        # Если запись в журнале открыта, но проставлен quit_date, то закрыть
        # период (относится к owntracks)
        close_journal_period = (
            (self.df["journal_opened"] == True)
            & (self.df["mts_active"] == False)
            & (self.df["owntracks"] == True)
            & (self.df["quit_date"] <= dt.date.today())
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
            # self.session.execute(upd)

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
                Journal.owntracks,
                Employees.name,
                Employees.division,
                Employees.hire_date,
                Employees.quit_date,
                Employees.no_tracking,
            ).join(Employees, Journal.name_id == Employees.name_id)
            # .where(Journal.period_end == None)
        )
        df = pd.read_sql(sel, self.connection)
        # нужно поменять запрос на полный журнал, а потом отфильтровать все
        # записи, чтобы осталась только последняя открытая запись
        # (max period_init). Тогда не будет задвоений,
        # а journal_opened оставить только для реально открытых записей

        df = df.sort_values(["name_id", "period_init"]).drop_duplicates(
            ["name_id"], keep="last"
        )
        df["journal_opened"] = pd.isna(df["period_end"])
        return df[
            [
                "name_id",
                "subscriberID",
                "period_init",
                "period_end",
                "journal_opened",
                "owntracks",
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
                "owntracks",
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
        no_statements = (
            (self.df["mts_active"] == True) | (self.df["owntracks"] == True)
        ) & (self.df["no_statements"] == True)
        df = self.df.loc[no_statements]
        df = df[
            [
                "name_id",
                "name",
                "division",
                "division_name",
                "hire_date",
                "period_init",
                "mts_active",
                "owntracks",
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
            & (self.df["owntracks"] == False)
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
    j = HrManager()
    j = j.get_suggests_dict()
    pass
