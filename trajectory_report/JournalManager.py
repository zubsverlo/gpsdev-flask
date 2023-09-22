# ~~ЖУРНАЛ ИСПОЛЬЗОВАНИЯ ID~~
# этот модуль предназначен для отслеживания, в какой период времени
# и кем использовался конкретный ID (subscriberID в МТС).
# модуль редактирует записи владельца ID в БД и добавляет новые.
# журнал реагирует на изменения в MTS, поэтому регулярно запрашивает
# по API актуальный список абонентов.
# ~АЛГОРИТМ РАБОТЫ~
# Запрашивается список абонентов из мтс
# Из БД запрашивается список неуволенных сотрудников
# И словарь из актуальных записей journal.
# Сотрудники без subscriberID образуют список неотслеживаемых
# Сотрудники, которые были уволены, но ещё отслеживаются,
# дополняют список на удаление, как и сотрудники,
# которых и в помине нет.
# По остальным нужно сравнить subscriberID. Если он не совпадает - значит
# было изменение. Текущую запись в БД нужно завершить, а затем открыть новую,
# с тем же именем и с текущей даты.


from trajectory_report.api.mts import get_subscribers
from trajectory_report.database import DB_ENGINE
import datetime as dt
from trajectory_report.models import Employees, Statements, Journal, Division
from sqlalchemy import select, update
from sqlalchemy.orm import Session
import pandas as pd
from collections import defaultdict
from numpy import nan


class JournalManager:

    def __init__(self):
        self.session = Session(DB_ENGINE)
        # Работающие на текущий момент сотрудники
        self.emps = self.get_employees_actual()
        # Список сотрудников из МТС
        mts = get_subscribers()
        self.mts = {i['name']: i['subscriberID'] for i in mts}
        # self.company_dict = {i['subscriberID']: i['company'] for i in mts}
        self.company_dict = defaultdict(list)
        for i in mts:
            self.company_dict[i['company']].append(i['subscriberID'])
        # получить открытые записи из журнала:
        self.journal_db = self.get_journal_actual()

        self.trackable = set.intersection(
            set(self.mts.keys()),
            set([i['name'] for i in self.emps]))
        # self.divisions_dict = self.get_divisions_dict()

    def set_quit_date(self):
        """Проставляет дату увольнения сотрудникам, которые попадают под
        критерий: в шахматке проставлено "У" или последняя информация в
        statements была более 28 дней назад.
        """
        sel = select(Employees.name_id).where(Employees.quit_date == None)
        not_fired = self.session.execute(sel).all()
        not_fired = [i.name_id for i in not_fired]

        sel = select(Statements.name_id, Statements.date, Statements.statement)\
            .where(Statements.date >= (dt.date.today()-dt.timedelta(days=45)))\
            .where(Statements.name_id.in_(not_fired))
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        res = pd.DataFrame(res)

        def last_day(x):
            x = x.sort_values(by='date', ascending=False)
            return x.iloc[0]

        res = res.groupby(by=['name_id'], as_index=False)\
            .apply(lambda x: last_day(x))

        res['quit_date'] = res.apply(
            lambda x: x.date if x.statement == "У" or (
                        dt.date.today() - x.date) > dt.timedelta(
                days=28) else nan, axis=1)
        res = res[res['quit_date'].notna()]
        res = res[['name_id', 'quit_date']].to_dict(orient='records')
        for i in res:
            sel = update(Employees).where(Employees.name_id == i['name_id'])\
            .values(quit_date=i['quit_date'])
            self.session.execute(sel)
        self.session.commit()
        print('allright, employees now are fired:', len(res))


    def get_employees_actual(self):
        """Получить список словарей со всеми сотрудниками,
        которые не были уволены"""
        sel = select(Employees.name, Employees.name_id,
                     Employees.phone,
                     Division.division) \
            .join(Division)\
            .where(Employees.quit_date == None)
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        return res

    @property
    def untrackable(self):
        """Добавленные, но не подключенные сотрудники
        [{name, name_id, phone, division}]"""
        names = set([i['name'] for i in self.emps]) - set(self.mts.keys())
        return [i for i in self.emps if i['name'] in names]


    def get_journal_actual(self):
        """Получить из БД список subscriberID по всем текущим записям
        отслеживания"""
        sel = select(Journal.name_id, Journal.subscriberID) \
            .where(Journal.period_end == None)
        self.session.execute(sel)
        return {i.name_id: i.subscriberID
                for i in self.session.execute(sel).all()}

    def journal_usage_close(self, subscriber_id, name_id):
        """Закрытие периода владения устройством"""
        sel = update(Journal).where(Journal.subscriberID == subscriber_id,
                                    Journal.name_id == name_id,
                                    Journal.period_end == None)\
                .values(period_end=dt.date.today()-dt.timedelta(days=1))
        self.session.execute(sel)

    def journal_usage_open(self, sub_id, name_id):
        """Открытие периода владения устройством"""
        self.session.add(Journal(
            subscriberID=sub_id,
            name_id=name_id,
            period_init=dt.date.today()
        ))

    def update_journal(self):
        """Обновление journal. По добавляются записи по новеньким,
        проставляются изменения по стареньким."""
        for i in self.emps:
            i['subscriberID'] = self.journal_db.get(i['name_id'])
        trackable_dict = {}
        for i in self.emps:
            if i['name'] in list(self.trackable):
                trackable_dict[i['name']] = dict(
                    subs_id=i['subscriberID'],
                    name_id=i['name_id'])
        for name in self.trackable:
            # отслеживаемые сотрудники
            if trackable_dict[name]['subs_id'] != self.mts[name]:
                # если не совпадают subscriberID
                if trackable_dict[name]['subs_id'] is None:
                    # если нет текущего отслеживаемого устройства,
                    # добавляем запись
                    self.journal_usage_open(self.mts.get(name),
                                            trackable_dict[name]['name_id'])
                else:
                    # в ином случае - закрываем текущую и открываем новую
                    self.journal_usage_close(trackable_dict[name]['subs_id'],
                                             trackable_dict[name]['name_id'])
                    self.journal_usage_open(self.mts.get(name),
                                            trackable_dict[name]['name_id'])
        self.session.commit()

    def get_divisions_dict(self):
        """Словарь с учреждениями по name_id,
        показывает, в каких учреждениях был сотрудник"""
        sel = select(Statements.name_id,
                     Statements.division)\
            .group_by(Statements.division,
                      Statements.name_id)
        columns = [i.name for i in sel.selected_columns]
        res = self.session.execute(sel).all()
        res = [{k: getattr(r, k) for k in columns} for r in res]
        res = pd.DataFrame(res)\
                .groupby('name_id')\
                .agg(list)\
                .to_dict()['division']
        return res

    def get_company_by_subscriberID(self, subscriberID) -> str:
        """Получить название компании по subscriberID"""
        for company, list_of_subs in self.company_dict.items():
            if subscriberID in list_of_subs:
                return company

    @property
    def removable(self):
        """Сотрудники на удаление, но с возможностью уточнить subscriberID
        и компанию
        [{name, subscriberID}]"""
        removable = set(self.mts.keys()) - set([i['name'] for i in self.emps])
        return [{'name': k,
                 'subscriberID': v,
                 'company': self.get_company_by_subscriberID(v)}
                for k, v in self.mts.items() if k in removable]
