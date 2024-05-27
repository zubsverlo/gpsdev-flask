import requests
from trajectory_report.config import TOKEN_TELEGRAM, TELEGRAM_ADMIN_ID
from os import getenv
import json
import datetime as dt
from trajectory_report.report.Report import Report

CHANNELS_TO_NOTIFY: dict = json.loads(getenv("TELEGRAM_CHANNELS_TO_NOTIFY"))


def send_text(text: str, chat_id: str | None = None) -> int:
    """
    Присылает в лс администратору сообщение с текстом.
    Возвращает status_code запроса, чтобы понять, дошло ли сообщение.
    """
    api_url = "https://api.telegram.org/bot{}/".format(TOKEN_TELEGRAM)
    parse_mode = 'MarkDown'
    method = 'sendMessage'
    params = {'chat_id': chat_id or TELEGRAM_ADMIN_ID,
              'parse_mode': parse_mode,
              'text': text}
    resp = requests.post(api_url + method, params)
    return resp.status_code


def empty_locations_notify():
    date = dt.date.today()
    for division, chat_id in CHANNELS_TO_NOTIFY.items():
        r = Report(date, date, division)
        text = ""
        for i in r.employees_to_notify.to_numpy():
            text += ": +".join(i)+'\n'
        send_text(text, chat_id)
