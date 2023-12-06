import time
import pandas as pd
import datetime as dt
import numpy as np
from math import cos, asin, sqrt, pi
from numpy import NaN
from trajectory_report.config import REPORT_BASE, STATS_CHECKOUT
import io
import xlsxwriter
from typing import Optional, Union, List
from trajectory_report.report.ConstructReport import OneEmployeeReportDataGetter
from trajectory_report.report.ConstructReport import report_data_factory


class ReportBase:

    def _calculate_distance(self,
                            stmts_jrnl_clstrs: pd.DataFrame) -> pd.DataFrame:
        """
        Высчитывание дистанции между объектами и кластерами локаций.
        Все кластеры, не входящие в заданный радиус, отбрасываются, так как
        здесь формируются отчеты о посещениях.
        """
        def dist(x: pd.Series) -> bool:
            return self.__distance(
                x.latitude_object, x.longitude_object,
                x.latitude_clusters, x.longitude_clusters
            ) <= REPORT_BASE['RADIUS'] / 1000
        # По каждой строке высчитывается дистанция, в пределах радиуса - True.
        stmts_jrnl_clstrs['in_radius'] = stmts_jrnl_clstrs.apply(dist, axis=1)
        stmts_jrnl_clstrs = stmts_jrnl_clstrs[stmts_jrnl_clstrs['in_radius']]
        return stmts_jrnl_clstrs.reset_index()

    def _calculate_distance_vectorized(self,
                                       stmts_jrnl_clstrs: pd.DataFrame
                                       ) -> pd.DataFrame:
        """
        Высчитывание дистанции между объектами и кластерами локаций.
        Все кластеры, не входящие в заданный радиус, отбрасываются, так как
        здесь формируются отчеты о посещениях.
        """

        # numpy массивы с координатами для вычисления дистанции
        object_lat = np.array(stmts_jrnl_clstrs.latitude_object)
        object_lon = np.array(stmts_jrnl_clstrs.longitude_object)
        cluster_lat = np.array(stmts_jrnl_clstrs.latitude_clusters)
        cluster_lon = np.array(stmts_jrnl_clstrs.longitude_clusters)

        # По каждой строке высчитывается дистанция, в пределах радиуса - True.
        distances = self.__distance_vectorized(object_lat, object_lon, cluster_lat, cluster_lon)
        distances = [i <= REPORT_BASE['RADIUS'] / 1000 for i in distances]
        stmts_jrnl_clstrs['in_radius'] = distances
        stmts_jrnl_clstrs = stmts_jrnl_clstrs[stmts_jrnl_clstrs['in_radius']]
        return stmts_jrnl_clstrs.reset_index()

    @staticmethod
    def __distance(lat1: float, lon1: float, lat2: float,
                   lon2: float) -> float:
        p = pi / 180
        a = 0.5 - cos(
            (lat2 - lat1) * p) / 2 + cos(lat1 * p) * cos(lat2 * p) * (
                    1 - cos((lon2 - lon1) * p)) / 2
        return 12742 * asin(sqrt(a))

    @staticmethod
    def __distance_vectorized(lat1: np.array, lon1: np.array,
                              lat2: np.array, lon2: np.array
                              ) -> np.array:
        p = np.pi / 180
        a = 0.5 - np.cos(
            (lat2 - lat1) * p) / 2 + np.cos(lat1 * p) * np.cos(lat2 * p) * (
                    1 - np.cos((lon2 - lon1) * p)) / 2
        return 12742 * np.arcsin(np.sqrt(a))

    @staticmethod
    def _consolidate_time_periods(df):
        df = df.sort_values(by='datetime')
        df['p_leaving_datetime'] = df.leaving_datetime.shift(1)
        df['diff'] = df.datetime - df.p_leaving_datetime
        ind = df.loc[
            df['diff'] > dt.timedelta(
                minutes=REPORT_BASE['MINS_BETWEEN_ATTENDS'])
        ].index
        df.loc[ind, 'a'] = ind
        df['a'] = df['a'].fillna(method='ffill').fillna(0)

        ind = df.a.unique().tolist()
        for i in ind:
            df.loc[df.a == i, 'datetime'] = df.loc[df.a == i].datetime.min()
            df.loc[df.a == i, 'leaving_datetime'] = df.loc[
                df.a == i].leaving_datetime.max()
        df = df.drop_duplicates(subset=['datetime', 'leaving_datetime'])
        return df

    @staticmethod
    def _consolidate_time_periods_vectorized(df):
        """Объединение кластеров по периодам, версия с векторизацией.
        Алгоритм ускорен в 500 раз по времени исполнения"""
        # сортировка данных - ключевой этап
        df = df.sort_values(
            ['name_id', 'object_id', 'date', 'datetime'])

        # leaving_date последующей строки меньше, чем текущей.
        # Это означает, что последующий кластер охватывает период, который
        # уже включен в текущий кластер. Такие строки (последующий кластер)
        # не несут никакой ценности, поэтому мы их удаляем.
        df['next_ld_is_less'] = df.groupby(['name_id', 'object_id', 'date']) \
                                     ['leaving_datetime'].shift(-1) <= df[
                                     'leaving_datetime']
        # Смещаем bool на строку ниже, добавляя столбец
        df['odd_line'] = df['next_ld_is_less'].shift(1)

        # Удаляем столбец. fillna(False), чтобы покрыть образовавшийся NaT в
        # первой строке при смещении bool вниз.
        df = df[~df['odd_line'].fillna(False)]

        # В случае, если в таблице нет ни одного зафиксированного выхода,
        # после "удаления" лишних строк останется пустой DF без Columns.
        # Чтобы не возникло key_error при дальнейшней обработке, на этом месте
        # вернём пустой df со всеми столбцами:
        if df.empty:
            return pd.DataFrame(
                columns=[
                    'subscriberID', 'date', 'name_id', 'name', 'object_id',
                    'object', 'longitude_object', 'latitude_object',
                    'statement', 'j_exist', 'datetime', 'longitude_clusters',
                    'latitude_clusters', 'leaving_datetime', 'cluster',
                    'in_radius', 'next_ld_is_less', 'odd_line',
                    'time_difference'
                    ]
                )

        # time_difference - это разница между leaving_datetime текущей строки
        # и datetime последующей. Так мы определяем, относить ли два кластера
        # к одному периоду, чтобы совместить их в один.
        # Выше мы удалили все строки, где leaving_datetime мог быть ниже
        # текущего, поэтому, если это значение меньше или равно допускаемого
        # времени между двумя кластерами, то эти кластеры можно объединить.
        df['time_difference'] = df.groupby(['name_id', 'object_id', 'date']) \
                                ['datetime'].shift(-1) - df['leaving_datetime']
        # bool маска для нахождения кластеров для объединения
        mask = (df['time_difference'] <=
                dt.timedelta(minutes=REPORT_BASE['MINS_BETWEEN_ATTENDS']))

        # так как может возникнуть целая последовательность кластеров для
        # объединения, во избежание излишних итераций, leaving_datetime для
        # всех строк, кроме последней (там гарантированно наибольшее значение),
        # очищается, чтобы затем применить метод bfill - заполнение последующих
        # пустых ячеек известным значением, но в направлении снизу вверх
        df.loc[mask, 'leaving_datetime'] = pd.NaT
        df['leaving_datetime'] = df['leaving_datetime'].bfill()

        # В завершение, снова удаление всех последующих кластеров, охватывающих
        # тот же период, что и текущий (как в начале алгоритма)
        df['next_ld_is_less'] = df.groupby(['name_id', 'object_id', 'date']) \
                                     ['leaving_datetime'].shift(-1) <= df[
                                     'leaving_datetime']
        df['odd_line'] = df['next_ld_is_less'].shift(1)
        df = df[~df['odd_line'].fillna(False)]
        return df

    @staticmethod
    def _set_count_and_duration(rep) -> pd.DataFrame:
        """Высчитать итоговое время и количество посещений"""
        # Длительность в каждой строке
        rep['duration'] = rep['leaving_datetime'] - rep['datetime']
        # Просто копия любого столбца, для подсчета строк (кол-ва посещений)
        rep['attends_count'] = rep['datetime']

        # Суммируем длительность, считаем кол-во, убираем дубликаты
        rep = rep.groupby(
            by=['name', 'name_id', 'object', 'object_id', 'date']) \
            .agg({'duration': 'sum', 'attends_count': 'count'}) \
            .reset_index() \
            .drop_duplicates(subset=['name_id', 'object_id', 'date']) \
            .loc[:, ['name', 'name_id', 'object', 'object_id',
                     'date', 'duration', 'attends_count']]
        return rep


