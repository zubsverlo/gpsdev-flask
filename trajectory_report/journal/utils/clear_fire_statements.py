import datetime as dt

import pandas as pd
from sqlalchemy import select, text
from sqlalchemy.orm import Session

from gpsdev_flask import main_logger
from trajectory_report.database import DB_ENGINE
from trajectory_report.models import Statements

pd.set_option("display.max_rows", None)


def shift_statements(x):
    x["date2"] = x["date"].shift(1)
    return x


def clear_statements():
    sel = (
        select(Statements.name_id, Statements.date, Statements.statement)
        .where(Statements.object_id == 1)
        .where(Statements.statement == "У")
    )
    df = (
        pd.read_sql(sel, DB_ENGINE.connect())
        .sort_values(["name_id", "date"])
        .drop_duplicates(["name_id", "date", "statement"])
    )
    df = df.groupby([df["name_id"]]).apply(shift_statements)
    df["removable"] = (df["date"] - df["date2"]) == dt.timedelta(days=1)
    df = df[df["removable"] == False]
    df["date"] = df.apply(
        lambda x: max(x["date"], x["date2"]) if x["date2"] else (x["date"]),
        axis=1,
    )
    df = (
        df
        .sort_values(["name_id", "date"])
        .drop_duplicates(["name_id"], keep="last")
        .loc[:, ['name_id', 'date']]
    )
    df = df[df['date'] > (dt.date.today() - dt.timedelta(days=60))]
    main_logger.info(df.sort_values('date'))
    connection = DB_ENGINE.connect()
    session = Session(connection)
    for row in df.itertuples():
        stmt = text(f'delete from statements_site where name_id = "{row.name_id}" and date > "{row.date}" and statement = "У"')
        session.execute(stmt)
    session.commit()
    session.close()
    connection.close()
    pass


if __name__ == "__main__":
    clear_statements()
