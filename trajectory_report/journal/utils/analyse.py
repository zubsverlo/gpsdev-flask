import pandas as pd
import datetime as dt
from sqlalchemy import update, insert
from sqlalchemy.orm import Session
from trajectory_report.models import Employees, Journal
import logging

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def analyse(df: pd.DataFrame, session: Session) -> pd.DataFrame:
    delete_quit_date(df, session)
    set_quit_date(df, session)
    close_journal_mts(df, session)
    open_journal_mts(df, session)
    change_journal_mts(df, session)
    change_journal_from_owntracks_to_mts(df, session)
    close_journal_owntracks(df, session)
    resume_journal_owntracks(df, session)
    session.commit()


def delete_quit_date(df, session) -> None:
    """удалить quit_date у сотрудника, если последний
    день выходов не содержит 'У'"""
    del_quit_date_mask = (pd.notna(df["quit_date"])) & (
        df["contains_fired_stmt"] == False
    )
    del_quit_date = df.loc[del_quit_date_mask]
    logger.info(f"delete_quit_date len: {len(df.loc[del_quit_date_mask])}")
    upd = (
        update(Employees)
        .where(Employees.name_id.in_(list(del_quit_date.name_id)))
        .values(quit_date=None)
    )
    session.execute(upd)
    session.commit()


def set_quit_date(df, session) -> None:
    """проставить quit_date, если последний день
    выходов сотрудника содержит 'У'"""
    set_quit_date_mask = (pd.isna(df["quit_date"])) & (
        df["contains_fired_stmt"] == True
    )
    logger.info(f"set_quit_date len: {len(df.loc[set_quit_date_mask])}")
    for row in df.loc[set_quit_date_mask].itertuples():
        upd = (
            update(Employees)
            .where(Employees.name_id == row.name_id)
            .values(quit_date=row.last_stmt_date)
        )
        session.execute(upd)
    session.commit()


def close_journal_mts(df, session) -> None:
    """Если у сотрудника открыта запись в журнале, при этом запись
    не относится к owntracks, но сотрудник отсутствует в списке МТС - значит
    нужно закрыть запись вчерашней датой.
    """
    close_journal_mask = (
        (df["journal_opened"] == True)
        & (df["mts_active"] == False)
        & (df["owntracks"] == False)
    )
    close_date = dt.date.today() - dt.timedelta(days=1)
    logger.info(f"close_journal_mts len: {len(df.loc[close_journal_mask])}")
    for row in df.loc[close_journal_mask].itertuples():
        upd = (
            update(Journal)
            .where(Journal.name_id == row.name_id)
            .where(Journal.period_init == row.period_init)
            .where(Journal.subscriberID == row.subscriberID)
            .values(period_end=close_date)
        )
        session.execute(upd)
    session.commit()


def open_journal_mts(df, session) -> None:
    """Если сотрудник есть в базе данных (name_id существует),
    сотрудник не уволен (отсутств. quit_date), запись журнала не открыта и
    при этом он присутствует в списке сотрудников МТС - добавить запись журнала
    """
    open_journal_mask = (
        (df["mts_active"] == True)
        & (df["journal_opened"] == False)
        & (pd.isna(df["quit_date"]))
        & (pd.notna(df["name_id"]))
    )
    logger.info(f"open_journal_mts len: {len(df.loc[open_journal_mask])}")
    for record in df.loc[open_journal_mask].itertuples():
        ins = insert(Journal).values(
            name_id=record.name_id,
            subscriberID=record.subscriberID_mts,
            period_init=dt.date.today(),
        )
        session.execute(ins)
    session.commit()