class Report(ReportBase):
    """
    Данный объект является контейнером из различных DataFrame.
    При инициализации требуются DataFrame таблицы:
    stmts (statements) - (заявленные выходы по сотрудникам)
    journal - журнал закрепленных за каждым сотрудником subscriberID,
        для сопоставления координат и сотрудников
    schedules - данные о графике работы сотрудников, для определения порядка
        фильтрации служебных записок
    serves - служебные записки, применяются, когда не был зафиксирован выход
    clusters - кластеры нахождения в координатах
    date_from, date_to - изначальные даты запроса отчета
    conts - отображение отчета, False - длительность, True - кол-во посещений

    Объект формирует отчет при инициализации. Доступные атрибуты:
    report - отчет в вертикальном виде, может понадобиться для сравнения или
         формирования статистики посещений на основе этого отчета
    duplicated_attends - таблица с дублирующимися посещениями подопечных,
         нужна для отслеживания излишне проставленных выходов
    В виде @property:
        horizontal_report - отчет report, переведенный в горизонтальный вид
        xlsx - файл Bytes.IO, для скачивания отчета в формате xlsx.

    Также все изначальные таблицы доступны через "_".
    """
    def __init__(self,
                 date_from: Union[dt.date, str],
                 date_to: Union[dt.date, str],
                 division: Optional[Union[int, str]] = None,
                 name_ids: Optional[List[int]] = None,
                 object_ids: Optional[List[int]] = None,
                 counts: bool = False,
                 ):
        data = report_data_factory(date_from, date_to, division,
                                   name_ids, object_ids)
        self._date_from = dt.date.fromisoformat(str(date_from))
        self._date_to = dt.date.fromisoformat(str(date_to))

        self._stmts = data.get('_stmts')
        self._journal = data.get('_journal')
        self._schedules = data.get('_schedules')
        self._serves = data.get('_serves')
        self._clusters = data.get('_clusters')
        self._comment = data.get('_comment')
        self._frequency = data.get('_frequency')
        self._income = data.get('_income')
        self._no_payments = data.get('_no_payments')

        self._counts = counts

        # Эти параметры заполняются при выполнении метода _build_report
        self.duplicated_attends = None
        self.report = None

        # Построение отчета:
        self._build()

    def _build(self):
        """All the way that Report is being built by"""
        # Объединение таблицы заявленных выходов с таблицей журнала,
        # чтобы понять, в каком случае совмещать таблицу с кластерами
        # и создавать отчет, а в каком его нет.
        # А также - какой subscriberID использовать.
        statements_with_journal = self._create_stmts_with_journal_j_exist_vector()
        # Далее слияние этой таблицы с кластерами
        # (готовые данные о местонахождении сотрудников).
        stmts_jrnl_clstrs = pd.merge(
            statements_with_journal.set_index(['subscriberID', 'date']),
            self._clusters.set_index(['subscriberID', 'date']),
            left_index=True, right_index=True,
            suffixes=('_object', '_clusters')
        )
        # Вычисление дистанции между объектами и кластерами и фильтрация,
        # остаются только те строки, где дистанция в пределах RADIUS.
        stmts_jrnl_clstrs = self._calculate_distance_vectorized(
            stmts_jrnl_clstrs
        )
        # Оставшиеся кластеры нужно объединить в один, если зазор между ними
        # в пределах MINUTES_BETWEEN_CLUSTERS. Это сокращает кол-во строк
        # в отчете, а также показывает количество посещений одного адреса.
        stmts_jrnl_clstrs = self._consolidate_time_periods_vectorized(
            stmts_jrnl_clstrs
        )
        # Основная задача отчета - показать длительность и кол-во посещений:
        stmts_jrnl_clstrs = self._set_count_and_duration(stmts_jrnl_clstrs)
        # Отчет сопровождается таблицей дубликатов выходов. Это когда к одному
        # подопечному было зафиксировано более одного выхода.
        # Строки с самым большим кол-вом посещений всегда будут в начале.
        duplicated_attends = stmts_jrnl_clstrs \
            .groupby(by=['object', 'object_id', 'date']) \
            .agg({'duration': 'count', 'name': lambda x: ", ".join(list(x))}) \
            .reset_index() \
            .query("duration > 1") \
            .loc[:, ['object', 'date', 'duration', 'name']] \
            .sort_values(by=['duration', 'object', 'date'],
                         ascending=[False, True, True])

        # Относительно сформировавшегося отчета фильтруются служебные записки.
        # Здесь же состояние записки (int) расшифровывается ("С"/"ПРОВ")
        filtered_serves = self._filter_serves(stmts_jrnl_clstrs)

        # Далее нужно совместить statements с готовым отчетом, чтобы стали
        # доступны выходы, на которые нет сформированного отчета.
        # Это "Н/Б", служебка или отметка о больничном/отпуске/увол
        stmts_jrnl_clstrs = pd.merge(
            self._stmts,
            stmts_jrnl_clstrs,
            how='left',
            left_on=['name_id', 'object_id', 'date', 'name', 'object'],
            right_on=['name_id', 'object_id', 'date', 'name', 'object']
        )

        # Совмещение отчета со служебками.
        stmts_jrnl_clstrs = pd.merge(
            stmts_jrnl_clstrs,
            filtered_serves,
            how='left',
            left_on=['name_id', 'object_id', 'date'],
            right_on=['name_id', 'object_id', 'date']
        )
        # Готовый отчет в вертикальном виде
        self.duplicated_attends = duplicated_attends
        self.report = self._merge_into_one_column(stmts_jrnl_clstrs)
        return self

    def _create_stmts_with_journal_j_exist_vector(self) -> pd.DataFrame:
        """Объединение таблицы заявленных выходов с таблицей журнала,
        чтобы понять, в каком случае есть смысл запрашивать кластеры
        и создавать отчет, а в каком его нет.
        А также - какой subscriberID использовать."""
        stmts = pd.merge(self._stmts,
                         self._journal,
                         how='left', on='name_id')

        stmts['j_exist'] = ((stmts['date'] >= stmts['period_init']) &
                            (stmts['date'] <= stmts['period_end']))
        # все Больн./Отпуск/Увол. не нуждаются в отчете, им проставляем False
        stmts.loc[stmts['object_id'] == 1, 'j_exist'] = False

        # Фильтрация по наличию j_exist. Останутся все, где True,
        # либо первый (без разницы, какой он там)
        stmts = stmts[
            (stmts['j_exist']) |
            (~stmts.duplicated(subset=['name_id', 'object_id', 'date']))
        ]
        stmts = stmts.reset_index()[
            ['name_id', 'name', 'object_id', 'object', 'longitude', 'latitude',
             'date', 'statement', 'subscriberID', 'j_exist']
        ]

        return stmts

    def _create_stmts_with_journal_j_exist(self) -> pd.DataFrame:
        """Объединение таблицы заявленных выходов с таблицей журнала,
        чтобы понять, в каком случае есть смысл запрашивать кластеры
        и создавать отчет, а в каком его нет.
        А также - какой subscriberID использовать."""
        stmts = pd.merge(self._stmts,
                         self._journal,
                         how='left', on='name_id')
        stmts['j_exist'] = stmts.apply(
            lambda x: False if pd.isna(x['period_init'])
            else (x['period_init'] <= x['date'] <= x['period_end']),
            axis=1)
        # все Больн./Отпуск/Увол. не нуждаются в отчете, им проставляем False
        stmts.loc[stmts['object_id'] == 1, 'j_exist'] = False

        def check_if_any_j_exist(x: pd.DataFrame) -> pd.DataFrame:
            if any(x.j_exist):
                return x[x['j_exist']]
            return x.iloc[:1]

        # Фильтрация по наличию j_exist. Останутся все, где True,
        # либо первый (без разницы, какой он там)
        stmts = stmts.groupby(by=['name_id', 'object_id', 'date'],
                              as_index=False) \
            .apply(check_if_any_j_exist)

        stmts = stmts.reset_index()[
            ['name_id', 'name', 'object_id', 'object', 'longitude', 'latitude',
             'date', 'statement', 'subscriberID', 'j_exist']
        ]

        return stmts

    def _filter_serves(self, report: pd.DataFrame) -> pd.DataFrame:
        """Фильтрует служебные записки от дубликатов. Если по псу уже есть
        выход - значит служебку принимать нельзя. Кроме случаев, когда
        сотрудник является ванщиком. Для этого нужны schedules.
        Метод использует индексы для фильтрации служебок."""
        # Объединяем отчет и графики работы сотрудников (2 = "ванщик")
        with_schedules = pd.merge(
            report, self._schedules, on='name_id', how='left'
        )
        # Резервируем служебки ванщиков
        attendant_name_ids = self._schedules[self._schedules['schedule'] == 2]\
            .name_id.unique()
        reserved_serves = self._serves[self._serves.name_id
                                       .isin(attendant_name_ids)]

        # Исключаем все выходы с ванщиками (к ним фильтрация не относится)
        with_schedules = with_schedules[with_schedules['schedule'] != 2]

        with_schedules = with_schedules.set_index(['object_id', 'date'])
        serves = self._serves.set_index(['object_id', 'date'])
        # Теперь исключаем все служебки, где есть общий индекс с отчетом.
        # Это значит, что если выход к подопечному был в этот день - то
        # наличие второго выхода со служебкой исключено.
        serves = serves[
            serves.index.isin(serves.index.difference(with_schedules.index))
        ]
        # Объединяем зарезервированные служебки с отфильтрованными
        serves = pd.concat([serves.reset_index(), reserved_serves])
        # "Расшифровка" состояния служебки. 1 - одобрено. 3 - на проверке.
        serves['approval'] = serves['approval'].replace({1: "С", 3: "ПРОВ"})
        return serves \
            .drop_duplicates(subset=['name_id', 'object_id', 'date'])

    def _merge_into_one_column(self, df: pd.DataFrame) -> pd.DataFrame:
        """Совмещение выходов, служебок, отчетов в один столбец, применяя маски
        для фильтрации DataFrame.
        Маски позволяют быстро и эффективно выбрать определенные участки
        таблицы, чтобы, например, отредактировать их или на их основании
        задать значения для другого столбца (как здесь).
        """
        # По длительности посещений
        mask_duration = (pd.notna(df.duration))
        # По количеству посещений
        mask_attends_count = (pd.notna(df.attends_count))

        # Нет отчета, но есть есть служебка
        mask_no_duration_but_approval = (
                pd.isna(df.duration) & pd.notna(df.approval))
        # Нет отчета и нет служебки
        mask_no_duration_no_approval = (
                pd.isna(df.duration) & pd.isna(df.approval))
        # Ещё не наступившие даты или "БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ."
        mask_future_or_first_object = (
                (df.date > dt.date.today()) | (df.object_id == 1))

        # Какой вид отчета? Если нужно кол-во посещений - будут int с кол-вом.
        # Если нужна длительность - будет длительность (по умолчанию).
        if self._counts:
            df.loc[mask_attends_count, 'result'] = df \
                .loc[mask_attends_count, 'attends_count'] \
                .apply(lambda x: str(int(x)))
        else:
            df.loc[mask_duration, 'result'] = df \
                .loc[mask_duration, 'duration'] \
                .apply(lambda x: str(x)[-8:])
        df.loc[mask_no_duration_but_approval, 'result'] = df['approval']
        df.loc[mask_no_duration_no_approval, 'result'] = "Н/Б"
        df.loc[mask_future_or_first_object, 'result'] = df['statement']
        return df[["name", "name_id", "object", "object_id", "date", "result"]]

    @property
    def horizontal_report(self) -> pd.DataFrame:
        """Представление отчета в горизонтальном виде"""

        # Чтобы отображались все дни, независимо от наличия в эти дни
        # каких-либо данных, нужно составить "пустой" DF с этими датами
        # и совместить его с отчетом.

        # Даты:
        all_dates_range = [self._date_from + dt.timedelta(days=i) for i in
                           range((self._date_to - self._date_from).days + 1)]

        # "Пустой" отчет с датами:
        dates_df = pd.DataFrame(
            {'name_id': NaN, 'object_id': NaN, 'result': NaN,
             'date': all_dates_range})
        # Объединение:
        report = pd.concat([self.report, dates_df])

        # Перевод в горизонтальную таблицу:
        report = report.pivot(columns='date',
                              values='result',
                              index=["name", "name_id", "object", "object_id"])
        report = report.dropna(how='all').fillna('').reset_index()

        # перевод дат в str, name(object)_id - в int
        # т.к. эта таблица предназначена для перевода в json.
        report.columns = report.columns.astype(str)
        report['name_id'] = report['name_id'].astype(int)
        report['object_id'] = report['object_id'].astype(int)
        return report

    def xlsx(self, list_no_payments: list | None = None) -> io.BytesIO:
        """Переводит отчет в xlsx файл (объект BytesIO)"""
        document = io.BytesIO()
        writer = pd.ExcelWriter(document, engine='xlsxwriter')
        # writer = pd.ExcelWriter("/home/user/Desktop/get_xlsx.xlsx", engine='xlsxwriter')
        res = self.horizontal_report.drop(columns=['name_id', 'object_id'])
        new_columns = []
        for i in res.columns:
            try:
                new_columns.append(
                    dt.date.fromisoformat(str(i)).strftime("%d.%m"))
            except ValueError:
                new_columns.append(i)

        def index(l):
            result = []
            name = l[0]
            f = 0
            for i, v in enumerate(l):
                if v != name:
                    result.append(
                        (f, i - 1, name, res.iloc[i - 1].to_list()[1:]))
                    name = v
                    f = i
            result.append(
                (f, len(l) - 1, l[-1], res.iloc[len(l) - 1].to_list()[1:]))
            return result

        l = index(res.name.tolist())
        to_merge = []
        for i in l:
            to_merge.append((xlsxwriter.utility.xl_range(i[0] + 1, 0,
                                                         i[1] + 1, 0),
                             i[2], i[1] + 1))

        res.columns = new_columns
        res.to_excel(writer, index=False)
        book = writer.book  # доступ к xlsx книге
        book.get_worksheet_by_name('Sheet1').freeze_panes(1, 3)
        book.get_worksheet_by_name('Sheet1').set_column('A:A', 30, None)
        book.get_worksheet_by_name('Sheet1').set_column('B:B', 15, None)
        book.get_worksheet_by_name('Sheet1').set_column('C:C', 30, None)
        book.get_worksheet_by_name('Sheet1').set_column('D:D', 8, None)
        format_attend = book.add_format({'bg_color': '#cfe2f3'})
        format_absence = book.add_format({'bg_color': '#f88a8a'})
        format_na = book.add_format(
            {'bg_color': '#000000', 'font_color': '#ffffff'})
        format_b = book.add_format({'bg_color': '#b7e1cd'})
        format_o = book.add_format({'bg_color': '#ffe599'})
        format_u = book.add_format({'bg_color': '#aaaaaa'})
        format_days = book.add_format({'bg_color': '#b7b7b7'})
        format_rest = book.add_format({'bg_color': '#fce5cd'})
        format_check = book.add_format({'bg_color': '#ffa62c'})
        format_serve = book.add_format({'bg_color': '#c27ba0'})
        format_one = book.add_format({'bg_color': '#bbf5fc'})
        format_two = book.add_format({'bg_color': '#b269fa'})
        format_three = book.add_format({'bg_color': '#fa5c19'})
        no_payments = book.add_format({'bg_color': '#d8abc9',
                                       'align': 'left'})
        align_left = book.add_format({'align': 'left'})

        if list_no_payments:
            a = self.horizontal_report[['object', 'object_id']].reset_index()
            a['to_format'] = a['object_id']\
                .apply(lambda x: x in list_no_payments)
            for t in a.itertuples():
                item_format = no_payments if t.to_format else align_left
                book.get_worksheet_by_name('Sheet1')\
                    .write(t.Index+1, 2, t.object, item_format)

        # book.get_worksheet_by_name('Sheet1')\
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'text',
        #                          'criteria': 'containing',
        #                          'value': ':',
        #                          'format': format_attend})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"Н/Б"',
        #                          'format': format_absence})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"Н/А"',
        #                          'format': format_na})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"Б"',
        #                          'format': format_b})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"О"',
        #                          'format': format_o})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"У"',
        #                          'format': format_u})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"ПРОВ"',
        #                          'format': format_check})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '"С"',
        #                          'format': format_serve})
        book.get_worksheet_by_name('Sheet1') \
            .conditional_format('B1:B1000',
                                {'type': 'text',
                                 'criteria': 'containing',
                                 'value': ' БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ.',
                                 'format': format_rest})
        book.get_worksheet_by_name('Sheet1') \
            .conditional_format('B1:B1000',
                                {'type': 'text',
                                 'criteria': 'containing',
                                 'value': ' ПРОПУЩЕННЫЕ ДНИ',
                                 'format': format_days})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '1',
        #                          'format': format_one})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '==',
        #                          'value': '2',
        #                          'format': format_two})
        # book.get_worksheet_by_name('Sheet1') \
        #     .conditional_format('C1:ET1000',
        #                         {'type': 'cell',
        #                          'criteria': '>=',
        #                          'value': '3',
        #                          'format': format_three})

        align_rows_format = book.add_format({
            'align': 'center',
            'valign': 'vcenter'
        })
        for i in range(res.shape[0]):
            book.get_worksheet_by_name('Sheet1').set_row(
                i, 15, align_rows_format)

        merge_format = book.add_format({
            'align': 'center',
            'valign': 'vcenter',
        })
        merge_format.set_text_wrap()
        merge_format.set_bottom(1)
        rows_format = book.add_format({
            'align': 'center',
            'valign': 'vcenter',
        })
        rows_format.set_bottom(1)
        for i in to_merge:
            book.get_worksheet_by_name('Sheet1').set_row(i[2], 15,
                                                         rows_format)
            book.get_worksheet_by_name('Sheet1') \
                .merge_range(i[0], i[1], merge_format)

        book.get_worksheet_by_name('Sheet1').autofilter("A1:B1000")

        writer.save()
        document.seek(0)
        return document

    @property
    def as_json_dict(self) -> dict:
        """Для предоставления отчета через API, нужно перевести DataFrame в
        словарь и предоставить список столбцов."""
        h_report = self.horizontal_report.to_dict(orient='records')
        h_report_columns = self.horizontal_report.columns.tolist()
        dups = self.duplicated_attends
        dups['date'] = dups['date'].astype(str)
        dups = dups.to_dict(orient='records')
        return {'horizontal_report': {
                        'columns': h_report_columns,
                        'data': h_report
                    },
                'duplicated_attends': dups,
                'no_payments': self._no_payments}


