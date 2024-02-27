from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column, CHAR, VARCHAR, Table, ForeignKey, SMALLINT
from flask_login import UserMixin
from trajectory_report.models import (
    Base, Serves, Statements, Division, Schedule, Coordinates, Clusters,
    Journal, Employees, ObjectsSite, Comment, Frequency, OwnTracksLocation,
    PermitStatements)
from typing import List


user_access = Table(
    'user_access',
    Base.metadata,
    Column('user_id', ForeignKey('user.id', ondelete='CASCADE')),
    Column('division_id', ForeignKey('division.id'))
)


class Rang(Base):
    __tablename__ = 'rang'
    id: Mapped[int] = mapped_column(primary_key=True)
    rang: Mapped[str] = mapped_column(CHAR(13))


class User(Base, UserMixin):
    __tablename__ = 'user'
    id: Mapped[int] = mapped_column(primary_key=True)
    rang_id: Mapped["Rang"] = mapped_column(ForeignKey('rang.id'))
    name: Mapped[str] = mapped_column(CHAR(50), nullable=False)
    phone: Mapped[str] = mapped_column(CHAR(11), nullable=False)
    access: Mapped[List['Division']] = relationship(
        'Division',
        secondary='user_access',
        cascade="delete, all",
        passive_deletes=True
    )
    password: Mapped[str] = mapped_column(CHAR(60), nullable=False)
    rang: Mapped['Rang'] = relationship('Rang', lazy='joined')

    @property
    def access_list(self):
        accessed = []
        for i in self.access:
            accessed.extend([i.id, i.division])
        return accessed

    def __repr__(self):
        return f"User({self.name}, access: {self.access})"

"""
{
    '_type': 'location', 
    'BSSID': '40:ed:00:57:69:c0', \\ if available, identifies the access point
    'SSID': 'sosed', \\ if available, is the unique name of the WLAN
    'acc': 100, \\ точность локации
    'alt': 63, \\ высота над уровнем моря
    'batt': 93, \\ процент заряда батареи
    'bs': 1, \\ Battery Status 0=unknown, 1=unplugged, 2=charging, 3=full 
    'conn': 'w', \\ Internet connectivity status: w - WiFi; o - offline; m - mobile data
    'created_at': 1708332621, \\ the time at which the message is constructed (vs. tst which is the timestamp of the GPS fix) 
    'lat': 35.3369338, 
    'lon': 33.2674035, 
    'm': 1, \\ режим сбора координат: significant=1, move=2
    't': 'p', \\ триггер локации 
    'tid': 'su', \\ Tracker ID used to display the initials of a user
    'topic': 'owntracks/ilia/begonia', \\ contains the original publish topic
    'tst': 1708332621, \\ UNIX epoch timestamp in seconds of the location fix
    'vac': 100, \\ vertical accuracy of the alt element
    'vel': 0 \\  velocity (integer/kmh/optional)
}
"""