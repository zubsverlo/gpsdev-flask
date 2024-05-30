import time
import pandas as pd
import datetime as dt
import numpy as np
from math import cos, asin, sqrt, pi
from numpy import NaN
from trajectory_report.config import REPORT_BASE, STATS_CHECKOUT
import io
import xlsxwriter
from trajectory_report.report.ConstructReport import (
    one_employee_report_data_factory,
)
from trajectory_report.report.ConstructReport import report_data_factory
from dataclasses import dataclass


def distance_vectorized(
    lat1: np.array, lon1: np.array, lat2: np.array, lon2: np.array
) -> np.array:
    p = np.pi / 180
    a = (
        0.5
        - np.cos((lat2 - lat1) * p) / 2
        + np.cos(lat1 * p)
        * np.cos(lat2 * p)
        * (1 - np.cos((lon2 - lon1) * p))
        / 2
    )
    return 12742 * np.arcsin(np.sqrt(a))


def calculate_distance(data_flow: pd.DataFrame) -> pd.DataFrame:
    """
    Высчитывание дистанции между объектами и кластерами локаций.
    Все кластеры, не входящие в заданный радиус, отбрасываются, так как
    здесь формируются отчеты о посещениях.
    """

    # numpy массивы с координатами для вычисления дистанции
    object_lat = np.array(data_flow.object_lat)
    object_lng = np.array(data_flow.object_lng)
    cluster_lat = np.array(data_flow.lat)
    cluster_lng = np.array(data_flow.lng)

    # По каждой строке высчитывается дистанция, в пределах радиуса - True.
    distances = distance_vectorized(
        object_lat, object_lng, cluster_lat, cluster_lng
    )
    distances = [i <= REPORT_BASE["RADIUS"] / 1000 for i in distances]
    data_flow["in_radius"] = distances
    data_flow = data_flow[data_flow["in_radius"]]
    return data_flow


def consolidate_time_periods(df):
    """Объединение кластеров по периодам, версия с векторизацией.
    Алгоритм ускорен в 500 раз по времени исполнения"""
    # сортировка данных - ключевой этап
    df = df.sort_values(["uid", "object_id", "date", "datetime"])

    # leaving_date последующей строки меньше, чем текущей.
    # Это означает, что последующий кластер охватывает период, который
    # уже включен в текущий кластер. Такие строки (последующий кластер)
    # не несут никакой ценности, поэтому мы их удаляем.
    df["next_ld_is_less"] = (
        df.groupby(["uid", "object_id", "date"])[
            "leaving_datetime"
        ].shift(-1)
        <= df["leaving_datetime"]
    )
    # Смещаем bool на строку ниже, добавляя столбец
    df["odd_line"] = df["next_ld_is_less"].shift(1)

    # Удаляем столбец. fillna(False), чтобы покрыть образовавшийся NaT в
    # первой строке при смещении bool вниз.
    df = df[~df["odd_line"].fillna(False)]

    # В случае, если в таблице нет ни одного зафиксированного выхода,
    # после "удаления" лишних строк останется пустой DF без Columns.
    # Чтобы не возникло key_error при дальнейшней обработке, на этом месте
    # вернём пустой df со всеми столбцами:
    if df.empty:
        return pd.DataFrame(
            columns=[
                "date",
                "uid",
                "name",
                "object_id",
                "object",
                "object_lng",
                "object_lat",
                "statement",
                "j_exist",
                "datetime",
                "lng",
                "lat",
                "leaving_datetime",
                "cluster",
                "in_radius",
                "next_ld_is_less",
                "odd_line",
                "time_difference",
            ]
        )

    # time_difference - это разница между leaving_datetime текущей строки
    # и datetime последующей. Так мы определяем, относить ли два кластера
    # к одному периоду, чтобы совместить их в один.
    # Выше мы удалили все строки, где leaving_datetime мог быть ниже
    # текущего, поэтому, если это значение меньше или равно допускаемого
    # времени между двумя кластерами, то эти кластеры можно объединить.
    df["time_difference"] = (
        df.groupby(["uid", "object_id", "date"])["datetime"].shift(-1)
        - df["leaving_datetime"]
    )
    # bool маска для нахождения кластеров для объединения
    mask = df["time_difference"] <= dt.timedelta(
        minutes=REPORT_BASE["MINS_BETWEEN_ATTENDS"]
    )

    # так как может возникнуть целая последовательность кластеров для
    # объединения, во избежание излишних итераций, leaving_datetime для
    # всех строк, кроме последней (там гарантированно наибольшее значение),
    # очищается, чтобы затем применить метод bfill - заполнение последующих
    # пустых ячеек известным значением, но в направлении снизу вверх
    df.loc[mask, "leaving_datetime"] = pd.NaT
    df["leaving_datetime"] = df["leaving_datetime"].bfill()

    # В завершение, снова удаление всех последующих кластеров, охватывающих
    # тот же период, что и текущий (как в начале алгоритма)
    df["next_ld_is_less"] = (
        df.groupby(["uid", "object_id", "date"])[
            "leaving_datetime"
        ].shift(-1)
        <= df["leaving_datetime"]
    )
    df["odd_line"] = df["next_ld_is_less"].shift(1)
    df = df[~df["odd_line"].fillna(False)]
    return df


