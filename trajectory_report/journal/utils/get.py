from trajectory_report.api.mts import get_subscribers
from trajectory_report.models import Employees, Statements, Journal, Division
from sqlalchemy import select, and_, Connection
import pandas as pd
from sqlalchemy import func, distinct


def get_analysis_table(conn: Connection) -> pd.DataFrame:

    employees = get_employees(conn)
    last_day_statements = get_last_day_statements(conn)
    not_in_statements = get_not_existing_in_statements(conn)
    journal_opened = get_journal_opened(conn)
    divisions = get_divisions(conn)
    mts_subscribers = get_mts_subscribers()

    df = employees.copy()
    df = pd.merge(df, last_day_statements, on="name_id")
    df = pd.concat([df, not_in_statements])
    df = pd.merge(
        df,
        journal_opened,
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
    df = pd.merge(df, mts_subscribers, on="name", how="outer")
    df["subscriberID_equal"] = df["subscriberID"] == df["subscriberID_mts"]
    df = df.fillna(
        value={
            "mts_active": False,
            "journal_opened": False,
            "no_statements": False,
            "owntracks": False,
        }
    )
    df = pd.merge(df, divisions, on="division", how="left")
    df["division_name"] = df["division_name_additional"]
    df = pd.merge(
        df,
        employees[["name_id", "phone"]],
        on=["name_id"],
        how="left",
    )
    df["phone"] = df["phone_y"]
    return df


def get_employees(conn: Connection) -> pd.DataFrame:
    sel = select(
        Employees.name_id,
        Employees.name,
        Employees.division,
        Employees.no_tracking,
        Employees.hire_date,
        Employees.quit_date,
        Employees.phone,
    )
    return pd.read_sql(sel, conn)


def get_last_day_statements(conn: Connection) -> pd.DataFrame:
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

    df = pd.read_sql(sel_max_date, conn)
    contains_fired_stmt = df.groupby(["name_id"]).apply(
        lambda x: "У" in list(x.statement)
    )
    df = df.set_index("name_id")
    df["contains_fired_stmt"] = contains_fired_stmt
    df = df.reset_index()
    df = df.drop_duplicates(subset="name_id")
    return df[["name_id", "last_stmt_date", "contains_fired_stmt"]]


def get_not_existing_in_statements(conn: Connection) -> pd.DataFrame:
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
    df = pd.read_sql(sel, conn)
    df["no_statements"] = True
    return df


def get_mts_subscribers() -> pd.DataFrame:
    subscribers = get_subscribers()
    df = pd.DataFrame(subscribers)
    df["mts_active"] = True
    df = df.rename(columns={"subscriberID": "subscriberID_mts"})
    return df[["company", "subscriberID_mts", "name", "mts_active"]]


def get_journal_opened(conn: Connection) -> pd.DataFrame:
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
    df = pd.read_sql(sel, conn)
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


def get_divisions(conn: Connection) -> pd.DataFrame:
    sel = select(
        Division.id.label("division"),
        Division.division.label("division_name_additional"),
    )
    return pd.read_sql(sel, conn)
