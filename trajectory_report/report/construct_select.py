# (все функции для запроса таблиц из БД для формирования отчета)
import datetime as dt
from typing import Optional, List, Union

from sqlalchemy import select, Select, func
from trajectory_report.models import (
    Statements,
    Employees,
    Division,
    ObjectsSite,
    Journal,
    Serves,
    Coordinates,
    Clusters,
    Comment,
    Frequency,
)


def statements(
    date_from: dt.date,
    date_to: dt.date,
    division: Optional[Union[int, str]] = None,
    name_ids: Optional[List[int]] = None,
    object_ids: Optional[List[int]] = None,
    objects_with_address: bool = False,
) -> Select:
    """Получить записи с заявленными выходами"""
    if objects_with_address:
        sel = select(
            Statements.name_id,
            Employees.name,
            Statements.object_id,
            ObjectsSite.name.label("object"),
            ObjectsSite.longitude,
            ObjectsSite.latitude,
            ObjectsSite.address,
            Statements.date,
            Statements.statement,
        )
    else:
        sel = select(
            Statements.name_id,
            Employees.name,
            Statements.object_id,
            ObjectsSite.name.label("object"),
            ObjectsSite.longitude,
            ObjectsSite.latitude,
            Statements.date,
            Statements.statement,
        )
    sel = (
        sel.join(Employees)
        .join(ObjectsSite)
        .where(Statements.date >= date_from)
        .where(Statements.date <= date_to)
        .select_from(Statements)
    )
    if isinstance(division, int):
        sel = sel.where(Statements.division == division)
    if isinstance(division, str):
        sel = sel.join(Division, Statements.division == Division.id)
        sel = sel.where(Division.division == division)
    if name_ids:
        sel = sel.where(Statements.name_id.in_(name_ids))
    if object_ids:
        sel = sel.where(Statements.object_id.in_(object_ids))
    return sel


def employees(**kwargs) -> Select:
    """Все сотрудники"""
    sel: Select = select(Employees.name_id, Employees.name)
    return sel


def objects(**kwargs) -> Select:
    """Все объекты (подопечные)"""
    sel: Select = select(
        ObjectsSite.object_id,
        ObjectsSite.name.label("object"),
        ObjectsSite.latitude,
        ObjectsSite.longitude,
    )
    return sel


def divisions(**kwargs) -> Select:
    """Все объекты (подопечные)"""
    sel: Select = select(
        Division.id.label("division"), Division.division.label("division_name")
    )
    return sel


def statements_only(
    date_from: dt.date, date_to: Optional[dt.date] = None, **kwargs
) -> Select:
    """Получить все записи с заявленными выходами"""
    sel = select(
        Statements.name_id,
        Statements.object_id,
        Statements.date,
        Statements.statement,
        Statements.division,
    ).where(Statements.date >= date_from)
    if date_to:
        sel = sel.where(Statements.date <= date_to)
    return sel


def employee_schedules(
    name_ids: Optional[List[int]] = None, **kwargs
) -> Select:
    """Расписание сотрудников"""
    sel: Select = select(Employees.name_id, Employees.schedule)
    if name_ids:
        sel = sel.where(Employees.name_id.in_(name_ids))
    return sel


def journal(name_ids: Optional[List[int]] = None, **kwargs) -> Select:
    """Получить записи journal с привязками subscriberID, name_id к датам"""
    sel: Select = select(
        Journal.name_id,
        Journal.subscriberID,
        Journal.period_init,
        Journal.period_end,
    )
    if name_ids:
        sel = sel.where(Journal.name_id.in_(name_ids))
    return sel


