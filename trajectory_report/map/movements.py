import folium
from folium.plugins import AntPath, Geocoder, Search
from branca.element import Figure
import math
import skmob
from skmob.preprocessing import clustering
from numpy import median
import pandas as pd
from trajectory_report.report.Report import OneEmployeeReport, Report
from typing import Union, Optional, List
import datetime as dt
from numpy import isnan
from geopandas import GeoDataFrame, GeoSeries
from gpsdev_flask import main_logger


"""

  Возможно, неплохо сформировать отдельную карту со всеми координатами на 
  карте, без объединения в кластеры, для наглядности.
  
"""


class MapsBase:
    """
    Базовый класс для формирования карты. Метод _tie_clusters позволяет
    раскинуть точки на карте, которые могут перекрывать друг друга.
    Это происходит при помощи определения всех точек в кластеры (в пределах
    очень небольшого радиуса), а затем - группировке точек по кластерам.
    Потом в пределах кластера точкам задаются новые координаты.
    """

    @staticmethod
    def _spiderfy_shape_positions(count: int, center_pt: tuple) -> list:
        """
        Если координаты объектов на карте совпали или могут перекрывать друг
        друга, то их нужно раздвинуть немного в сторону.
        Эта функция принимает одну координату и количество точек. Затем выдает
        список из координат, находящихся на небольшой отдаленности друг от
        друга, так чтобы не перекрыть друг друга.
        """
        angle_step = math.pi * 2 / count
        circle_start_angle = 85
        leg_length = 0.00016
        if 4 < count <= 8:
            leg_length = leg_length * 1.8
        elif 8 < count <= 12:
            leg_length = leg_length * 2.2
        elif count > 12:
            leg_length = leg_length * 2.5

        res = []

        for i in range(count):
            angle = circle_start_angle + i * angle_step
            res.append(
                (
                    # latitude
                    center_pt[0] + leg_length * math.sin(angle),
                    # longitude
                    center_pt[1] + leg_length * math.cos(angle),
                )
            )

        return res

    def _tie_clusters(self, x):
        length = len(x)
        if length == 1:
            return x
        coord = (x.lat.iloc[0], x.lng.iloc[0])
        new_coords = self._spiderfy_shape_positions(length, coord)
        new_coords = list(zip(*new_coords))
        x.lat = new_coords[0]
        x.lng = new_coords[1]
        return x

    def _concatenate_points(self, df) -> pd.DataFrame:
        df = skmob.TrajDataFrame(
            df, latitude="lat", longitude="lng"
        )
        df = clustering.cluster(df, cluster_radius_km=0.005)
        df = df.groupby(by="cluster", group_keys=False).apply(
            lambda x: self._tie_clusters(x)
        )
        return pd.DataFrame(df)

    @property
    def map_html(self):
        return self.map._repr_html_()


