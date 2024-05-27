import datetime as dt
from sqlalchemy import select, Select
from sqlalchemy.sql.expression import func
from trajectory_report.models import (
    Journal,
    Coordinates,
    OwnTracksLocation,
    LocationAnalysis,
)
from trajectory_report.database import DB_ENGINE
import pandas as pd
from trajectory_report.config import LONG_PERIOD


YESTERDAY = dt.date.today()-dt.timedelta(days=1)


def get_dates_range() -> list[dt.date]:
    """Получить список дат, по которым нужно произвести кластеры.
    Если кластеров нет вообще - выдаст список из дат за последние 2 месяца."""
    with DB_ENGINE.connect() as conn:
        # Дата последних произведенных кластеров
        date = conn.execute(func.max(LocationAnalysis.date)).scalar()
        if not date:
            # Если кластеры ещё не производились - задать день 2 месяца назад
            date = dt.date.today() - dt.timedelta(days=60)
        # Список дат, по которым нужно произвести кластеры координат.
        return [
            date + dt.timedelta(days=i)
            for i in range(1, (dt.date.today() - date).days)
        ]


def journal_selection_select() -> Select:
    """Получить записи journal с привязками subscriberID, name_id к датам"""
    sel: Select = select(
        Journal.name_id,
        Journal.subscriberID,
        Journal.period_init,
        Journal.period_end,
        Journal.owntracks,
    )
    return sel


def locations_mts_select(date: dt.date) -> Select:
    """get current locations by subscriber_ids"""
    sel: Select = (
        select(
            Coordinates.subscriberID,
            Coordinates.locationDate.label('created_at'),
        )
        .where(Coordinates.requestDate > date)
        .where(Coordinates.requestDate < date+dt.timedelta(days=1))
        .where(Coordinates.locationDate != None)
    )
    return sel


def locations_owntracks_select(date) -> Select:
    """get current locations by subscriber_ids"""
    sel: Select = (
        select(
            OwnTracksLocation.employee_id.label("name_id"),
            OwnTracksLocation.created_at,
        )
        .where(OwnTracksLocation.created_at > date)
        .where(OwnTracksLocation.created_at < date+dt.timedelta(days=1))
    )
    return sel


def get_coordinates(date):
    with DB_ENGINE.connect() as conn:
        journal = pd.read_sql(journal_selection_select(), conn)
        locations_mts = pd.read_sql(locations_mts_select(date), conn)
        locations_owntracks = pd.read_sql(
            locations_owntracks_select(date), conn
        )
    journal.loc[pd.isna(journal['period_end']), 'period_end'] = dt.date.today()
    # filter journal to get current employee's subscriberID
    journal = journal.loc[
        (journal['period_init'] <= date) &
        (journal['period_end'] >= date)
    ]
    locations_mts = pd.merge(journal, locations_mts, on='subscriberID')\
        .rename(columns={'locationDate': 'created_at'})\
        .loc[:, ['name_id', 'created_at', 'owntracks']]
    locs = pd.concat([locations_mts, locations_owntracks]).fillna(False)
    locs = locs.sort_values(['name_id', 'created_at'])

    locs['shifted'] = locs.groupby('name_id')['created_at'].shift(-1)
    locs["difference"] = locs.shifted - locs.created_at
    locs["long_period"] = locs.difference > dt.timedelta(minutes=LONG_PERIOD)
    locs_min = locs.groupby('name_id').created_at.min()
    locs_max = locs.groupby('name_id').created_at.max()

    locs = locs[locs["long_period"]]
    locs = locs\
        .groupby('name_id')\
        .agg({'difference': ['count', 'mean'],
              'owntracks': 'first'})\
        .pipe(lambda x: x.set_axis(x.columns.map('_'.join), axis=1))
    locs['start'] = locs_min
    locs['end'] = locs_max
    locs = locs.reset_index()
    locs['difference_mean'] = locs.difference_mean.apply(
        lambda x: int(x.total_seconds())
    )
    locs['date'] = date
    locs = locs.rename(
        columns={
            'difference_count': 'count',
            'difference_mean': 'seconds',
            'owntracks_first': 'owntracks',
        }
    )
    # add records to the db
    locs.to_sql(
        'location_analysis', DB_ENGINE, if_exists='append', index=False
    )


def analyze_coordinates():
    # get dates since the last analysis and make analysis for every of them
    dates = get_dates_range()
    for date in dates:
        get_coordinates(date)


if __name__ == "__main__":
    analyze_coordinates()