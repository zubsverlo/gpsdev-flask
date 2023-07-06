from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import Column, CHAR, Table, ForeignKey
from flask_login import UserMixin
from trajectory_report.models import (
    Base, Serves, Statements, Division, Schedule, Coordinates, Clusters,
    Journal, Employees, ObjectsSite)
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