class MapMovements(OneEmployeeReport, MapsBase):
    """
    Передвижения одного сотрудника за один день.
    Аттрибуты:
    _objects_points - точки объектов (подопечных) на карте
    _clusters_points - кластеры
    map - объект Folium
    map_html - код html для отображения карты
    """

    def __init__(
        self,
        name_id: int,
        date: Union[dt.date, str],
        division: Union[int, str],
    ):
        super().__init__(name_id, date, division)

        self._objects = self._stmts.drop_duplicates("object_id").loc[
            :, ["object", "object_lng", "object_lat", "address"]
        ]
        self._objects = self._objects.rename(
            columns={'object_lng': 'lng', 'object_lat': 'lat'}
        )

        median_lat = median(self.clusters.lat)
        median_lng = median(self.clusters.lng)

        # Атрибут для уведомления, когда карта есть, но перемещений нет
        self.no_movements = True if not len(self.clusters) else False

        self._median_coordinates = [
            median_lat if not isnan(median_lat) else 55.7522,
            median_lng if not isnan(median_lng) else 37.6156,
        ]

        points = pd.concat([self._clusters_points, self._objects_points])
        # Для формирования TDF колонка datetime должна быть заполнена.
        # В _objects_points не может быть datetime.
        # Но в данном случае не имеет значения, каким временем, поэтому
        # просто заполним случайным оразом
        points["datetime"] = points["datetime"].ffill()
        self._points = self._concatenate_points(points)

        self.map = self._create_map()

    @property
    def _objects_points(self) -> pd.DataFrame:
        # Объекты
        objects = self._objects
        objects["icon"] = [
            folium.features.Icon(icon="user", prefix="fa", color="black")
            for _ in range(len(objects))
        ]
        objects["tooltip"] = objects["object"]
        objects["popup"] = objects["object"] + "\n" + objects["address"]
        return objects

    @property
    def _clusters_points(self) -> pd.DataFrame:
        clusters = self.clusters
        clusters["popup"] = clusters["leaving_datetime"] - clusters["datetime"]

        clusters = clusters.sort_values(by="datetime")

        # Первая и последняя иконка - это начало и конец пути. Остальные -
        # "пауза".
        icons = [
            folium.features.Icon(icon="pause", prefix="fa", color="orange")
            for _ in range(len(clusters))
        ]
        if icons:
            icons[0] = folium.features.Icon(
                icon="play", prefix="fa", color="green"
            )
            icons[-1] = folium.features.Icon(
                icon="stop", prefix="fa", color="red"
            )
        # Добавление иконок к кластерам
        clusters["icon"] = icons
        # Информация о времени (при наведении курсора)
        clusters["tooltip"] = clusters["datetime"].apply(
            lambda x: x.strftime("%H:%M")
        )
        # Подробная информация (при нажатии на точку)
        clusters["popup"] = clusters.apply(
            lambda x: (
                "Время:\n"
                f"{x['tooltip']}\n"
                "Длительность:\n"
                f"{str(x['popup'])[-8:]}"
            ),
            axis=1,
        )
        clusters = clusters[
            ["datetime", "lat", "lng", "icon", "popup", "tooltip"]
        ]
        return clusters

    def _create_map(self):
        # СОЗДАНИЕ КАРТЫ
        map = folium.Map(self._median_coordinates, zoom_start=11)
        e = Figure(height="100%")  # todo: поменять на "100%"
        e.add_child(map)

        # Накидываем на карту все образовавшиеся точки.

        for row in self._points.itertuples():
            folium.Marker(
                (row.lat, row.lng),
                popup=row.popup,
                tooltip=row.tooltip,
                icon=row.icon,
            ).add_to(map)

        # Antpath отображает маршрут через анимацию ползающих "муравьев"
        path = self.clusters.sort_values(by="datetime")
        if len(path):
            AntPath(
                [i for i in zip(path.lat, path.lng)],
                delay=1000,
                weight=6,
                dash_array=[9, 100],
                color="#000000",
                pulseColor="#FFFFFF",
                hardwareAcceleration=True,
                opacity=0.6,
            ).add_to(map)
        return map

    @property
    def as_json_dict(self) -> dict:
        report = None
        analytics = None
        if self.report is not None:
            report = self.report[
                [
                    "object",
                    "attend_number",
                    "datetime",
                    "duration",
                    "attends_sum",
                ]
            ]
            report["duration"] = report.duration.apply(lambda x: str(x)[-8:])
            report["datetime"] = report.datetime.apply(lambda x: str(x)[-8:])
            report = report.rename(columns={"datetime": "time"})
            report = report.to_dict(orient="records")
        if self.offline_periods is not None:
            analytics = self.offline_periods[
                ["datetime", "shifted", "difference"]
            ]
            analytics["start"] = analytics["datetime"].apply(
                lambda x: str(x)[-8:]
            )
            analytics["end"] = analytics["shifted"].apply(
                lambda x: str(x)[-8:]
            )
            analytics["duration"] = analytics["difference"].apply(
                lambda x: str(x)[-8:]
            )
            analytics = analytics[["start", "end", "duration"]]
            analytics = analytics.to_dict(orient="records")

        resp = {
            "map": self.map_html,
            # 'recommended_for_checkout': self.recommended_for_checkout,
            "no_movements": self.no_movements,
        }
        if report:
            resp["report"] = report
        if analytics:
            resp["analytics"] = analytics
        if self.start_time:
            resp["start_time"] = str(self.start_time)[-8:]
        if self.end_time:
            resp["end_time"] = str(self.end_time)[-8:]
        if self.locations_frequency:
            resp["locations_frequency"] = (
                self.locations_frequency.__str__().split(".")[0]
            )
        return resp


