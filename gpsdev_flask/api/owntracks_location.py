from flask import Blueprint
from gpsdev_flask import db_session, redis_session
from gpsdev_flask.models import OwnTracksLocation
from sqlalchemy import select, update, delete
from flask import jsonify, request, g, current_app
from marshmallow import ValidationError, EXCLUDE
from gpsdev_flask.api.error_responses import (
    not_found_404,
    validation_error_422,
    not_allowed_403,
)
from gpsdev_flask.ma_schemas import OwnTracksLocationSchema
import folium
from folium.plugins import AntPath, Geocoder, Search
from branca.element import Figure
import pandas as pd
from geopandas import GeoDataFrame, GeoSeries
import pandas as pd
from skmob import TrajDataFrame
from skmob.preprocessing import detection, clustering
from trajectory_report.config import (
    STAY_LOCATIONS_CONFIG_MTS,
    CLUSTERS_CONFIG_MTS,
)
from jose import jwt, JWTError
import datetime as dt


owntracks_location = Blueprint("owntracks_location", __name__)
# openssl -hex 32
SECRET_KEY = "8390b4e9ef9db9e62d1af3f46b9036f50adbce14abe4c907a103f2d2579ca321"
ALGORITHM = "HS256"
jwt.encode({"sub": "ilia"}, algorithm=ALGORITHM, key=SECRET_KEY)
"eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJpbGlhIn0.tQj9WY06lxDSncMnw-UbzilrtBuclwx7zi09OgtxTGU"


def create_map(points: pd.DataFrame, stay_locations=True):
    columns = ["datetime", "leaving_datetime"]
    if not stay_locations:
        columns = ["datetime"]
    map = folium.Map([35.3369267, 33.2673924], zoom_start=20)
    e = Figure(height="100%")  # todo: поменять на "100%"
    e.add_child(map)
    icon = folium.features.Icon(icon="user", prefix="fa", color="black")
    geojson = GeoDataFrame(
        points.loc[:, columns].astype(str),
        geometry=GeoSeries.from_xy(x=points.lng, y=points.lat),
    ).to_json()
    object_layer = folium.GeoJson(
        geojson,
        show=False,
        overlay=False,
        marker=folium.Marker(icon=icon),
        popup=folium.GeoJsonPopup(columns, labels=True),
    ).add_to(map)

    if len(points):
        p = points.copy()  # .sort_values('id')
        AntPath(
            [i for i in zip(p.lat, p.lng)],
            delay=1000,
            weight=6,
            dash_array=[9, 100],
            color="#000000",
            pulseColor="#FFFFFF",
            hardwareAcceleration=True,
            opacity=0.6,
        ).add_to(map)

    return map._repr_html_()


def generate_clusters(locs: pd.DataFrame, stay_locations=True):
    tdf = TrajDataFrame(
        pd.DataFrame(locs),
        latitude="lat",
        longitude="lon",
        user_id="employee_id",
        datetime="created_at",
    )
    if not stay_locations:
        return tdf
    tdf = detection.stay_locations(
        tdf,
        minutes_for_a_stop=2,
        no_data_for_minutes=360,
        spatial_radius_km=0.15,
    )
    return pd.DataFrame(tdf)


@owntracks_location.route("/", methods=["POST"])
def post_location():
    auth = request.authorization
    try:
        payload = jwt.decode(auth.password, key=SECRET_KEY)
    except JWTError:
        return not_allowed_403()
    if not payload.get("sub") == auth.username:
        return not_allowed_403()
    schema = OwnTracksLocationSchema(unknown=EXCLUDE)
    try:
        obj = schema.load(request.get_json())
        print(obj)
    except ValidationError as e:
        print(e.messages)
        return validation_error_422(e.messages)
    loc = OwnTracksLocation(**obj, employee_id=1)
    if loc.created_at.date() < dt.date.today():
        # переформировать кластеры, если локации пришли позже
        redis_session.sadd(
            "owntracks_cluster_dates", str(loc.created_at.date())
        )
    db_session.add(loc)
    db_session.commit()
    print(request.get_json())
    # return jsonify({"_type": "cmd", "action":"setConfiguration", "configuration":{"_type":"configuration", "moveModeLocatorInterval": 120, "locatorInterval": 90, "locatorDisplacement": 150}})
    return jsonify({})


@owntracks_location.route("/check", methods=["GET"])
def check_locations(limit=15):
    limit = request.args.get("limit") or limit
    sel = (
        select(OwnTracksLocation)
        .where(OwnTracksLocation.created_at != None)
        .order_by(OwnTracksLocation.id.desc())
        .limit(limit)
    )
    print(sel)
    res = db_session.execute(sel).scalars()
    scheme = OwnTracksLocationSchema(many=True)
    res = scheme.dump(res)

    if request.args.get("html"):
        stay_locations = True
        if request.args.get("stay_locations"):
            stay_locations = False
        res = generate_clusters(
            pd.DataFrame(res).sort_values("created_at"),
            stay_locations=stay_locations,
        )
        map = create_map(res, stay_locations=stay_locations)
        return map
    return jsonify(res)