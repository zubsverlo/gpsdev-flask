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

"""Нужно добавить метод, который возващает сотрудников из списка уволенных
в список актуальных, если оказалось, что после "У" появились другие выходы.
Нужно анализировать таблицу statements, запросить их для всех уволенных
сотрудников и проанализировать.

Ещё, когда сотрудник перестает отслеживаться в мтс, нужно закрывать период
в journal.
Ещё хотелось бы видеть подразделение, в котором работал сотрудник, когда его
нужно удалить из отслеживания, если его можно получить.
"""

from trajectory_report.api.mts import get_subscribers
from trajectory_report.database import DB_ENGINE
import datetime as dt
from trajectory_report.models import Employees, Statements, Journal, Division
from sqlalchemy import select, update, and_
from sqlalchemy.orm import Session
import pandas as pd
from collections import defaultdict
from numpy import nan
from sqlalchemy import func, distinct


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
        pass

    def set_quit_date(self):
        """Проставляет дату увольнения сотрудникам, которые попадают под
        критерий: в шахматке проставлено "У" или последняя информация в
        statements была более 28 дней назад.
        """
        sel = select(Employees.name_id).where(Employees.quit_date == None)
        not_fired = self.session.execute(sel).all()
        not_fired = [i.name_id for i in not_fired]

        sel = select(
            Statements.name_id,
            Statements.date,
            Statements.statement)\
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
        sel = update(Journal).where(
            Journal.subscriberID == subscriber_id,
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

    def get_company_by_subscriberID(self, subscriberID) -> str | None:
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


class HrManager:
    """
    HrManager управляет сотрудниками:
      Отслеживает новых без подключения
      Предлагает отключить удаленных
      Контролирует Journal таблицу, закрывая периоды пользования
      Возвращает удаленных сотрудников, если по ним снова есть выходы.
      В целом, хотелось бы от такого объекта получать исчерпанную информацию:
        Есть ли проблемы с локациями?
        Давно ли были проставлены последние выходы?
        А что по соотношению выходов к невыходам?
      Это требования к Dashboard, а HrManager дополняет его информацией, но
      анализируя только statements, journal и инормацию с MTS.
    Мне нужна информация:
    От МТС - Имя, subsID, компания (все текущие подключенные)
    Из БД - employees (возможно, все), journal
    """

    def __init__(self) -> None:
        self.session = Session(DB_ENGINE)
        """
        Мне нужны данные:
            Сотрудники, которые не подключены к отслеживанию
            Сотрудники, которые подключены, но по ним не заполнены выходы
            Сотрудники, по которым последний выход был заполнен N дней назад
            Сотрудники, которых нужно удалить в связи с увольнением:
                Желательно с сортировкой по учреждениям, если такие данные есть

        Скрипт должен:
            Закрывать периоды journal, если subscriberID нет в актуальном MTS
            Добавлять запись в journal, если сотрудника подключили
            Закрывать старый период и открывать новый, если поменялись данные
        """
        
        # Все сотрудники (для изменений и отслеживания инфо по ним)
        self.employees = self._get_employees()
        
        # По каждому сотруднику все выходы за последний имеющийся день
        # вынести из last_day столбцы: последния дата выходов, есть ли в ней У
        self.last_day_statements = self._get_last_day_statements()
        
        # Список сотрудников, по которым не было проставлено ни одного выхода
        # вынести в отдельный столбец пометку: no_statements
        self.not_in_statements = self._get_not_existing_in_statements()
        
        # Список подписчиков из МТС с компаниями
        # столбец: mts_active
        # Чтобы у них был name_id для совмещения, сначала нужно собрать эти
        # данные из таблицы Employees (в какой момент времени?),
        # чтобы можно было совместить её со всеми остальными таблицами.
        # UPD: Пусть объединение будет по name сотрудника, а не name_id
        self.mts_subscribers = self._get_mts_subscribers()
        
        # Открытые текущие записи журнала
        # вынести в столбец: открыт ли период в journal
        self.journal_opened = self._get_journal_opened()
        
        # Идея: совместить всё в одну таблицу, и в ней проводить анализ
        # вынести из last_day столбцы: последния дата выходов, есть ли в ней У
        df = self.employees.copy()
        df = pd.merge(df, self.last_day_statements, on='name_id')
        df = pd.concat([df, self.not_in_statements])
        df = pd.merge(df, self.journal_opened,
                      on=[
                          'name_id', 'name', 'division', 
                          'hire_date', 'quit_date', 'no_tracking'
                          ],
                      how='outer')
        df = pd.merge(df, self.mts_subscribers, on='name', how='outer')
        df['subscriberID_equal'] = df['subscriberID'] == df['subscriberID_mts']
        df = df.fillna(
            value={'mts_active': False,
                   'journal_opened': False,
                   'no_statements': False}
            )
        del_quit_date = (pd.notna(df['quit_date']))\
            & (df['contains_fired_stmt'] == False)
            
        set_quit_date = (pd.isna(df['quit_date']))\
            & (df['contains_fired_stmt'] == True)
            
        close_journal_period = (df['journal_opened'] == True)\
            & (df['mts_active'] == False)
            
        open_journal_period = (df['mts_active'] == True)\
            & (df['journal_opened'] == False)\
            & (pd.isna(df['quit_date']))\
            & (pd.notna(df['name_id']))
            
        open_close_journal_period = (df['mts_active'] == True)\
            & (df['journal_opened'] == True)\
            & (df['subscriberID_equal'] == False)\
            & (pd.notna(df['name_id']))
        
        # suggestions
        DATE_21_DAYS_AGO = dt.date.today()-dt.timedelta(days=21)
        # проставлять увольнение по дате посл. выхода в statements
        to_set_abandoned_quit = (pd.notna(df['name_id']))\
            & (pd.isna(df['quit_date']))\
            & (df['contains_fired_stmt'] == False)\
            & (df['last_stmt_date'] <= DATE_21_DAYS_AGO)
        
        # уже уволенные
        to_del_from_mts = (pd.notna(df['quit_date']))\
            & (df['mts_active'] == True)
        
        # им бы проставить увольнение - в таблице
        no_statements = (df['mts_active'] == True)\
            & (df['no_statements'] == True)
            
        # этих нужно подключить
        to_activate = (df['mts_active'] == False)\
            & (df['no_tracking'] == False)\
            & (pd.isna(df['quit_date']))
        
            
        pass

    def _get_employees(self) -> pd.DataFrame:
        sel = select(
            Employees.name_id, Employees.name, Employees.division, 
            Employees.no_tracking, Employees.hire_date, Employees.quit_date
        )
        return pd.read_sql(sel, DB_ENGINE.connect())

    def _get_last_day_statements(self) -> pd.DataFrame:
        # ("select ta.name_id, employees_site.quit_date, ta.date, "
        #  "employees_site.name, statements_site.statement from "
        #  "(select name_id, max(date) as date from statements_site "
        #  "group by name_id) as ta join statements_site on "
        #  "ta.name_id = statements_site.name_id and ta.date = "
        #  "statements_site.date join employees_site on ta.name_id = "
        #  "employees_site.name_id order by employees_site.name;")
        subq = select(
            Statements.name_id.label('name_id'),
            func.max(Statements.date).label('last_stmt_date')
        ).group_by(Statements.name_id).alias('subq')
        
        sel_max_date = select(
            subq.c.name_id, subq.c.last_stmt_date,
            Statements.statement, Employees.quit_date
        )\
            .join(
                Statements,
                and_(
                    (subq.c.name_id == Statements.name_id),
                    (subq.c.last_stmt_date == Statements.date)
                )
            )\
            .join(
                Employees, Employees.name_id == subq.c.name_id
            )
        
        df = pd.read_sql(sel_max_date, DB_ENGINE.connect())
        contains_fired_stmt = df\
            .groupby(['name_id'])\
            .apply(lambda x: "У" in list(x.statement))
        df = df.set_index('name_id')
        df['contains_fired_stmt'] = contains_fired_stmt
        df = df.reset_index()
        df = df.drop_duplicates(subset='name_id')
        return df[['name_id', 'last_stmt_date', 'contains_fired_stmt']]

    def _get_not_existing_in_statements(self) -> pd.DataFrame:
        # (
        #     "select division.division, name_id, name, phone, hire_date, "
        #     "quit_date from employees_site join division on "
        #     "employees_site.division = division.id where name_id not in "
        #     "(select distinct name_id from statements_site) and quit_date is "
        #     "null order by division;"
        # )
        # select division.division, name_id, name, phone, hire_date, quit_date from employees_site join division on employees_site.division = division.id where name_id not in (select distinct name_id from statements_site) and quit_date is null order by division;
        subsel = select(
            distinct(Statements.name_id)
        )
        sel = select(
            Division.division.label('division_name'),
            Division.id.label('division'),
            Employees.name_id,
            Employees.name,
            Employees.hire_date,
            Employees.quit_date,
            Employees.no_tracking
        )\
            .where(Employees.name_id.not_in(subsel))\
            .where(Employees.quit_date == None)\
            .join(Division, Employees.division == Division.id)
        df = pd.read_sql(sel, DB_ENGINE.connect())
        df['no_statements'] = True
        return df

    def _get_journal_opened(self) -> pd.DataFrame:
        sel = select(
            Journal.id, Journal.name_id, Journal.subscriberID, 
            Journal.period_init, Journal.period_end,
            Employees.name, Employees.division, 
            Employees.hire_date, Employees.quit_date, Employees.no_tracking
        ).where(Journal.period_end == None)\
            .join(Employees, Journal.name_id == Employees.name_id)
        df = pd.read_sql(sel, DB_ENGINE.connect())
        df['journal_opened'] = True
        return df[['name_id', 'subscriberID', 'period_init', 
                   'period_end', 'journal_opened', 'name',
                   'division', 'quit_date', 'hire_date', 'no_tracking']]

    def _get_mts_subscribers(self) -> pd.DataFrame:
        subscribers = get_subscribers()
        df = pd.DataFrame(subscribers)
        df['mts_active'] = True
        df = df.rename(columns={'subscriberID': 'subscriberID_mts'})
        return df[['company', 'subscriberID_mts', 'name', 'mts_active']]


if __name__ == "__main__":
    j = HrManager()
    pass