def serves(
    date_from: dt.date,
    date_to: Optional[dt.date] = None,
    name_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    """Получить служебные записки из БД"""
    sel: Select = select(
        Serves.name_id,
        Serves.object_id,
        Serves.date,
        Serves.approval,
    ).where(Serves.date >= date_from)

    if date_to:
        sel = sel.where(Serves.date <= date_to)
    if name_ids:
        sel = sel.where(Serves.name_id.in_(name_ids))
    return sel


def current_locations(
    subscriber_ids: Optional[List[int]] = None, **kwargs
) -> Select:
    """get current locations by subscriber_ids"""
    sel: Select = (
        select(
            Coordinates.subscriberID,
            Coordinates.locationDate,
            Coordinates.longitude,
            Coordinates.latitude,
        )
        .where(Coordinates.requestDate > dt.date.today())
        .where(Coordinates.locationDate != None)
    )
    if subscriber_ids:
        sel = sel.where(Coordinates.subscriberID.in_(subscriber_ids))
    return sel


def clusters(
    date_from: dt.date,
    date_to: Optional[dt.date] = None,
    subscriber_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    """Получить кластеры из БД"""
    sel: Select = select(
        Clusters.subscriberID,
        Clusters.date,
        Clusters.datetime,
        Clusters.longitude,
        Clusters.latitude,
        Clusters.leaving_datetime,
        Clusters.cluster,
    ).where(Clusters.date >= date_from)

    if date_to:
        sel = sel.where(Clusters.date < date_to + dt.timedelta(days=1))
    if subscriber_ids:
        sel = sel.where(Clusters.subscriberID.in_(subscriber_ids))
    return sel


def statements_one_emp(
    date: dt.date, name_id: int, division: Union[int, str]
) -> Select:
    sel = (
        select(
            Statements.name_id,
            Employees.name,
            Statements.object_id,
            ObjectsSite.name.label("object"),
            ObjectsSite.longitude,
            ObjectsSite.latitude,
            ObjectsSite.address,
            Statements.date,
            Statements.statement,
        )
        .join(Employees)
        .join(ObjectsSite)
        .where(Statements.date == date)
        .where(Statements.name_id == name_id)
        .select_from(Statements)
    )
    if isinstance(division, int):
        sel = sel.where(Statements.division == division)
    if isinstance(division, str):
        sel = sel.join(Division, Statements.division == Division.id)
        sel = sel.where(Division.division == division)
    return sel


def locations_one_emp(date: dt.date, subscriber_id: int) -> Select:
    """get locations by subscriber_id and date"""
    sel: Select = (
        select(
            Coordinates.subscriberID,
            Coordinates.requestDate,
            Coordinates.locationDate,
            Coordinates.longitude,
            Coordinates.latitude,
        )
        .where(Coordinates.subscriberID == subscriber_id)
        .where(Coordinates.requestDate >= date)
        .where(Coordinates.requestDate < date + dt.timedelta(days=1))
    )
    return sel


def journal_one_emp(name_id: int) -> Select:
    sel: Select = select(
        Journal.name_id,
        Journal.subscriberID,
        Journal.period_init,
        Journal.period_end,
    ).where(Journal.name_id == name_id)
    return sel


def comment(
    division: Optional[int] = None,
    name_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    sel: Select = select(
        Comment.employee_id.label("name_id"),
        Comment.object_id,
        Comment.comment,
    )
    if isinstance(division, int):
        sel = sel.where(Comment.division_id == division)
    if isinstance(division, str):
        sel = sel.join(Division, Comment.division_id == Division.id)
        sel = sel.where(Division.division == division)
    if name_ids:
        sel = sel.where(Comment.employee_id.in_(name_ids))
    return sel


def frequency(
    division: Optional[int] = None,
    name_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    sel: Select = select(
        Frequency.employee_id.label("name_id"),
        Frequency.object_id,
        Frequency.frequency_str.label("frequency"),
    )
    if isinstance(division, int):
        sel = sel.where(Frequency.division_id == division)
    if isinstance(division, str):
        sel = sel.join(Division, Frequency.division_id == Division.id)
        sel = sel.where(Division.division == division)
    if name_ids:
        sel = sel.where(Frequency.employee_id.in_(name_ids))
    return sel


def income(object_ids: List[int], **kwargs) -> Select:
    sel: Select = select(ObjectsSite.object_id, ObjectsSite.income).where(
        ObjectsSite.object_id.in_(object_ids)
    )
    return sel


def no_payments(object_ids: List[int], **kwargs) -> Select:
    sel: Select = (
        select(ObjectsSite.object_id)
        .where(ObjectsSite.no_payments == True)
        .where(ObjectsSite.object_id.in_(object_ids))
    )
    return sel


def holiday_attend_needed(object_ids: List[int], **kwargs) -> Select:
    sel: Select = (
        select(ObjectsSite.object_id)
        .where(ObjectsSite.holiday_attend_needed == True)
        .where(ObjectsSite.object_id.in_(object_ids))
    )
    return sel


def empty_locations() -> Select:
    last_loc = (func.max(Coordinates.locationDate)).label("last_loc")
    prev_hour = dt.datetime.now() - dt.timedelta(hours=1)
    sel: Select = (
        select(Coordinates.subscriberID)
        .where(Coordinates.requestDate >= prev_hour)
        .group_by(Coordinates.subscriberID)
        .having(last_loc == None)
    )
    return sel


def employees_with_nameid_name_phone(name_ids: List[int]) -> Select:
    sel: Select = select(
        Employees.name_id, Employees.name, Employees.phone
    ).where(Employees.name_id.in_(name_ids))
    return sel


def staffers(name_ids: List[int]) -> Select:
    sel: Select = (
        select(Employees.name_id)
        .where(Employees.name_id.in_(name_ids))
        .where(Employees.staffer == True)
    )
    return sel