class OneEmployeeReport():
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

    def __init__(self, name_id: int, date: dt.date | str, division: int | str):
        data = one_employee_report_data_factory(name_id, date, division)
        self._stmts = data['_stmts']
        self.clusters = data['clusters']
        self._locations = data['_locations']
        self.owntracks = data['owntracks']
        self.report = self._build_report()
        self.owntracks_location_analysis()

    def _build_report(self) -> pd.DataFrame | None:
        stmts_clstrs = pd.merge(
            self._stmts.loc[self._stmts.object_id != 1],
            self.clusters,
            on=['uid', 'date'],
        )

        # Вычисление дистанции между объектами и кластерами и фильтрация,
        # остаются только те строки, где дистанция в пределах RADIUS.
        stmts_clstrs = calculate_distance(stmts_clstrs)

        ###
        # Здесь возможно, что df останется пустым.
        # В таком случае отчета не будет.
        ###
        if stmts_clstrs.empty:
            return None

        # Оставшиеся кластеры нужно объединить в один, если зазор между ними
        # в пределах MINUTES_BETWEEN_CLUSTERS. Это сокращает кол-во строк
        # в отчете, а также показывает количество посещений одного адреса.
        stmts_clstrs = consolidate_time_periods(stmts_clstrs)

        if stmts_clstrs.empty:
            return None

        return self._detailed_report(stmts_clstrs)

    @staticmethod
    def _detailed_report(df: pd.DataFrame) -> pd.DataFrame:
        """Подробный отчет с отображением времени и длительности каждого
        посещения (каждое к каждому подопечному)"""
        df = df.sort_values(by=["name", "object", "date", "datetime"])

        df["duration"] = df.leaving_datetime - df.datetime

        df["attend_number"] = (
            df.groupby(by=["name", "object", "date"]).duration.cumcount() + 1
        )
        attends_sum = (
            df.groupby(by=["name", "object", "date"]).count().duration
        )

        df = df.set_index(["name", "object", "date"])
        df["attends_sum"] = attends_sum
        df = df.reset_index()
        return df

    def owntracks_location_analysis(self) -> None:
        """
        Анализ локаций и состояния телефона.
        Время первой локации, время последней локации,
        средний промежуток между нормальными локациями.
        А также df с локациями, промежуток между которыми больше 25 минут
        """
        locs = self._locations.copy()
        if not self.owntracks:
            locs = locs[pd.notna(locs["datetime"])]
            locs = locs.sort_values("datetime")
            locs = locs.drop_duplicates("datetime")
        locs["shifted"] = locs.datetime.shift(-1)
        locs["difference"] = locs.shifted - locs.datetime
        locs["long_period"] = locs.difference > dt.timedelta(minutes=25)

        self.offline_periods = locs[locs["long_period"]]

        self.start_time = locs["datetime"].min().to_pydatetime()
        self.end_time = locs["datetime"].max().to_pydatetime()
        self.locations_frequency = (
            locs[locs["long_period"] == False]["difference"]
            .mean()
            .to_pytimedelta()
        )
        pass

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

        coordinates_values = ("Служебка", 0, lon, lat)
        columns = [
            "object_name",
            "object_id",
            "object_lng",
            "object_lat",
        ]
        clusters[columns] = coordinates_values

        result = self._calculate_distance(clusters)

        if len(result):
            return True
        return False