class ReportWithAdditionalColumns(Report):
    def __init__(self,
                 date_from: Union[dt.date, str],
                 date_to: Union[dt.date, str],
                 division: Optional[Union[int, str]] = None,
                 name_ids: Optional[List[int]] = None,
                 object_ids: Optional[List[int]] = None,
                 counts: bool = False,
                 ):
        super().__init__(date_from, date_to, division, name_ids,
                         object_ids, counts)

    @property
    def horizontal_report(self) -> pd.DataFrame:
        """Представление отчета в горизонтальном виде"""

        # Чтобы отображались все дни, независимо от наличия в эти дни
        # каких-либо данных, нужно составить "пустой" DF с этими датами
        # и совместить его с отчетом.

        report = super().horizontal_report
        # здесь нужно запросить комментарии и частоту посещений,
        # совместить их с основной таблицей отчета, а затем -
        # вставить эти столбцы на нужные позиции в таблице.

        # главная задача - определить, где будут собираться эти данные.
        # если они собираются в этом классе, чтобы затем присоединиться, то это
        # нарушает принципы SOLID. Возможно, нужен также отдельный класс, который
        # добавляет в объект эти данные. но отсюда возникают дополнительные
        # factories, хотя суть всего - добавить пару столбцов.
        # но это единственно правильный вариант, который оставит код чистым.
        # пусть этот вопрос решает report_data_factory.
        comments_and_frequency = pd.merge(self._comment, self._frequency,
                                          on=['name_id', 'object_id'],
                                          how='outer')
        report = pd.merge(report, comments_and_frequency,
                          on=['name_id', 'object_id'], how='left')
        report = pd.merge(report, self._income, on=['object_id'], how='left')
        report.insert(2, 'comment', report.pop('comment'))
        report.insert(5, 'frequency', report.pop('frequency'))
        report.insert(6, 'income', report.pop('income'))
        report = report.fillna('')
        return report