def change_journal_mts(df, session) -> None:
    """
    Случаи, когда journal открыт по mts, но subscriberID не совпадает.
    Тогда нужно закрыть устаревший subscriberID и открыть запись с новым.
    Также нужно убедиться, что эта запись не owntracks.
    """
    open_close_journal_mask = (
        (df["mts_active"] == True)
        & (df["journal_opened"] == True)
        & (df["subscriberID_equal"] == False)
        & (pd.notna(df["name_id"]))
        & (df["owntracks"] == False)
    )
    close_date = dt.date.today() - dt.timedelta(days=1)
    logger.info(
        f"change_journal_mts len: {len(df.loc[open_close_journal_mask])}"
    )
    for row in df.loc[open_close_journal_mask].itertuples():
        upd = (
            update(Journal)
            .where(Journal.name_id == row.name_id)
            .where(Journal.period_init == row.period_init)
            .where(Journal.subscriberID == row.subscriberID)
            .values(period_end=close_date)
        )
        ins = insert(Journal).values(
            name_id=row.name_id,
            subscriberID=row.subscriberID_mts,
            period_init=dt.date.today(),
        )
        session.execute(upd)
        session.execute(ins)
    session.commit()


def change_journal_from_owntracks_to_mts(df, session) -> None:
    """
    Если отслеживание было по owntracks, но затем сотрудник появился в списке
    mts, то приоритет отдается mts. Значит, нужно закрыть запись с owntracks
    и открыть её для mts.
    """
    change_journal_mask = (
        (df["mts_active"] == True)
        & (df["journal_opened"] == True)
        & (df["owntracks"] == True)
        & (pd.isna(df["quit_date"]))
        & (pd.notna(df["name_id"]))
    )
    close_period_date = dt.date.today() - dt.timedelta(days=1)
    logger.info(
        (
            f"change_journal_from_owntracks_to_mts len: "
            f"{len(df.loc[change_journal_mask])}"
        )
    )
    for row in df.loc[change_journal_mask].itertuples():
        upd = (
            update(Journal)
            .where(Journal.name_id == row.name_id)
            .where(Journal.period_init == row.period_init)
            .where(Journal.owntracks == True)
            .where(Journal.period_end == None)
            .values(period_end=close_period_date)
        )

        ins = insert(Journal).values(
            name_id=row.name_id,
            subscriberID=row.subscriberID_mts,
            period_init=dt.date.today(),
        )

        session.execute(upd)
        session.execute(ins)
    session.commit()


def close_journal_owntracks(df, session) -> None:
    """
    Если сотруднику проставили увольнение, то нужно закрыть запись журнала.
    То же самое, что с mts, только относится к owntracks.
    """
    close_journal_mask = (
        (df["journal_opened"] == True)
        & (df["mts_active"] == False)
        & (df["owntracks"] == True)
        & (df["quit_date"] <= dt.date.today())
    )
    close_date = dt.date.today() - dt.timedelta(days=1)
    logger.info(
        f"close_journal_owntracks len: {len(df.loc[close_journal_mask])}"
    )
    for row in df.loc[close_journal_mask].itertuples():
        upd = (
            update(Journal)
            .where(Journal.name_id == row.name_id)
            .where(Journal.period_init == row.period_init)
            .where(Journal.subscriberID == None)
            .where(Journal.period_end == None)
            .where(Journal.owntracks == True)
            .values(period_end=close_date)
        )
        session.execute(upd)
    session.commit()


def resume_journal_owntracks(df, session) -> None:
    """
    Если сотрудника сначала уволили, а потом восстановили, но отслеживался он
    при помощи owntracks, то нужно восстановить последнюю запись журнала с
    owntracks (если последней была именно такая).
    """
    resume_journal_mask = (
        (df["journal_opened"] == False)
        & (df["mts_active"] == False)
        & (df["owntracks"] == True)
        & (pd.isna(df["quit_date"]))
        & (pd.notna(df["period_end"]))
    )
    logger.info(
        f"resume_journal_owntracks len: {len(df.loc[resume_journal_mask])}"
    )
    for row in df.loc[resume_journal_mask].itertuples():
        upd = (
            update(Journal)
            .where(Journal.name_id == row.name_id)
            .where(Journal.period_init == row.period_init)
            .where(Journal.subscriberID == None)
            .where(Journal.period_end == row.period_end)
            .where(Journal.owntracks == True)
            .values(period_end=None)
        )
        session.execute(upd)
    session.commit()
