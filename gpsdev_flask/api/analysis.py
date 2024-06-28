import datetime as dt

import pandas as pd
from flask import Blueprint, jsonify, request
from flask_login import current_user
from marshmallow import ValidationError
from sqlalchemy import distinct, func, select
from trajectory_report.coordinates_analysis_report import get_report
from trajectory_report.exceptions import ReportException

from gpsdev_flask import db_session
from gpsdev_flask.api import api_login_required
from gpsdev_flask.api.error_responses import (
    report_error_422,
    validation_error_422,
)
from gpsdev_flask.ma_schemas import CoordinatesAnalysisSchema
from gpsdev_flask.models import (
    Division,
    Employees,
    Journal,
    OwnTracksLocation,
    Statements,
)

analysis = Blueprint("analysis", __name__)


@analysis.route("/", methods=["POST"])
@api_login_required
def get_report_analysis():
    try:
        report_request = CoordinatesAnalysisSchema().load(request.get_json())
    except ValidationError as e:
        return validation_error_422(e.messages)
    try:
        r = get_report(**report_request)
    except ReportException as e:
        return report_error_422(str(e))
    return jsonify(r)


@analysis.route("/table", methods=["GET"])
@api_login_required
def get_last_coordinates():
    sel_journal = (
        select(Journal.name_id)
        .where(Journal.period_end == None)
        .where(Journal.owntracks == 1)
    )
    journal = db_session.execute(sel_journal).scalars()

    sel_stmts = (
        select(distinct(Statements.name_id))
        .where(Statements.date == dt.date.today())
        .where(Statements.statement == "В")
    )
    stmts = db_session.execute(sel_stmts).scalars()

    sel = (
        select(
            OwnTracksLocation.employee_id.label("name_id"),
            Division.division,
            func.max(OwnTracksLocation.created_at).label("datetime"),
            Employees.name,
            Employees.phone,
        )
        .join(Employees, Employees.name_id == OwnTracksLocation.employee_id)
        .join(Division, Division.id == Employees.division)
        .where(Employees.quit_date == None)
        .where(OwnTracksLocation.employee_id.in_(journal))
        .where(Division.id.in_(current_user.access_list))
        .group_by(OwnTracksLocation.employee_id)
    )
    df: pd.DataFrame = pd.read_sql(sel, db_session.connection())
    df["works_today"] = df["name_id"].isin(stmts)
    df["since_last_location"] = dt.datetime.now() - df["datetime"]
    df["problem"] = df["since_last_location"] > dt.timedelta(minutes=60)
    df["since_last_location"] = df["since_last_location"].apply(
        lambda x: str(x).split(".")[0].replace("days", "дней")
    )

    df["datetime"] = df["datetime"].apply(
        lambda x: x.strftime("%Y.%m.%d %H:%M:%S")
    )
    df.loc[df["works_today"] == False, "problem"] = False
    df = df.sort_values(
            ["problem", "division", "datetime"], ascending=[False, True, True]
    )
    return jsonify(df.to_dict(orient="records"))
