# (модели базы данных)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import (
    ForeignKey,
    String,
    Index,
    CHAR,
    UniqueConstraint,
    REAL,
    SMALLINT,
    VARCHAR,
)
import datetime as dt

"""
__table_args__ = (
UniqueConstraint('customer_id', 'location_code', name='_customer_location_uc'),)
Эта опция помогает определить, какое сочетание в таблице будет уникальным.
Если оно не уникально - добавить строку будет нельзя
"""


class Base(DeclarativeBase):
    pass


class Serves(Base):
    __tablename__ = "serves_site"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_id: Mapped[int] = mapped_column(ForeignKey("employees_site.name_id"))
    object_id: Mapped[int] = mapped_column(
        ForeignKey("objects_site.object_id")
    )
    date: Mapped[dt.date]
    comment: Mapped[str] = mapped_column(String(200))
    address: Mapped[str] = mapped_column(String(255))
    approval: Mapped[int]
    employee: Mapped["Employees"] = relationship("Employees", lazy="joined")
    object: Mapped["ObjectsSite"] = relationship("ObjectsSite", lazy="joined")
    __table_args__ = (
        Index("serves_site_date", "date"),
        Index("name_date" "name_id", "date"),
    )

    def __repr__(self):
        return (
            f"Name: {self.name_id} Object: {self.object_id} "
            f"Date: {self.date} Approval: {self.approval}"
        )


class Statements(Base):
    __tablename__ = "statements_site"
    id: Mapped[int] = mapped_column(primary_key=True)
    division: Mapped[int] = mapped_column(ForeignKey("division.id"))
    name_id: Mapped[int] = mapped_column(ForeignKey("employees_site.name_id"))
    object_id: Mapped[int] = mapped_column(
        ForeignKey("objects_site.object_id")
    )
    date: Mapped[dt.date]
    statement: Mapped[str] = mapped_column(CHAR(length=1))
    __table_args__ = (
        Index("StmtsNameDate", "division", "object_id", "date", "name_id"),
        Index("statements_date", "date"),
        UniqueConstraint(
            "division",
            "object_id",
            "date",
            "name_id",
            name="_statements_unique",
        ),
    )

    def __repr__(self):
        return (
            f"Statements({self.id}, {self.division}, {self.name_id}, "
            f"{self.object_id}, {self.date}, {self.statement})"
        )


class Division(Base):
    __tablename__ = "division"
    id: Mapped[int] = mapped_column(primary_key=True)
    division: Mapped[str] = mapped_column(CHAR(20))

    def __repr__(self):
        return f"Division({self.id}, {self.division})"


class Schedule(Base):
    __tablename__ = "schedule"
    id: Mapped[int] = mapped_column(primary_key=True)
    schedule: Mapped[str] = mapped_column(CHAR(20))

    def __repr__(self):
        return f"Schedule({self.id}, {self.schedule})"


class Coordinates(Base):
    __tablename__ = "coordinates"
    locationID: Mapped[int] = mapped_column(primary_key=True)
    requestDate: Mapped[dt.datetime]
    subscriberID: Mapped[int] = mapped_column(nullable=False)
    locationDate: Mapped[dt.datetime]
    longitude: Mapped[float] = mapped_column(REAL)
    latitude: Mapped[float] = mapped_column(REAL)

    __table_args__ = (
        Index(
            "subsIdRequestDate", "subscriberID", "requestDate", "locationDate"
        ),
        Index("subsRequest", "subscriberID", "requestDate"),
        Index("reqDate", "requestDate"),
    )

    def __repr__(self):
        return f"{self.locationID}, {self.subscriberID}, {self.locationDate}"


class Clusters(Base):
    __tablename__ = "clusters_site"
    id: Mapped[int] = mapped_column(primary_key=True)
    subscriberID: Mapped[int]
    date: Mapped[dt.date]
    datetime: Mapped[dt.datetime]
    longitude: Mapped[float] = mapped_column(REAL)
    latitude: Mapped[float] = mapped_column(REAL)
    leaving_datetime: Mapped[dt.datetime]
    cluster: Mapped[int] = mapped_column(nullable=False)

    __table_args__ = (Index("subsIdDate", "subscriberID", "date"),)

    def __repr__(self):
        return f"{self.id}, {self.subscriberID}, {self.date}"


class Journal(Base):
    __tablename__ = "journal_site"
    id: Mapped[int] = mapped_column(primary_key=True)
    name_id: Mapped[int] = mapped_column(ForeignKey("employees_site.name_id"))
    subscriberID: Mapped[int]
    period_init: Mapped[dt.date]
    period_end: Mapped[dt.date]
    name: Mapped["Employees"] = relationship("Employees", lazy="joined")
    __table_args__ = (
        Index("journal_site_index", "name_id", "subscriberID"),
        Index("journal_site_subscriberID_index", "subscriberID"),
    )

    def __repr__(self):
        return (
            f"SubsID: {self.subscriberID} Name_id: {self.name_id} "
            f"Init: {self.period_init} End: {self.period_end}"
        )