@dataclass
class Report:
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

    date_from: dt.date | str
    date_to: dt.date | str
    division: int | str | None = None
    name_ids: list[int] | None = None
    object_ids: list[int] | None = None
    counts: bool = False

    def __post_init__(self):
        data = report_data_factory(
            date_from=self.date_from,
            date_to=self.date_to,
            division=self.division,
            name_ids=self.name_ids,
            object_ids=self.object_ids,
        )
        self._date_from = dt.date.fromisoformat(str(self.date_from))
        self._date_to = dt.date.fromisoformat(str(self.date_to))

        self._stmts = data.get("_stmts")
        self._serves = data.get("_serves")
        self._clusters = data.get("_clusters")
        self._employees = data.get("_employees")
        self._objects = data.get("_objects")
        self._comment = data.get("_comment")
        self._frequency = data.get("_frequency")
        self._staffers = data.get("_staffers")
        self._holiday_attend_needed = data.get("_holiday_attend_needed")
        # Эти параметры заполняются при выполнении метода _build_report
        self.duplicated_attends = None
        self.report = None
        # Построение отчета:
        self._build()

    def _build(self):
        """All the way that Report is being built by"""
        data_flow = pd.merge(
            self._stmts,
            self._objects[["object_id", "object_lat", "object_lng"]],
            how="left",
            on=["object_id"],
        )
        # Далее слияние этой таблицы с кластерами
        # (готовые данные о местонахождении сотрудников).
        data_flow = pd.merge(
            data_flow,
            self._clusters,
            on=["uid", "date"],
        )
        # Вычисление дистанции между объектами и кластерами и фильтрация,
        # остаются только те строки, где дистанция в пределах RADIUS.
        data_flow = self._calculate_distance(data_flow)
        # Оставшиеся кластеры нужно объединить в один, если зазор между ними
        # в пределах MINUTES_BETWEEN_CLUSTERS. Это сокращает кол-во строк
        # в отчете, а также показывает количество посещений одного адреса.
        data_flow = self._consolidate_time_periods(data_flow)

        # Основная задача отчета - показать длительность и кол-во посещений:
        data_flow = self._set_count_and_duration(data_flow)

        # Относительно сформировавшегося отчета фильтруются служебные записки.
        # Здесь же состояние записки (int) расшифровывается ("С"/"ПРОВ")
        filtered_serves = self._filter_serves(data_flow)

        # Далее нужно совместить statements с готовым отчетом, чтобы стали
        # доступны выходы, на которые нет сформированного отчета.
        # Это "Н/Б", служебка или отметка о больничном/отпуске/увол
        data_flow = pd.merge(
            self._stmts,
            data_flow,
            how="left",
            on=["uid", "object_id", "date"],
        )

        # Совмещение отчета со служебками.
        data_flow = pd.merge(
            data_flow,
            filtered_serves,
            how="left",
            on=["uid", "object_id", "date"],
        )
        # Готовый отчет в вертикальном виде
        self.report = self._merge_into_one_column(data_flow)
        # Объединение с именами сотрудников и подопечных
        self.report = pd.merge(
            self.report,
            self._employees[["uid", "name"]],
            how="left",
            on=["uid"],
        )
        self.report = pd.merge(
            self.report,
            self._objects[["object_id", "object"]],
            how="left",
            on=["object_id"],
        )

        # Отчет сопровождается таблицей дубликатов выходов. Это когда к одному
        # подопечному было зафиксировано более одного выхода.
        # Строки с самым большим кол-вом посещений всегда будут в начале.
        # Подтвержденная служебная записка приравнивается к выходу, поэтому
        # учитывается в дубликатах.
        self.duplicated_attends = (
            self.report.query("result != 'Н/Б'")
            .query("object_id != 1")
            .query("result != 'ПРОВ'")
            .groupby(by=["object", "object_id", "date"])
            .agg({"result": "count", "name": lambda x: ", ".join(list(x))})
            .reset_index()
            .query("result > 1")
            .loc[:, ["object", "date", "result", "name"]]
            .sort_values(
                by=["result", "object", "date"], ascending=[False, True, True]
            )
            .rename(columns={"result": "duration"})
        )

        # name_id сотрудников, у которых остались "Н/Б" на сегодня.
        # Из этих сотрудников формируется список на оповещение, в случае, если
        # локаций не было в течение определенного периода
        self.employees_to_notify = (
            pd.merge(
                self.report,
                self._employees[["uid", "empty_locations", "phone"]],
                how="left",
                on="uid",
            )
            .query("result == 'Н/Б'")
            .query("empty_locations == True")
            .query("date == @dt.date.today()")
            .drop_duplicates("uid")
            .loc[:, ["name", "phone"]]
        )
        self.report = self.report.rename(columns={'uid': 'name_id'})
        return self

    def _filter_serves(self, data: pd.DataFrame) -> pd.DataFrame:
        """Фильтрует служебные записки от дубликатов. Если по псу уже есть
        выход - значит служебку принимать нельзя. Кроме случаев, когда
        сотрудник является ванщиком. Для этого нужны schedules.
        Метод использует индексы для фильтрации служебок."""
        # Объединяем отчет и графики работы сотрудников (2 = "ванщик")
        with_schedules = pd.merge(
            data,
            self._employees[["uid", "schedule"]],
            on="uid",
            how="left",
        )
        # Резервируем служебки ванщиков
        attendant_name_ids = self._employees[
            self._employees["schedule"] == 2
        ].uid.unique()
        reserved_serves = self._serves[
            self._serves.uid.isin(attendant_name_ids)
        ]

        # Исключаем все выходы с ванщиками (к ним фильтрация не относится)
        with_schedules = with_schedules[with_schedules["schedule"] != 2]

        with_schedules = with_schedules.set_index(["object_id", "date"])
        serves = self._serves.set_index(["object_id", "date"])
        # Теперь исключаем все служебки, где есть общий индекс с отчетом.
        # Это значит, что если выход к подопечному был в этот день - то
        # наличие второго выхода со служебкой исключено.
        serves = serves[
            serves.index.isin(serves.index.difference(with_schedules.index))
        ]
        # Объединяем зарезервированные служебки с отфильтрованными
        serves = pd.concat([serves.reset_index(), reserved_serves])
        # "Расшифровка" состояния служебки. 1 - одобрено. 3 - на проверке.
        serves["approval"] = serves["approval"].replace({1: "С", 3: "ПРОВ"})
        return serves.drop_duplicates(subset=["uid", "object_id", "date"])

    def _merge_into_one_column(self, data: pd.DataFrame) -> pd.DataFrame:
        """Совмещение выходов, служебок, отчетов в один столбец, применяя маски
        для фильтрации DataFrame.
        Маски позволяют быстро и эффективно выбрать определенные участки
        таблицы, чтобы, например, отредактировать их или на их основании
        задать значения для другого столбца (как здесь).
        """
        # По длительности посещений
        mask_duration = pd.notna(data.duration)
        # По количеству посещений
        mask_attends_count = pd.notna(data.attends_count)

        # Нет отчета, но есть есть служебка
        mask_no_duration_but_approval = pd.isna(data.duration) & pd.notna(
            data.approval
        )
        # Нет отчета и нет служебки
        mask_no_duration_no_approval = pd.isna(data.duration) & pd.isna(
            data.approval
        )
        # Ещё не наступившие даты или "БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ."
        mask_future_or_first_object = (data.date > dt.date.today()) | (
            data.object_id == 1
        )

        # Какой вид отчета? Если нужно кол-во посещений - будут int с кол-вом.
        # Если нужна длительность - будет длительность (по умолчанию).
        if self.counts:
            data.loc[mask_attends_count, "result"] = data.loc[
                mask_attends_count, "attends_count"
            ].apply(lambda x: str(int(x)))
        else:
            data.loc[mask_duration, "result"] = data.loc[
                mask_duration, "duration"
            ].apply(lambda x: str(x)[-8:])
        data.loc[mask_no_duration_but_approval, "result"] = data["approval"]
        data.loc[mask_no_duration_no_approval, "result"] = "Н/Б"
        data.loc[mask_future_or_first_object, "result"] = data["statement"]
        return data[["uid", "object_id", "date", "result"]]

    @staticmethod
    def _calculate_distance(data: pd.DataFrame) -> pd.DataFrame:
        """
        Высчитывание дистанции между объектами и кластерами локаций.
        Все кластеры, не входящие в заданный радиус, отбрасываются, так как
        здесь формируются отчеты о посещениях.
        """

        def distance(
            lat1: np.array, lon1: np.array, lat2: np.array, lon2: np.array
        ) -> np.array:
            p = np.pi / 180
            a = (
                0.5
                - np.cos((lat2 - lat1) * p) / 2
                + np.cos(lat1 * p)
                * np.cos(lat2 * p)
                * (1 - np.cos((lon2 - lon1) * p))
                / 2
            )
            return 12742 * np.arcsin(np.sqrt(a))

        # numpy массивы с координатами для вычисления дистанции
        object_lat = np.array(data.object_lat)
        object_lng = np.array(data.object_lng)
        cluster_lat = np.array(data.lat)
        cluster_lng = np.array(data.lng)

        # По каждой строке высчитывается дистанция, в пределах радиуса - True.
        distances = distance(object_lat, object_lng, cluster_lat, cluster_lng)
        distances = [i <= REPORT_BASE["RADIUS"] / 1000 for i in distances]
        data["in_radius"] = distances
        stmts_jrnl_clstrs = data[data["in_radius"] == True]
        return stmts_jrnl_clstrs

    @staticmethod
    def _consolidate_time_periods(data: pd.DataFrame) -> pd.DataFrame:
        """Объединение кластеров по периодам, версия с векторизацией.
        Алгоритм ускорен в 500 раз по времени исполнения"""
        # сортировка данных - ключевой этап
        data = data.sort_values(["uid", "object_id", "date", "datetime"])

        # leaving_date последующей строки меньше, чем текущей.
        # Это означает, что последующий кластер охватывает период, который
        # уже включен в текущий кластер. Такие строки (последующий кластер)
        # не несут никакой ценности, поэтому мы их удаляем.
        data["next_ld_is_less"] = (
            data.groupby(["uid", "object_id", "date"])[
                "leaving_datetime"
            ].shift(-1)
            <= data["leaving_datetime"]
        )
        # Смещаем bool на строку ниже, добавляя столбец
        data["odd_line"] = data["next_ld_is_less"].shift(1)

        # Удаляем столбец. fillna(False), чтобы покрыть образовавшийся NaT в
        # первой строке при смещении bool вниз.
        data = data[~data["odd_line"].fillna(False)]

        # В случае, если в таблице нет ни одного зафиксированного выхода,
        # после "удаления" лишних строк останется пустой DF без Columns.
        # Чтобы не возникло key_error при дальнейшней обработке, на этом месте
        # вернём пустой df со всеми столбцами:
        if data.empty:
            return pd.DataFrame(
                columns=[
                    "date",
                    "uid",
                    "object_id",
                    "object_lng",
                    "object_lat",
                    "statement",
                    "datetime",
                    "lng",
                    "lat",
                    "leaving_datetime",
                    "cluster",
                    "in_radius",
                    "next_ld_is_less",
                    "odd_line",
                    "time_difference",
                ]
            )

        # time_difference - это разница между leaving_datetime текущей строки
        # и datetime последующей. Так мы определяем, относить ли два кластера
        # к одному периоду, чтобы совместить их в один.
        # Выше мы удалили все строки, где leaving_datetime мог быть ниже
        # текущего, поэтому, если это значение меньше или равно допускаемого
        # времени между двумя кластерами, то эти кластеры можно объединить.
        data["time_difference"] = (
            data.groupby(["uid", "object_id", "date"])["datetime"].shift(
                -1
            )
            - data["leaving_datetime"]
        )
        # bool маска для нахождения кластеров для объединения
        mask = data["time_difference"] <= dt.timedelta(
            minutes=REPORT_BASE["MINS_BETWEEN_ATTENDS"]
        )

        # так как может возникнуть целая последовательность кластеров для
        # объединения, во избежание излишних итераций, leaving_datetime для
        # всех строк, кроме последней (там гарантированно наибольшее значение),
        # очищается, чтобы затем применить метод bfill - заполнение последующих
        # пустых ячеек известным значением, но в направлении снизу вверх
        data.loc[mask, "leaving_datetime"] = pd.NaT
        data["leaving_datetime"] = data["leaving_datetime"].bfill()

        # В завершение, снова удаление всех последующих кластеров, охватывающих
        # тот же период, что и текущий (как в начале алгоритма)
        data["next_ld_is_less"] = (
            data.groupby(["uid", "object_id", "date"])[
                "leaving_datetime"
            ].shift(-1)
            <= data["leaving_datetime"]
        )
        data["odd_line"] = data["next_ld_is_less"].shift(1)
        data = data[~data["odd_line"].fillna(False)]
        return data

    @staticmethod
    def _set_count_and_duration(data: pd.DataFrame) -> pd.DataFrame:
        """Высчитать итоговое время и количество посещений"""
        # Длительность в каждой строке
        data["duration"] = data["leaving_datetime"] - data["datetime"]
        # Просто копия любого столбца, для подсчета строк (кол-ва посещений)
        data["attends_count"] = data["datetime"]

        # Суммируем длительность, считаем кол-во, убираем дубликаты
        data = (
            data.groupby(by=["uid", "object_id", "date"])
            .agg({"duration": "sum", "attends_count": "count"})
            .reset_index()
            .drop_duplicates(subset=["uid", "object_id", "date"])
            .loc[
                :,
                ["uid", "object_id", "date", "duration", "attends_count"],
            ]
        )
        return data

    @property
    def horizontal_report(self) -> pd.DataFrame:
        """Представление отчета в горизонтальном виде"""

        # Чтобы отображались все дни, независимо от наличия в эти дни
        # каких-либо данных, нужно составить "пустой" DF с этими датами
        # и совместить его с отчетом.

        # Даты:
        all_dates_range = [
            self._date_from + dt.timedelta(days=i)
            for i in range((self._date_to - self._date_from).days + 1)
        ]

        # "Пустой" отчет с датами:
        dates_df = pd.DataFrame(
            {
                "name_id": NaN,
                "object_id": NaN,
                "result": NaN,
                "date": all_dates_range,
            }
        )
        # Объединение:
        report = pd.concat([self.report, dates_df])

        # Перевод в горизонтальную таблицу:
        report = report.pivot(
            columns="date",
            values="result",
            index=["name", "name_id", "object", "object_id"],
        )
        report = report.dropna(how="all").fillna("").reset_index()

        # перевод дат в str, name(object)_id - в int
        # т.к. эта таблица предназначена для перевода в json.
        report.columns = report.columns.astype(str)
        report["name_id"] = report["name_id"].astype(int)
        report["object_id"] = report["object_id"].astype(int)

        # Дополнительные столбцы к отчету: комментарии, частота посещ., доход
        comment_and_frequency = pd.merge(
            self._comment,
            self._frequency,
            on=["name_id", "object_id"],
            how="outer",
        )
        report = pd.merge(
            report,
            comment_and_frequency,
            on=["name_id", "object_id"],
            how="left",
        )
        report = pd.merge(
            report,
            self._objects[["object_id", "income"]],
            on=["object_id"],
            how="left",
        )
        # Перемещение столбцов в правильный порядок
        report.insert(2, "comment", report.pop("comment"))
        report.insert(5, "frequency", report.pop("frequency"))
        report.insert(6, "income", report.pop("income"))
        report = report.fillna("")
        return report

    def xlsx(self, list_no_payments: list[int] | None = None) -> io.BytesIO:
        """Переводит отчет в xlsx файл (объект BytesIO)"""
        document = io.BytesIO()
        writer = pd.ExcelWriter(document, engine="xlsxwriter")
        # writer = pd.ExcelWriter("/home/user/Desktop/get_xlsx.xlsx", engine='xlsxwriter')
        res = self.horizontal_report.drop(columns=["name_id", "object_id"])
        new_columns = []
        for i in res.columns:
            try:
                new_columns.append(
                    dt.date.fromisoformat(str(i)).strftime("%d.%m")
                )
            except ValueError:
                new_columns.append(i)

        def index(l):
            result = []
            name = l[0]
            f = 0
            for i, v in enumerate(l):
                if v != name:
                    result.append(
                        (f, i - 1, name, res.iloc[i - 1].to_list()[1:])
                    )
                    name = v
                    f = i
            result.append(
                (f, len(l) - 1, l[-1], res.iloc[len(l) - 1].to_list()[1:])
            )
            return result

        l = index(res.name.tolist())
        to_merge = []
        for i in l:
            to_merge.append(
                (
                    xlsxwriter.utility.xl_range(i[0] + 1, 0, i[1] + 1, 0),
                    i[2],
                    i[1] + 1,
                )
            )

        res.columns = new_columns
        res.to_excel(writer, index=False)
        book = writer.book  # доступ к xlsx книге
        book.get_worksheet_by_name("Sheet1").freeze_panes(1, 3)
        book.get_worksheet_by_name("Sheet1").set_column("A:A", 30, None)
        book.get_worksheet_by_name("Sheet1").set_column("B:B", 15, None)
        book.get_worksheet_by_name("Sheet1").set_column("C:C", 30, None)
        book.get_worksheet_by_name("Sheet1").set_column("D:D", 8, None)
        format_attend = book.add_format({"bg_color": "#cfe2f3"})
        format_absence = book.add_format({"bg_color": "#f88a8a"})
        format_na = book.add_format(
            {"bg_color": "#000000", "font_color": "#ffffff"}
        )
        format_b = book.add_format({"bg_color": "#b7e1cd"})
        format_o = book.add_format({"bg_color": "#ffe599"})
        format_u = book.add_format({"bg_color": "#aaaaaa"})
        format_days = book.add_format({"bg_color": "#b7b7b7"})
        format_rest = book.add_format({"bg_color": "#fce5cd"})
        format_check = book.add_format({"bg_color": "#ffa62c"})
        format_serve = book.add_format({"bg_color": "#c27ba0"})
        format_one = book.add_format({"bg_color": "#bbf5fc"})
        format_two = book.add_format({"bg_color": "#b269fa"})
        format_three = book.add_format({"bg_color": "#fa5c19"})
        no_payments = book.add_format({"bg_color": "#d8abc9", "align": "left"})
        align_left = book.add_format({"align": "left"})
        staffers = book.add_format({"bg_color": "#c7d1f6"})

        if list_no_payments:
            a = self.horizontal_report[["object", "object_id"]].reset_index()
            a["to_format"] = a["object_id"].apply(
                lambda x: x in list_no_payments
            )
            for t in a.itertuples():
                item_format = no_payments if t.to_format else align_left
                book.get_worksheet_by_name("Sheet1").write(
                    t.Index + 1, 2, t.object, item_format
                )

        staffers_format_set = set()
        if self._staffers:
            a = self.horizontal_report[["name", "name_id"]].reset_index()
            a["to_format"] = a["name_id"].apply(lambda x: x in self._staffers)
            for t in a.itertuples():
                if t.to_format:
                    staffers_format_set.add(t.name)
                item_format = staffers if t.to_format else None
                book.get_worksheet_by_name("Sheet1").write(
                    t.Index + 1, 0, t.name, item_format
                )

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
        book.get_worksheet_by_name("Sheet1").conditional_format(
            "B1:B1000",
            {
                "type": "text",
                "criteria": "containing",
                "value": " БОЛЬНИЧНЫЙ/ОТПУСК/УВОЛ.",
                "format": format_rest,
            },
        )
        book.get_worksheet_by_name("Sheet1").conditional_format(
            "B1:B1000",
            {
                "type": "text",
                "criteria": "containing",
                "value": " ПРОПУЩЕННЫЕ ДНИ",
                "format": format_days,
            },
        )
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

        align_rows_format = book.add_format(
            {"align": "center", "valign": "vcenter"}
        )
        for i in range(res.shape[0]):
            book.get_worksheet_by_name("Sheet1").set_row(
                i, 15, align_rows_format
            )

        rows_format = book.add_format(
            {
                "align": "center",
                "valign": "vcenter",
            }
        )
        rows_format.set_bottom(1)

        def merge_format_getter(staffers=False):
            format_ = book.add_format(
                {
                    "align": "center",
                    "valign": "vcenter",
                }
            )
            format_.set_text_wrap()
            format_.set_bottom(1)
            if staffers:
                format_.set_bg_color("#c7d1f6")
            return format_

        for i in to_merge:
            book.get_worksheet_by_name("Sheet1").set_row(i[2], 15, rows_format)
            if i[1] in staffers_format_set:
                book.get_worksheet_by_name("Sheet1").merge_range(
                    i[0], i[1], merge_format_getter(staffers=True)
                )
                continue
            book.get_worksheet_by_name("Sheet1").merge_range(
                i[0], i[1], merge_format_getter()
            )

        book.get_worksheet_by_name("Sheet1").autofilter("A1:B1000")

        writer.save()
        document.seek(0)
        return document

    @property
    def as_json_dict(self) -> dict:
        """Для предоставления отчета через API, нужно перевести DataFrame в
        словарь и предоставить список столбцов."""
        h_report = self.horizontal_report.to_dict(orient="records")
        h_report_columns = self.horizontal_report.columns.tolist()
        dups = self.duplicated_attends
        dups["date"] = dups["date"].astype(str)
        dups = dups.to_dict(orient="records")
        no_payments = self._objects.query(
            "no_payments == True"
        ).object_id.tolist()
        staffers = self._employees.query("staffer == True").uid.tolist()
        return {
            "horizontal_report": {
                "columns": h_report_columns,
                "data": h_report,
            },
            "duplicated_attends": dups,
            "no_payments": no_payments,
            "staffers": staffers,
            "holiday_attend_needed": self._holiday_attend_needed,
        }


if __name__ == "__main__":
    s = time.perf_counter()
    # r = Report('2024-02-01', '2024-05-31', "Коньково")
    # o = OneEmployeeReport(1293, "2024-05-23", "Коньково")
    # o = OneEmployeeReport(898, "2024-02-02", "Коньково")
    o = OneEmployeeReport(1187, "2024-05-29", "ПВТ1")
    e = time.perf_counter()
    # a = r.as_json_dict
    print(e - s)
    pass
