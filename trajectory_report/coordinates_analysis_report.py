import datetime as dt
from sqlalchemy import select, Select
from trajectory_report.models import (
    Employees,
    Division,
    Statements,
    LocationAnalysis,
)
from trajectory_report.database import DB_ENGINE
import pandas as pd
from trajectory_report.exceptions import ReportException


# filter by statements only those who worked when report fetched
# and add periods to analyze (1 day, 2 days, 7 days etc.)
def locs_sel(
        date_from: dt.date, date_to: dt.date
) -> Select:
    sel: Select = select(
        LocationAnalysis.name_id,
        LocationAnalysis.date,
        LocationAnalysis.start,
        LocationAnalysis.end,
        LocationAnalysis.count,
        LocationAnalysis.seconds,
        LocationAnalysis.owntracks,
    )\
        .where(LocationAnalysis.date >= date_from)\
        .where(LocationAnalysis.date <= date_to)
    return sel


def stmts_sel(date_from: dt.date, date_to: dt.date) -> Select:
    sel: Select = select(
        Statements.name_id,
        Statements.object_id,
        Statements.date
    )\
        .where(Statements.date >= date_from)\
        .where(Statements.date <= date_to)\
        .where(Statements.object_id != 1)
    return sel


def employees_sel(name_ids: list) -> Select:
    sel: Select = select(
        Employees.name_id,
        Employees.name,
        Employees.phone,
        Division.division,
    )\
        .join(Division)\
        .where(Employees.name_id.in_(name_ids))
    return sel


def get_report(date_from: dt.date | str, date_to: dt.date | str):
    date_from = dt.date.fromisoformat(str(date_from))
    date_to = dt.date.fromisoformat(str(date_to))
    with DB_ENGINE.connect() as conn:
        analysis = pd.read_sql(locs_sel(date_from, date_to), conn)
        stmts = pd.read_sql(stmts_sel(date_from, date_to), conn)
        name_ids = stmts.name_id.unique().tolist()
        employees = pd.read_sql(employees_sel(name_ids), conn)
    if analysis.empty:
        raise ReportException("Нет данных для анализа за указанный период")
    stmts = stmts.drop_duplicates(['name_id', 'date'])[['name_id', 'date']]
    stmts = pd.merge(
        stmts, analysis, on=['name_id', 'date'], how='inner'
    )
    stmts = pd.merge(stmts, employees, on='name_id', how='left')
    stmts['seconds'] = stmts.seconds.apply(
        lambda x: str(dt.timedelta(seconds=x))
    )
    stmts['start'] = stmts['start'].apply(lambda x: x.strftime("%H:%M:%S"))
    stmts['end'] = stmts['end'].apply(lambda x: x.strftime("%H:%M:%S"))
    return stmts.to_dict(orient='records')


if __name__ == "__main__":
    get_report("2024-05-20", "2024-05-20")