class Employees(Base):
    __tablename__ = "employees_site"
    name_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(CHAR(length=100))
    phone: Mapped[str] = mapped_column(CHAR(length=13))
    address: Mapped[str] = mapped_column(CHAR(length=150))
    hire_date: Mapped[dt.date]
    quit_date: Mapped[dt.date]
    no_tracking: Mapped[bool]
    bath_attendant: Mapped[bool]
    division: Mapped[int] = mapped_column(ForeignKey("division.id"))
    schedule: Mapped[int] = mapped_column(ForeignKey("schedule.id"))
    staffer: Mapped[bool]
    division_ref: Mapped["Division"] = relationship("Division", lazy="joined")
    schedule_ref: Mapped["Schedule"] = relationship("Schedule", lazy="joined")

    __table_args__ = (Index("emp_index", "name_id", "name"),)

    def __repr__(self):
        return f"Employees({self.name_id}, {self.name}, {self.division})"


class ObjectsSite(Base):
    __tablename__ = "objects_site"
    object_id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(CHAR(length=100))
    division: Mapped[int] = mapped_column(ForeignKey("division.id"))
    address: Mapped[str] = mapped_column(CHAR(length=250))
    phone: Mapped[str] = mapped_column(CHAR(length=200))
    longitude: Mapped[float] = mapped_column(REAL)
    latitude: Mapped[float] = mapped_column(REAL)
    radius: Mapped[int]
    active: Mapped[bool]
    no_payments: Mapped[bool]
    income: Mapped[float]
    admission_date: Mapped[dt.date]
    denial_date: Mapped[dt.date]
    apartment_number: Mapped[str] = mapped_column(CHAR(length=50))
    holiday_attend_needed: Mapped[bool]
    personal_service_after_revision: Mapped[str] = mapped_column(
        CHAR(length=70)
    )
    division_ref: Mapped["Division"] = relationship("Division", lazy="joined")
    comment: Mapped[str] = mapped_column(CHAR(length=200))

    def __repr__(self):
        return f"ObjID: {self.object_id}, Name: {self.name}"


class Frequency(Base):
    __tablename__ = "frequency"
    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int]
    employee_id: Mapped[int]
    object_id: Mapped[int]
    frequency: Mapped[int]
    frequency_str: Mapped[str] = mapped_column(CHAR(length=3))
    __table_args__ = (
        Index("frequency_index", "division_id", "employee_id", "object_id"),
        UniqueConstraint(
            "division_id", "employee_id", "object_id", name="_frequency"
        ),
    )


class Comment(Base):
    __tablename__ = "comment"
    id: Mapped[int] = mapped_column(primary_key=True)
    division_id: Mapped[int]
    employee_id: Mapped[int]
    object_id: Mapped[int]
    comment: Mapped[str] = mapped_column(CHAR(length=250))
    __table_args__ = (
        Index("comment_index", "division_id", "employee_id", "object_id"),
        UniqueConstraint(
            "division_id",
            "employee_id",
            "object_id",
            name="_comment_and_frequency",
        ),
    )


class OwnTracksLocation(Base):
    __tablename__ = "owntracks_location"
    id: Mapped[int] = mapped_column(primary_key=True)
    employee_id: Mapped[int]
    bssid: Mapped[str] = mapped_column(VARCHAR(32), nullable=True)
    ssid: Mapped[str] = mapped_column(VARCHAR(32), nullable=True)
    acc: Mapped[int] = mapped_column(nullable=True)
    batt: Mapped[int] = mapped_column(SMALLINT(), nullable=True)
    bs: Mapped[int] = mapped_column(SMALLINT())
    conn: Mapped[str] = mapped_column(CHAR(1), nullable=True)
    created_at: Mapped[int] = mapped_column(nullable=True)
    lat: Mapped[float] = mapped_column(REAL)
    lon: Mapped[float] = mapped_column(REAL)
    m: Mapped[int] = mapped_column(SMALLINT(), nullable=True)
    t: Mapped[str] = mapped_column(CHAR(1), nullable=True)
    tst: Mapped[int] = mapped_column(nullable=True)
    vel: Mapped[int] = mapped_column(SMALLINT(), nullable=True)


class PermitStatements(Base):
    __tablename__ = "permit_statements"
    id: Mapped[int] = mapped_column(primary_key=True)
    object_id: Mapped[int] = mapped_column(
        ForeignKey("objects_site.object_id")
    )
    date: Mapped[dt.date]

    __table_args__ = (
        Index("object_id", "date"),
        UniqueConstraint(
            "object_id", "date", name="_permit_statements_unique_constraint"
        ),
    )