class MapBindings(Report, MapsBase):
    """
    Карта привязок подопечных к сотрудникам.
    Каждый сотрудник - это слой на карте (по умолчанию отключен), который
    отображает на карте подопечных.
    Помогает увидеть, в каком районе у сотрудника находятся подопечные.
    """

    def __init__(
        self,
        date_from: Union[dt.date, str],
        date_to: Union[dt.date, str],
        division: Optional[Union[int, str]] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
        **kwargs,
    ):
        super().__init__(
            date_from, date_to, division, name_ids, object_ids, **kwargs
        )

        self.points = self._points_from_stmts()

        self.map = folium.Map(
            location=[55.50703, 37.58213],
            zoom_start=12,
            tiles="cartodbpositron",
        )
        e = Figure(height="100%")  # todo: поменять на "100%"
        e.add_child(self.map)
        self._create_map()

    def save_map(self):
        self.map.save("/home/user/Desktop/map.html")

    def _create_map(self):
        self.points.groupby("name").apply(lambda x: self._make_layer(x))
        self.map.add_child(folium.map.LayerControl())

    def _make_layer(self, x):
        self.map.add_child(
            folium.plugins.MarkerCluster(
                disableClusteringAtZoom=True,
                show=False,
                name=x.name,
                locations=[i for i in zip(x.lat.tolist(), x.lng.tolist())],
                popups=x.object.tolist(),
            )
        )

    def _points_from_stmts(self):
        """Из stmts нужно образуем таблицу с привязками сотрудников к
        объектам, сами объекты располагаем таким образом, чтобы они
        не накладывались друг на друга, если отображать на карте объекты
        всех сотрудников сразу."""

        # Object_id 1 без локаций, это служебный объект (отпуск, больнич, увол)
        # Даты нас не интересуют, только связка сотрудник-псу
        points = self._stmts.loc[self._stmts.object_id != 1].drop_duplicates(
            ["name", "object"]
        )

        # Для кластеризации необходим столбец со временем, сгенерируем его
        # сами, т.к. подопечные имеют только координаты.
        points["datetime"] = points.date.apply(
            lambda x: dt.datetime.fromisoformat(str(x))
        )

        # ПРОБЛЕМА: при раскидывании близлежащих точек один объект может
        # оказаться с несколькими разными координатами.
        # Решением будет изъять все уникальные объекты, раскинуть их координаты
        # и заменить эти координаты новыми, воссоединив с основным DataFrame.

        objects = self._concatenate_points(
            points.drop_duplicates(["object_id"])
        ).set_index("object_id")[["lng", "lat"]]
        points = points.set_index("object_id")
        points = pd.merge(points, objects, left_index=True, right_index=True)

        return points.reset_index()


class MapObjectsOnly(Report, MapsBase):
    def __init__(
        self,
        date_from: Union[dt.date, str],
        date_to: Union[dt.date, str],
        division: Optional[Union[int, str]] = None,
        name_ids: Optional[List[int]] = None,
        object_ids: Optional[List[int]] = None,
        **kwargs,
    ):
        super().__init__(
            date_from,
            date_to,
            division,
            name_ids,
            object_ids,
            objects_with_address=True,
            **kwargs,
        )

        self._objects = (
            self._stmts.drop_duplicates("object_id")
            .loc[self._stmts.object_id != 1]
            .loc[:, ["object", "lng", "lat", "address"]]
        )

        self._median_coordinates = [55.7522, 37.6156]
        points = self._objects.copy()
        points["datetime"] = dt.datetime.now().isoformat(timespec="minutes")
        self._points = self._concatenate_points(points)
        self.geojson = GeoDataFrame(
            self._points.loc[:, ["object", "address"]],
            geometry=GeoSeries.from_xy(x=self._points.lng, y=self._points.lat),
        ).to_json()
        self.map = self._create_map()

        pass

    @property
    def _objects_points(self) -> pd.DataFrame:
        # Объекты
        objects = self._objects
        objects["icon"] = [
            folium.features.Icon(icon="user", prefix="fa", color="black")
            for _ in range(len(objects))
        ]
        objects["tooltip"] = objects["object"]
        objects["popup"] = objects["object"] + "\n" + objects["address"]
        return objects

    def _create_map(self):
        # СОЗДАНИЕ КАРТЫ
        map = folium.Map(self._median_coordinates, zoom_start=11)
        e = Figure(height="100%")  # todo: поменять на "100%"
        e.add_child(map)
        icon = folium.features.Icon(icon="user", prefix="fa", color="black")
        Geocoder(placeholder="Найти адрес").add_to(map)
        object_layer = folium.GeoJson(
            self.geojson,
            show=False,
            overlay=False,
            marker=folium.Marker(icon=icon),
            popup=folium.GeoJsonPopup(["object", "address"], labels=False),
            tooltip=folium.GeoJsonTooltip(["object"], labels=False),
        ).add_to(map)
        Search(
            object_layer,
            search_label="object",
            placeholder="Поиск по ПСУ",
            collapsed=True,
            auto_collapse=True,
        ).add_to(map)
        return map


if __name__ == "__main__":
    divisions = ["ПВТ1", "ПНИ12,30"]
    start_date, end_date = "2023-01-01", "2023-01-23"
    m = MapMovements(898, "2024-02-02", "Коньково").as_json_dict
    # for division in divisions:
        # m = MapBindings(start_date, end_date, division)
        # m.map.save(f'{division}_{start_date}-{end_date}_закрепления.html')
        # m = MapObjectsOnly(start_date, end_date, division)
        # m.map.save(f"{division}_{start_date}-{end_date}_подопечные.html")
    pass