class OneEmployeeReport(OneEmployeeReportDataGetter, ReportBase):
    """
    ФОРМИРОВАНИЕ ИНДИВИДУАЛЬНОГО ОТЧЕТА
    Понадобятся: clusters, statements+objects.

    Свойства объекта:
      clusters - остановки сотрудника, для отображения перемещений на карте
      report - подробный отчет с кол-вом, временем, длит. посещений
      analytics - подробный отчет о доступности телефона
      stats - ёмкий обобщенный отчет о доступности телефона
      recommended_for_checkout - результат анализа, о проблемах с локациями
    """
    def __init__(self,
                 name_id: int,
                 date: Union[dt.date, str],
                 division: Union[int, str]):
        super().__init__(name_id, date, division)
        self.report = self._build_report()
        self.analytics = self._location_analysis()

    def _build_report(self) -> Optional[pd.DataFrame]:
        stmts_clstrs = pd.merge(
            self._stmts.loc[self._stmts.object_id != 1].set_index(['date']),
            self.clusters.set_index(['date']),
            left_index=True, right_index=True,
            suffixes=('_object', '_clusters')
        )

        # Вычисление дистанции между объектами и кластерами и фильтрация,
        # остаются только те строки, где дистанция в пределах RADIUS.
        stmts_clstrs = self._calculate_distance_vectorized(stmts_clstrs)

        ###
        # Здесь возможно, что df останется пустым.
        # В таком случае отчета не будет.
        ###
        if not len(stmts_clstrs):
            return None

        # Оставшиеся кластеры нужно объединить в один, если зазор между ними
        # в пределах MINUTES_BETWEEN_CLUSTERS. Это сокращает кол-во строк
        # в отчете, а также показывает количество посещений одного адреса.
        # stmts_clstrs = stmts_clstrs \
        #     .groupby(by=['name_id', 'name', 'object_id', 'object', 'date'],
        #              group_keys=False) \
        #     .apply(lambda x: self._consolidate_time_periods(x))
        stmts_clstrs = self._consolidate_time_periods_vectorized(stmts_clstrs)

        if not len(stmts_clstrs):
            return None

        return self._detailed_report(stmts_clstrs)

    @staticmethod
    def _detailed_report(df: pd.DataFrame) -> pd.DataFrame:
        """Подробный отчет с отображением времени и длительности каждого
        посещения (каждое к каждому подопечному)"""
        df = df.sort_values(by=['name', 'object', 'date', 'datetime'])

        df['duration'] = df.leaving_datetime - df.datetime

        df['attend_number'] = df.groupby(
            by=['name', 'object', 'date']).duration.cumcount() + 1
        attends_sum = df.groupby(
            by=['name', 'object', 'date']
        ).count().duration
         
        df = df.set_index(['name', 'object', 'date'])
        df['attends_sum'] = attends_sum
        df = df.reset_index()
        return df

    def _location_analysis(self) -> pd.DataFrame:
        """Подробная таблица с анализом состояния телефона"""

        locs = self._locations.sort_values(by='requestDate')
        # locs.available - pd.Series из True и False, в зависимости от наличия
        locs['available'] = pd.notna(locs.locationDate)

        """
        Чтобы определить период активности/неактивности телефона, нужно 
        объединить их в группу. Здесь применяется векторный подход: сначала 
        добавляется столбец со смещением на одну строку, это позволяет 
        добавить ещё один столбец, где сравнивается текущая и следующая 
        строка, чтобы определить, было ли изменение значения. 
        Таким образом каждое изменение образует True (что является числом 1),
        а функция cumsum - это совокупная сумма всего столбца.
        Cumsum позволяет объединить каждый период в отдельную группу, чтобы 
        затем выделить начальное и конечное время периода. 
        Получается примерно так:
        available  available_shift  changing  cumsum
        True        pd.NaN          True        1
        True        True            False       1
        True        False           True        2
        False       False           False       2
        False       True            True        3
        ..........................................
        Ниже используются другие названия столбцов, и более сокращенный вариант
        написания! Cumsum в примере - это changing_of_available. 
        """

        locs['changing_of_available'] = (
                locs.available != locs.available.shift()
        ).cumsum()
        # Группировка по периодам, чтобы выделить начальное и конечное время.
        # Available здесь может казаться лишним, но он потребуется в дальнейшем
        # для группировки при формировании stats.
        min_and_max = locs.groupby(by=['changing_of_available', 'available'])\
            .agg(min=pd.NamedAgg(column='requestDate', aggfunc=min),
                 max=pd.NamedAgg(column='requestDate', aggfunc=max))\
            .reset_index()
        #
        min_and_max['duration'] = min_and_max['max'] - min_and_max['min']
        return min_and_max

    @property
    def stats(self) -> pd.DataFrame:
        """
        Ёмкая информация о доступности телефона:
          Сумма длительности доступного и недоступного состояний
          Кол-во переходов из одного состояния в другое
          Средняя длительность двух состояний
        """
        return self.analytics[
            self.analytics.duration > dt.timedelta(seconds=0)] \
            .groupby('available') \
            .agg({'duration': ['sum', 'count', 'mean']})

    @property
    def recommended_for_checkout(self) -> bool:
        """
        На основании таблицы stats принимается решение, нужно ли направить
        сотрудника для решения проблем с локациями.
        На проблемы указывает любой из двух вариантов:
         1. Период неактивности в процентом соотношении больше, чем активности
         и количество переходов между состояниями больше COUNT.
         2. Средняя длительность активности телефона меньше MINUTES.
        """
        if len(self.stats.reset_index()[['available']]) <= 1:
            return False
        stats = self.stats.droplevel(0, axis=1)
        stats.index = stats.index.astype(str)
        true_total_secs = stats.loc['True', 'sum'].total_seconds()
        false_total_secs = stats.loc['False', 'sum'].total_seconds()
        true_mean = stats.loc['True', 'mean']

        percentage = int((true_total_secs / false_total_secs) * 100)
        # Кол-во переходов между состояниями считается по активному состоянию
        count = stats.loc['True', 'count']
        mean_true_less_than_default = true_mean < dt.timedelta(
            minutes=STATS_CHECKOUT['MINUTES'])

        if (percentage < 100 and count > STATS_CHECKOUT['COUNT'])\
                or mean_true_less_than_default:
            return True
        return False

    def check_by_coordinates(self, lat: float, lon: float) -> bool:
        """
        Проверка нахождения сотрудника по координатам.
        Изначально для метода _calculate_distance требуются объединенные
        statements и clusters.
        Но так как мы проверяем единственные координаты - можно добавить к
        кластерам недостающие столбцы, таким образом имитируя объединение этих
        двух таблиц.
        Если хоть один кластер в пределах координат - выдаст True.
        """
        clusters = self.clusters.copy()

        coordinates_values = ('Служебка', 0, lon, lat)
        columns = ['object_name', 'object_id',
                   'longitude_object', 'latitude_object']
        clusters[columns] = coordinates_values

        clusters = clusters.rename(columns={
            'longitude': 'longitude_clusters',
            'latitude': 'latitude_clusters'
        })

        result = self._calculate_distance(clusters)

        if len(result):
            return True
        return False


if __name__ == "__main__":
    s = time.perf_counter()
    r = ReportWithAdditionalColumns('2023-11-01', '2023-11-30', "Коньково")
    # o = OneEmployeeReport(658, "2023-09-25", "Зеленоград")
    e = time.perf_counter()
    # a = r.as_json_dict
    print(e-s)
    pass
