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
from trajectory_report.journal.utils import get_analysis_table, analyse


class JournalManager:
    def __init__(self):
        self.connection = DB_ENGINE.connect()
        session = Session(DB_ENGINE)
        analyse(get_analysis_table(self.connection), session)
        self.connection.commit()
        self.df = get_analysis_table(self.connection)
        session.close()
        self.connection.close()

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
    j = JournalManager()
