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
    OwnTracksCluster,
    OwnTracksLocation,
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


def statements_extended(
    date_from: dt.date,
    date_to: dt.date,
    division: Optional[Union[int, str]] = None,
    name_ids: Optional[List[int]] = None,
    object_ids: Optional[List[int]] = None,
) -> Select:
    """Получить записи с заявленными выходами"""

    sel = (
        select(
            Statements.name_id.label('uid'),
            Statements.object_id,
            Statements.date,
            Statements.statement,
        )
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


def employees(ids: list[int] | None = None, **kwargs) -> Select:
    """Все сотрудники"""
    sel: Select = select(
        Employees.name_id.label('uid'),
        Employees.name,
        Employees.bath_attendant,
        Employees.schedule,
        Employees.phone,
        Employees.staffer,
    )
    if ids:
        sel = sel.where(Employees.name_id.in_(ids))
    return sel


def objects(ids: list[int] | None = None, **kwargs) -> Select:
    """Все объекты (подопечные)"""
    sel: Select = select(
        ObjectsSite.object_id,
        ObjectsSite.name.label("object"),
        ObjectsSite.latitude.label("object_lat"),
        ObjectsSite.longitude.label("object_lng"),
        ObjectsSite.address,
        ObjectsSite.no_payments,
        ObjectsSite.income,
    )
    if ids:
        sel = sel.where(ObjectsSite.object_id.in_(ids))
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
        Journal.owntracks,
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
        Serves.name_id.label('uid'),
        Serves.object_id,
        Serves.date,
        Serves.approval,
    ).where(Serves.date >= date_from)

    if date_to:
        sel = sel.where(Serves.date <= date_to)
    if name_ids:
        sel = sel.where(Serves.name_id.in_(name_ids))
    return sel


def current_locations_mts(
    subscriber_ids: Optional[List[int]] = None, **kwargs
) -> Select:
    """get current locations by subscriber_ids"""
    sel: Select = (
        select(
            Coordinates.subscriberID.label('uid'),
            Coordinates.locationDate.label('datetime'),
            Coordinates.longitude.label('lng'),
            Coordinates.latitude.label('lat'),
        )
        .where(Coordinates.requestDate > dt.date.today())
        .where(Coordinates.locationDate != None)
    )
    if subscriber_ids:
        sel = sel.where(Coordinates.subscriberID.in_(subscriber_ids))
    return sel


def current_locations_owntracks(
    employee_ids: Optional[List[int]] = None, **kwargs
) -> Select:
    """get current locations by subscriber_ids"""
    sel: Select = select(
        OwnTracksLocation.employee_id.label('uid'),
        OwnTracksLocation.created_at,
        OwnTracksLocation.tst,
        OwnTracksLocation.lon.label('lng'),
        OwnTracksLocation.lat,
    ).where(OwnTracksLocation.created_at > dt.date.today())
    if employee_ids:
        sel = sel.where(OwnTracksLocation.employee_id.in_(employee_ids))
    return sel


def clusters(
    date_from: dt.date,
    date_to: Optional[dt.date] = None,
    subscriber_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    """Получить кластеры из БД"""
    sel: Select = select(
        Clusters.subscriberID.label('uid'),
        Clusters.date,
        Clusters.datetime,
        Clusters.longitude.label('lng'),
        Clusters.latitude.label('lat'),
        Clusters.leaving_datetime,
        Clusters.cluster,
    ).where(Clusters.date >= date_from)

    if date_to:
        sel = sel.where(Clusters.date < date_to + dt.timedelta(days=1))
    if subscriber_ids:
        sel = sel.where(Clusters.subscriberID.in_(subscriber_ids))
    return sel


def clusters_owntracks(
    date_from: dt.date,
    date_to: Optional[dt.date] = None,
    employee_ids: Optional[List[int]] = None,
    **kwargs
) -> Select:
    sel: Select = select(
        OwnTracksCluster.employee_id.label("uid"),
        OwnTracksCluster.date,
        OwnTracksCluster.datetime,
        OwnTracksCluster.longitude.label('lng'),
        OwnTracksCluster.latitude.label('lat'),
        OwnTracksCluster.leaving_datetime,
        OwnTracksCluster.cluster,
    ).where(OwnTracksCluster.date >= date_from)

    if date_to:
        sel = sel.where(OwnTracksCluster.date < date_to + dt.timedelta(days=1))
    if employee_ids:
        sel = sel.where(OwnTracksCluster.employee_id.in_(employee_ids))
    return sel


def statements_one_emp(
    date: dt.date, name_id: int, division: Union[int, str]
) -> Select:
    sel = (
        select(
            Statements.name_id.label('uid'),
            Employees.name,
            Statements.object_id,
            ObjectsSite.name.label("object"),
            ObjectsSite.longitude.label("object_lng"),
            ObjectsSite.latitude.label("object_lat"),
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


def statements_one_emp_extended(
    date: dt.date, name_id: int, division: int | str | None
) -> Select:
    sel = (
        select(
            Statements.name_id,
            Statements.object_id,
            Statements.date,
            Statements.statement,
        )
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
            Coordinates.subscriberID.label('uid'),
            Coordinates.locationDate.label('datetime'),
            Coordinates.longitude.label('lng'),
            Coordinates.latitude.label('lat'),
        )
        .where(Coordinates.subscriberID == subscriber_id)
        .where(Coordinates.requestDate >= date)
        .where(Coordinates.requestDate < date + dt.timedelta(days=1))
    )
    return sel


def locations_one_emp_owntracks(date: dt.date, employee_id: int) -> Select:
    sel: Select = (
        select(
            OwnTracksLocation.employee_id.label('uid'),
            OwnTracksLocation.created_at,
            OwnTracksLocation.tst,
            OwnTracksLocation.lon.label('lng'),
            OwnTracksLocation.lat,
        )
        .where(OwnTracksLocation.created_at > date)
        .where(OwnTracksLocation.created_at < date + dt.timedelta(days=1))
        .where(OwnTracksLocation.employee_id == employee_id)
    )
    return sel


def journal_one_emp(name_id: int) -> Select:
    sel: Select = select(
        Journal.name_id.label("uid"),
        Journal.subscriberID,
        Journal.period_init,
        Journal.period_end,
        Journal.owntracks,
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


def empty_locations_owntracks() -> Select:
    prev_hour = dt.datetime.now() - dt.timedelta(hours=1)
    sel: Select = select(
        OwnTracksLocation.employee_id.distinct().label("name_id")
    ).where(OwnTracksLocation.created_at >= prev_hour)
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
